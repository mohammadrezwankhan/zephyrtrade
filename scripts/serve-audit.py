#!/usr/bin/env python3
"""Serve the proposed audit document with its exact generated CSP for local checks.

This loopback-only review server is not a production deployment configuration.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=root / ".cloudflare/site/run/index.html")
    parser.add_argument("--headers", type=Path, default=root / ".cloudflare/runtime-security-headers.json")
    parser.add_argument("--port", type=int, default=4173)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535.")
    body = args.html.read_bytes()
    artifact = json.loads(args.headers.read_text(encoding="utf-8"))
    digest = hashlib.sha256(body).hexdigest()
    if artifact.get("document_sha256") != digest:
        parser.error("HTML and CSP artifact hashes differ. Regenerate headers from the final HTML.")
    headers = artifact.get("headers")
    if not isinstance(headers, dict) or not headers.get("Content-Security-Policy"):
        parser.error("The header artifact must contain a Content-Security-Policy.")
    for name, value in headers.items():
        if not isinstance(name, str) or not isinstance(value, str) or any(c in name + value for c in "\r\n"):
            parser.error("Header names and values must be strings without line breaks.")

    class Handler(BaseHTTPRequestHandler):
        server_version = "AuditReview/1.0"

        def respond(self, include_body: bool) -> None:
            path = urlsplit(self.path).path
            if path == "/":
                self.send_response(302)
                self.send_header("Location", "/run/")
                self.send_header("Content-Length", "0")
                self.end_headers()
                return
            if path not in ("/run/", "/run/index.html"):
                self.send_error(404, "Only the audited document is served")
                return
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            for name, value in headers.items():
                self.send_header(name, value)
            self.end_headers()
            if include_body:
                self.wfile.write(body)

        def do_GET(self) -> None:
            self.respond(True)

        def do_HEAD(self) -> None:
            self.respond(False)

    server = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print(json.dumps({"url": f"http://127.0.0.1:{args.port}/run/", "sha256": digest}), flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
