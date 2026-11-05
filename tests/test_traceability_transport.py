"""Offline dispatch-boundary regressions for the pinned traceability transport."""

from __future__ import annotations

import importlib.util
import io
import unittest
import urllib.error
import urllib.request
import urllib.response
from http.client import HTTPMessage
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "traceability_transport_checker", ROOT / "scripts" / "check-traceability.py"
)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Cannot load traceability checker")
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class _Response(urllib.response.addinfourl):
    msg = "offline fixture"

    def __init__(
        self, url: str, body: bytes, code: int, location: str | None = None
    ) -> None:
        headers = HTTPMessage()
        if location is not None:
            headers["Location"] = location
        super().__init__(io.BytesIO(body), headers, url, code)


class TransportBoundaryTests(unittest.TestCase):
    def test_public_redirects_are_rejected_before_another_dispatch(self) -> None:
        url = checker.EXPECTED["overview_url"]
        for code in (301, 302, 303, 307, 308):
            for destination in (
                "https://attacker.example/",
                "http://attacker.example/",
                url + "else",
            ):
                with self.subTest(code=code, destination=destination):
                    dispatched: list[tuple[str, str | None]] = []

                    def dispatch(
                        _opener: urllib.request.OpenerDirector,
                        request: urllib.request.Request,
                        _data: bytes | None = None,
                        *,
                        records: list[tuple[str, str | None]] = dispatched,
                        redirect_code: int = code,
                        target: str = destination,
                    ) -> _Response:
                        records.append(
                            (request.full_url, request.get_header("Authorization"))
                        )
                        if len(records) == 1:
                            return _Response(url, b"redirect", redirect_code, target)
                        return _Response(
                            request.full_url, b"unexpected second request", 200
                        )

                    with patch.object(
                        urllib.request.OpenerDirector, "_open", new=dispatch
                    ):
                        status, _body = checker._http_get(url)
                    self.assertEqual(code, status)
                    self.assertEqual([(url, None)], dispatched)

    def test_github_redirects_never_forward_authorization(self) -> None:
        url = "https://api.github.com/repos/" + checker.EXPECTED["repository"]
        for code in (301, 302, 303, 307, 308):
            for destination in (
                "https://attacker.example/",
                "http://attacker.example/",
                url + "/else",
            ):
                with self.subTest(code=code, destination=destination):
                    dispatched: list[tuple[str, str | None]] = []

                    def dispatch(
                        _opener: urllib.request.OpenerDirector,
                        request: urllib.request.Request,
                        _data: bytes | None = None,
                        *,
                        records: list[tuple[str, str | None]] = dispatched,
                        redirect_code: int = code,
                        target: str = destination,
                    ) -> _Response:
                        records.append(
                            (request.full_url, request.get_header("Authorization"))
                        )
                        if len(records) == 1:
                            return _Response(url, b"redirect", redirect_code, target)
                        return _Response(request.full_url, b'{"unexpected": true}', 200)

                    with (
                        patch.object(
                            urllib.request.OpenerDirector, "_open", new=dispatch
                        ),
                        self.assertRaises(urllib.error.HTTPError),
                    ):
                        checker._github_repo_get(
                            checker.EXPECTED["repository"], "offline-token"
                        )
                    self.assertEqual([(url, "Bearer offline-token")], dispatched)

    def test_pinned_requests_preserve_decoded_body_and_github_json(self) -> None:
        urls = [
            checker.EXPECTED[key]
            for key in ("portal_url", "overview_url", "runtime_url", "metadata_url")
        ]
        urls.append(checker.REPOSITORY_URL)
        api_url = "https://api.github.com/repos/" + checker.EXPECTED["repository"]
        dispatched: list[tuple[str, str | None]] = []

        def dispatch(
            _opener: urllib.request.OpenerDirector,
            request: urllib.request.Request,
            _data: bytes | None = None,
        ) -> _Response:
            dispatched.append((request.full_url, request.get_header("Authorization")))
            body = (
                b'{"name": "fixture", "private": false}'
                if request.full_url == api_url
                else b"exact\r\nbody\xff"
            )
            return _Response(request.full_url, body, 200)

        with patch.object(urllib.request.OpenerDirector, "_open", new=dispatch):
            for url in urls:
                self.assertEqual((200, "exact\r\nbody\ufffd"), checker._http_get(url))
            self.assertEqual(
                {"name": "fixture", "private": False},
                checker._github_repo_get(
                    checker.EXPECTED["repository"], "offline-token"
                ),
            )
        self.assertEqual(
            [(url, None) for url in urls] + [(api_url, "Bearer offline-token")],
            dispatched,
        )

    def test_unpinned_urls_are_rejected_before_request_creation(self) -> None:
        urls = (
            "file:///etc/passwd",
            "http://mklab.co.technology/",
            "https://mklab.co.technology.attacker.example/",
            "https://attacker.example/",
            checker.EXPECTED["overview_url"] + "?spoof=1",
        )
        for url in urls:
            with (
                self.subTest(url=url),
                patch.object(
                    urllib.request,
                    "Request",
                    side_effect=AssertionError("request constructed"),
                ),
                self.assertRaises(ValueError),
            ):
                checker._http_get(url)

    def test_unpinned_repository_cannot_attach_credentials(
        self,
    ) -> None:
        for repository in (
            "file:///etc/passwd",
            "https://attacker.example/",
            checker.EXPECTED["repository"] + "/spoof",
            "other/repository",
        ):
            with (
                self.subTest(repository=repository),
                patch.object(
                    urllib.request,
                    "Request",
                    side_effect=AssertionError("request constructed"),
                ),
                self.assertRaises(ValueError),
            ):
                checker._github_repo_get(repository, "offline-token")
