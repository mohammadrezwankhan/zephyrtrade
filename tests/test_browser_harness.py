"""Keep browser instrumentation confined to the exact test fixture bytes."""

from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
from pathlib import Path

import pytest

from scripts.check_browser import instrument


class DocumentContents(HTMLParser):
    def __init__(self, document: str) -> None:
        super().__init__(convert_charrefs=True)
        self.policies: list[dict[str, list[str]]] = []
        self.scripts: list[str] = []
        self.in_script = False
        self.feed(document)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "meta" and values.get("http-equiv") == "Content-Security-Policy":
            policy = values.get("content")
            assert policy is not None
            directives = [part.split() for part in policy.split(";") if part.strip()]
            self.policies.append({parts[0]: parts[1:] for parts in directives})
        if tag == "script":
            self.in_script = True
            self.scripts.append("")

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.scripts[-1] += data

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self.in_script = False


@pytest.mark.parametrize("store", [None, {"scenario": "</script><img src=x>"}])
def test_browser_fixture_authorizes_only_its_actual_script_bytes(
    store: dict[str, str] | None,
) -> None:
    path = Path(__file__).resolve().parents[1] / "ZephyrTrade-Champion.html"
    original = path.read_bytes()
    document = original.decode()
    before = DocumentContents(document)
    after = DocumentContents(instrument(document, store))
    assert len(before.policies) == len(after.policies) == 1
    assert len(after.scripts) == len(before.scripts) + 1
    fixture = next(
        script for script in after.scripts if "window.__denyStorage" in script
    )
    assert [script for script in after.scripts if script != fixture] == before.scripts
    digest = base64.b64encode(hashlib.sha256(fixture.encode()).digest()).decode()
    expected_token = f"'sha256-{digest}'"
    original_policy, fixture_policy = before.policies[0], after.policies[0]
    assert original_policy.keys() == fixture_policy.keys()
    for directive, tokens in original_policy.items():
        expected = (
            [*tokens, expected_token]
            if directive
            in {
                "script-src",
                "script-src-elem",
            }
            else tokens
        )
        assert fixture_policy[directive] == expected
    assert "'unsafe-inline'" not in fixture_policy["script-src"]
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "policy",
    [
        "",
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'">',
        '<meta http-equiv="Content-Security-Policy" '
        "content=\"script-src 'self'; script-src *\">",
        '<meta http-equiv="Content-Security-Policy" content="script-src \'self\'">' * 2,
    ],
)
def test_browser_fixture_rejects_missing_or_ambiguous_policy(policy: str) -> None:
    with pytest.raises(ValueError, match="policy"):
        instrument(f"<!doctype html><html><head>{policy}</head><body></body></html>")
