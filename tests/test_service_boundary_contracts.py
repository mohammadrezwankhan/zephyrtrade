"""Exercise local HTTP rejection, bounded workers, and CLI lifecycle behavior."""

from __future__ import annotations

import http.client
import json
import socket
import sys
import threading
import webbrowser
from collections.abc import Iterator
from http.server import ThreadingHTTPServer
from pathlib import Path
from typing import NoReturn

import pytest

from zephyrtrade import app


@pytest.fixture(scope="module")
def service() -> Iterator[app.LocalServer]:
    server = app.LocalServer(0)
    worker = threading.Thread(target=server.serve_forever, daemon=True)
    worker.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        worker.join(5)


def request(
    server: app.LocalServer,
    method: str,
    path: str,
    body: str | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, bytes]:
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    try:
        connection.request(method, path, body=body, headers=headers or {})
        response = connection.getresponse()
        return response.status, response.read()
    finally:
        connection.close()


def test_uniform_scenarios_and_missing_static_assets_have_truthful_results(
    service: app.LocalServer,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    result = app.optimize_payload(
        {"capacity": 30, "da": 400, "up": 600, "down": 200, "scenarios": [8]}
    )
    assert result["offer_mw"] == 8
    assert result["expected_revenue_dkk"] == 3200
    assert request(service, "GET", "/favicon.ico") == (204, b"")
    monkeypatch.setattr(app, "WEB_ROOT", tmp_path)
    status, body = request(service, "GET", "/")
    assert status == 503
    assert b"packaged UI asset is missing" in body


def test_post_routing_host_fetch_site_and_preflight_are_rejected(
    service: app.LocalServer,
) -> None:
    assert request(service, "OPTIONS", "/api/optimize")[0] == 405
    assert request(service, "POST", "/other", "{}")[0] == 404
    assert (
        request(service, "POST", "/api/optimize", "{}", {"Host": "attacker.example"})[0]
        == 403
    )
    assert (
        request(
            service, "POST", "/api/optimize", "{}", {"Sec-Fetch-Site": "cross-site"}
        )[0]
        == 403
    )


@pytest.mark.parametrize(
    "fields,body,status",
    [
        ("Transfer-Encoding: chunked\r\n", b"", 411),
        ("Content-Length: 2\r\nContent-Length: 2\r\n", b"{}", 411),
        ("Content-Length: nope\r\n", b"", 400),
        ("Content-Length: 2\r\n", b"{", 400),
    ],
)
def test_ambiguous_or_incomplete_request_framing_fails_before_solver(
    service: app.LocalServer,
    fields: str,
    body: bytes,
    status: int,
) -> None:
    with socket.create_connection(
        ("127.0.0.1", service.server_port), timeout=5
    ) as connection:
        message = (
            f"POST /api/optimize HTTP/1.1\r\nHost: 127.0.0.1:{service.server_port}\r\n"
            "Content-Type: application/json\r\n" + fields + "\r\n"
        )
        connection.sendall(message.encode("ascii") + body)
        connection.shutdown(socket.SHUT_WR)
        response = http.client.HTTPResponse(connection)
        response.begin()
        assert response.status == status
        assert b"error" in response.read()


def test_solver_failure_is_recoverable_and_releases_the_single_solver_slot(
    service: app.LocalServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def unavailable_solver(*_args: object, **_kwargs: object) -> NoReturn:
        raise RuntimeError("sensitive numerical backend detail")

    body = json.dumps(
        {"capacity": 30, "da": 400, "up": 600, "down": 200, "scenarios": [8]}
    )
    with monkeypatch.context() as context:
        context.setattr(app, "solve_single_period_offer_lp", unavailable_solver)
        status, data = request(
            service, "POST", "/api/optimize", body, {"Content-Type": "application/json"}
        )
    assert status == 503
    assert b"sensitive" not in data
    assert (
        request(
            service, "POST", "/api/optimize", body, {"Content-Type": "application/json"}
        )[0]
        == 200
    )


def test_worker_capacity_rejects_excess_requests_then_recovers(
    service: app.LocalServer,
) -> None:
    for _ in range(8):
        assert service.workers.acquire(timeout=5)
    try:
        assert request(service, "GET", "/api/health") == (503, b"")
    finally:
        for _ in range(8):
            service.workers.release()
    assert request(service, "GET", "/api/health")[0] == 200


def test_failed_thread_dispatch_does_not_leak_a_worker_slot(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def failed_dispatch(
        _server: ThreadingHTTPServer, _request: socket.socket, _address: tuple[str, int]
    ) -> NoReturn:
        raise OSError("cannot start worker")

    server = app.LocalServer(0)
    monkeypatch.setattr(ThreadingHTTPServer, "process_request", failed_dispatch)
    try:
        with socket.socket() as connection, pytest.raises(OSError, match="worker"):
            server.process_request(connection, ("127.0.0.1", 12345))
        for _ in range(8):
            assert server.workers.acquire(blocking=False)
        assert not server.workers.acquire(blocking=False)
        for _ in range(8):
            server.workers.release()
    finally:
        server.server_close()


def test_local_cli_rejects_privileged_ports_and_reports_an_occupied_port(
    service: app.LocalServer,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(sys, "argv", ["zephyr-app", "--port", "0", "--no-browser"])
    with pytest.raises(SystemExit) as invalid:
        app.main()
    assert invalid.value.code == 2
    monkeypatch.setattr(
        sys, "argv", ["zephyr-app", "--port", str(service.server_port), "--no-browser"]
    )
    with pytest.raises(SystemExit) as occupied:
        app.main()
    assert occupied.value.code == 1


@pytest.mark.parametrize("open_browser", [False, True])
def test_cli_shutdown_closes_its_socket_and_only_opens_a_local_url(
    open_browser: bool,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with socket.socket() as temporary:
        temporary.bind(("127.0.0.1", 0))
        port = temporary.getsockname()[1]
    opened: list[str] = []

    def stop_server(_server: app.LocalServer, _poll_interval: float = 0.5) -> NoReturn:
        raise KeyboardInterrupt

    def open_local(url: str) -> bool:
        opened.append(url)
        return True

    def immediate_timer(timer: threading.Timer) -> None:
        timer.run()

    monkeypatch.setattr(app.LocalServer, "serve_forever", stop_server)
    monkeypatch.setattr(webbrowser, "open", open_local)
    monkeypatch.setattr(threading.Timer, "start", immediate_timer)
    argv = ["zephyr-app", "--port", str(port)]
    if not open_browser:
        argv.append("--no-browser")
    monkeypatch.setattr(sys, "argv", argv)
    app.main()
    assert opened == ([f"http://127.0.0.1:{port}"] if open_browser else [])
    with socket.socket() as reopened:
        reopened.bind(("127.0.0.1", port))
