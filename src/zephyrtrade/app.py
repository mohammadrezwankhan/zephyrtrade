"""Local-only research UI and bounded SciPy cross-check service.

This is a single-user development service, not an internet-facing deployment.
It never loads saved estimator pickles or submits market orders.
"""

from __future__ import annotations

import argparse
import json
import math
import threading
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import numpy as np

from zephyrtrade import __version__
from zephyrtrade.optimize import solve_single_period_offer_lp

MAX_BODY = 32_768
WEB_ROOT = Path(__file__).with_name("web")
ASSETS = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/engine.js": ("engine.js", "text/javascript; charset=utf-8"),
    "/app.js": ("app.js", "text/javascript; charset=utf-8"),
    "/snapshot.js": ("snapshot.js", "text/javascript; charset=utf-8"),
}


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    """Validate a finite JSON number, excluding booleans and numeric strings."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a JSON number.")
    if not math.isfinite(value) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum:g} and {maximum:g}.")
    return float(value)


def optimize_payload(payload: Any) -> dict[str, Any]:
    """Validate lab assumptions and solve the repository's unchanged LP objective."""
    required = {"capacity", "da", "up", "down", "scenarios"}
    allowed = required | {"hours", "probabilities"}
    if not isinstance(payload, dict) or not required <= payload.keys():
        raise ValueError("Supply capacity, da, up, down and scenarios.")
    if payload.keys() - allowed:
        raise ValueError("The request contains unsupported fields.")
    capacity = _number(payload["capacity"], "Capacity", 0.1, 10000)
    hours = _number(payload.get("hours", 1), "Duration", 0.25, 24)
    prices = {k: _number(payload[k], k, -10000, 100000) for k in ("da", "up", "down")}
    scenarios = payload["scenarios"]
    if not isinstance(scenarios, list) or not 1 <= len(scenarios) <= 100:
        raise ValueError("Supply 1 to 100 production scenarios.")
    scenarios = np.array([_number(x, "Scenario", 0, capacity) for x in scenarios])
    probabilities = payload.get("probabilities")
    if probabilities is None or probabilities == []:
        probabilities = np.full(len(scenarios), 1.0 / len(scenarios))
    else:
        if not isinstance(probabilities, list) or len(probabilities) != len(scenarios):
            raise ValueError("Probabilities must align with the scenarios.")
        probabilities = np.array([_number(x, "Probability", 0, 1.0000001) for x in probabilities])
        total = float(probabilities.sum())
        if abs(total - 1) > 1e-7:
            raise ValueError("Probabilities must sum to 1 within 0.0000001.")
        probabilities = probabilities / total
    result = solve_single_period_offer_lp(
        scenarios, probabilities, prices["da"], prices["up"], prices["down"], capacity
    )
    return {
        "offer_mw": float(result["offer_mw"]),
        "expected_revenue_dkk": float(result["expected_revenue_dkk"]) * hours,
        "interval_hours": hours,
        "solver": "scipy.optimize.linprog / HiGHS",
        "data_kind": "user_assumptions_not_live",
    }


def _reject_constant(value: str) -> None:
    """Reject non-standard JSON NaN and Infinity values."""
    raise ValueError(f"{value} is not a valid JSON number.")


def _unique_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    """Reject duplicate JSON keys instead of silently taking the last value."""
    output: dict[str, Any] = {}
    for key, value in pairs:
        if key in output:
            raise ValueError("Duplicate JSON field.")
        output[key] = value
    return output


class LocalServer(ThreadingHTTPServer):
    """Serve only loopback, with bounded concurrent requests and one solver."""

    daemon_threads = True
    request_queue_size = 8

    def __init__(self, port: int = 8765) -> None:
        """Bind an isolated single-user service to the IPv4 loopback interface."""
        super().__init__(("127.0.0.1", port), Handler)
        self.workers = threading.BoundedSemaphore(8)
        self.solver = threading.Lock()

    def process_request(self, request: Any, client_address: Any) -> None:
        """Reject excess work rather than creating an unbounded thread pool."""
        if not self.workers.acquire(blocking=False):
            try:
                request.sendall(b"HTTP/1.0 503 Service Unavailable\r\nContent-Length: 0\r\nConnection: close\r\n\r\n")
            finally:
                self.shutdown_request(request)
            return
        try:
            super().process_request(request, client_address)
        except BaseException:
            self.workers.release()
            raise

    def process_request_thread(self, request: Any, client_address: Any) -> None:
        """Release the worker slot for both successful and disconnected requests."""
        try:
            super().process_request_thread(request, client_address)
        finally:
            self.workers.release()


class Handler(BaseHTTPRequestHandler):
    """Expose a fixed asset allowlist and a same-origin, JSON-only solver route."""

    server: LocalServer
    server_version = "ZephyrTradeLocal/1.1"
    sys_version = ""
    timeout = 10

    def log_message(self, format: str, *args: Any) -> None:
        """Avoid logging user scenario values, raw URLs or request headers."""

    def _reply(self, code: int, data: bytes, content_type: str) -> None:
        """Send bounded response content with local-use security headers."""
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Content-Security-Policy", "default-src 'none'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; frame-ancestors 'none'; form-action 'self'")
        self.send_header("Connection", "close")
        self.end_headers()
        if self.command != "HEAD":
            self.wfile.write(data)
        self.close_connection = True

    def _json(self, code: int, value: dict[str, Any]) -> None:
        """Serialize responses without nonfinite numbers."""
        self._reply(code, json.dumps(value, allow_nan=False).encode(), "application/json; charset=utf-8")

    def _trusted_host(self) -> bool:
        """Reject non-loopback Host headers, including DNS-rebinding hosts."""
        hosts = self.headers.get_all("Host", [])
        expected = {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}
        if len(hosts) != 1 or hosts[0].lower() not in expected:
            self._json(HTTPStatus.FORBIDDEN, {"error": "Use the local loopback application address."})
            return False
        return True

    def do_GET(self) -> None:
        """Serve health or an explicit asset, never arbitrary filesystem paths."""
        if not self._trusted_host():
            return
        path = urlsplit(self.path).path
        if path == "/api/health":
            self._json(200, {"service": "zephyrtrade-local", "version": __version__, "scope": "local_research_only"})
            return
        if path == "/favicon.ico":
            self._reply(204, b"", "image/x-icon")
            return
        asset = ASSETS.get(path)
        if asset is None:
            self._json(404, {"error": "Resource not found."})
            return
        filename, content_type = asset
        try:
            data = (WEB_ROOT / filename).read_bytes()
        except OSError:
            self._json(503, {"error": "A packaged UI asset is missing. Reinstall the application."})
            return
        self._reply(200, data, content_type)

    def do_HEAD(self) -> None:
        """Return asset metadata without a response body."""
        self.do_GET()

    def do_POST(self) -> None:
        """Validate the browser boundary before entering the local solver."""
        if not self._trusted_host():
            return
        if self.path != "/api/optimize":
            self._json(404, {"error": "Resource not found."})
            return
        origins = self.headers.get_all("Origin", [])
        allowed = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
        # Non-browser CLI requests may omit Origin. Cross-origin browser posts may not.
        if len(origins) > 1 or (origins and origins[0] not in allowed):
            self._json(403, {"error": "Cross-origin requests are not permitted."})
            return
        if self.headers.get("Sec-Fetch-Site") == "cross-site":
            self._json(403, {"error": "Cross-site requests are not permitted."})
            return
        if self.headers.get_content_type() != "application/json":
            self._json(415, {"error": "Use application/json."})
            return
        lengths = self.headers.get_all("Content-Length", [])
        if self.headers.get("Transfer-Encoding") or len(lengths) != 1:
            self._json(411, {"error": "A single Content-Length is required."})
            return
        try:
            length = int(lengths[0])
        except ValueError:
            self._json(400, {"error": "Invalid Content-Length."})
            return
        if not 1 <= length <= MAX_BODY:
            self._json(413, {"error": "Request must contain 1 to 32768 bytes."})
            return
        try:
            body = self.rfile.read(length)
            if len(body) != length:
                raise ValueError("Incomplete request body.")
            payload = json.loads(body, parse_constant=_reject_constant, object_pairs_hook=_unique_keys)
        except (ValueError, UnicodeDecodeError, RecursionError):
            self._json(400, {"error": "Send complete, valid JSON without duplicate fields or nonfinite values."})
            return
        if not self.server.solver.acquire(blocking=False):
            self._json(503, {"error": "The local solver is busy. Your inputs are retained; retry shortly."})
            return
        try:
            result = optimize_payload(payload)
            self._json(200, result)
        except (ValueError, TypeError, OverflowError) as exc:
            self._json(400, {"error": str(exc)})
        except RuntimeError:
            self._json(503, {"error": "The optimisation could not be completed. Review the assumptions and retry."})
        finally:
            self.server.solver.release()

    def do_OPTIONS(self) -> None:
        """Refuse cross-origin preflight; no CORS access is granted."""
        self._json(405, {"error": "Cross-origin access is not supported."})


def main() -> None:
    """Start the optional loopback UI without contacting any external service."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error("Choose a local port between 1024 and 65535.")
    try:
        server = LocalServer(args.port)
    except OSError as exc:
        parser.exit(1, f"Could not start the local server: {exc}. Try --port 8766.\n")
    url = f"http://127.0.0.1:{server.server_port}"
    print(f"ZephyrTrade Champion {__version__}\n{url}\nSynthetic research only. Press Ctrl+C to stop.", flush=True)
    if not args.no_browser:
        threading.Timer(0.5, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
