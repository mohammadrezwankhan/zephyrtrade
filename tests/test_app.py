"""Local HTTP boundary and real SciPy solver integration tests."""

import http.client
import json
from threading import Thread

import pytest

from zephyrtrade.app import LocalServer, optimize_payload


@pytest.fixture(scope="module")
def server():
    service = LocalServer(0)
    worker = Thread(target=service.serve_forever, daemon=True)
    worker.start()
    yield service
    service.shutdown()
    service.server_close()
    worker.join(timeout=5)


def request(server, method="GET", path="/api/health", body=None, headers=None):
    connection = http.client.HTTPConnection("127.0.0.1", server.server_port, timeout=5)
    connection.request(method, path, body, headers or {})
    response = connection.getresponse()
    result = response.status, dict(response.getheaders()), response.read()
    connection.close()
    return result


def assumptions():
    return {
        "capacity": 30,
        "hours": 1,
        "da": 400,
        "up": 600,
        "down": 200,
        "scenarios": [2, 8, 20],
        "probabilities": [0.2, 0.5, 0.3],
    }


def test_health_and_loopback_binding(server):
    status, headers, body = request(server)
    assert status == 200
    assert json.loads(body)["service"] == "zephyrtrade-local"
    assert server.server_address[0] == "127.0.0.1"
    assert headers["Cache-Control"] == "no-store"
    assert "frame-ancestors 'none'" in headers["Content-Security-Policy"]
    assert "Access-Control-Allow-Origin" not in headers


@pytest.mark.parametrize(
    "path", ["/", "/styles.css", "/app.js", "/engine.js", "/snapshot.js"]
)
def test_packaged_assets(server, path):
    status, headers, body = request(server, path=path)
    assert status == 200
    assert len(body) > 100
    assert headers["X-Content-Type-Options"] == "nosniff"


@pytest.mark.parametrize(
    "path",
    [
        "/../pyproject.toml",
        "/%2e%2e/LICENSE",
        "/data/raw/provenance.json",
        "/secret",
        "/artifacts/model.joblib",
    ],
)
def test_filesystem_not_exposed(server, path):
    assert request(server, path=path)[0] == 404


def test_head_has_no_body(server):
    status, headers, body = request(server, method="HEAD", path="/")
    assert status == 200 and len(body) == 0
    assert int(headers["Content-Length"]) > 100


def test_rebinding_host_is_rejected(server):
    assert request(server, headers={"Host": "attacker.example"})[0] == 403


@pytest.mark.parametrize(
    "origin", ["null", "https://attacker.example", "http://localhost:1"]
)
def test_cross_origin_posts_rejected(server, origin):
    assert (
        request(
            server,
            "POST",
            "/api/optimize",
            json.dumps(assumptions()),
            {"Content-Type": "application/json", "Origin": origin},
        )[0]
        == 403
    )


def test_real_http_solver_and_duration(server):
    payload = assumptions()
    payload["hours"] = 0.5
    status, headers, body = request(
        server,
        "POST",
        "/api/optimize",
        json.dumps(payload),
        {
            "Content-Type": "application/json",
            "Origin": f"http://127.0.0.1:{server.server_port}",
        },
    )
    assert status == 200
    result = json.loads(body)
    # At offer 8, a 6 MW shortfall costs 6 * 600 = 3600 DKK.
    expected = (0.2 * (-400) + 0.5 * 3200 + 0.3 * 5600) * 0.5
    assert result["offer_mw"] == pytest.approx(8)
    assert result["expected_revenue_dkk"] == pytest.approx(expected)
    assert result["data_kind"] == "user_assumptions_not_live"


@pytest.mark.parametrize(
    "body", ["{", '{"capacity":NaN}', '{"da":1,"da":2}', '"text"', "null", "[]"]
)
def test_bad_json_is_truthful_client_error(server, body):
    status, headers, response = request(
        server, "POST", "/api/optimize", body, {"Content-Type": "application/json"}
    )
    assert status == 400
    assert "error" in json.loads(response)
    assert b"Traceback" not in response


def test_wrong_media_type_and_oversize(server):
    assert (
        request(server, "POST", "/api/optimize", "x", {"Content-Type": "text/plain"})[0]
        == 415
    )
    assert (
        request(
            server,
            "POST",
            "/api/optimize",
            "x" * 32769,
            {"Content-Type": "application/json"},
        )[0]
        == 413
    )


def test_busy_solver_returns_recoverable_failure(server):
    with server.solver:
        result = request(
            server,
            "POST",
            "/api/optimize",
            json.dumps(assumptions()),
            {"Content-Type": "application/json"},
        )
    assert result[0] == 503
    assert b"retained" in result[2]
    assert request(server)[0] == 200


@pytest.mark.parametrize(
    "key,value",
    [
        ("capacity", True),
        ("capacity", 0),
        ("capacity", "30"),
        ("hours", float("inf")),
        ("up", 100),
        ("down", 700),
        ("scenarios", []),
        ("scenarios", [31]),
        ("scenarios", [float("nan")]),
        ("probabilities", [-0.2, 0.9, 0.3]),
        ("probabilities", [1]),
        ("probabilities", [0, 0, 0]),
        ("probabilities", "abc"),
    ],
)
def test_payload_validation(key, value):
    payload = assumptions()
    payload[key] = value
    with pytest.raises(ValueError):
        optimize_payload(payload)


def test_small_probability_rounding_is_normalized():
    payload = assumptions()
    payload.update(scenarios=[7], probabilities=[1.00000001])
    assert optimize_payload(payload)["offer_mw"] == pytest.approx(7)


def test_unknown_fields_rejected():
    with pytest.raises(ValueError, match="unsupported"):
        optimize_payload({**assumptions(), "execute_order": True})
