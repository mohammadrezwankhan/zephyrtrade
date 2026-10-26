#!/usr/bin/env python3
"""Check this repository's one public MKLab mapping and its published endpoints."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "traceability.json"
# This code-level identity pins the config to this checkout. The JSON file is the
# single-repository mapping only; it is not the central/private registry.
EXPECTED = {
    "app_id": "37",
    "repository": "mohammadrezwankhan/zephyrtrade",
    "portal_url": "https://mklab.co.technology/",
    "overview_url": "https://mktrade.co.business/",
    "runtime_url": "https://mktrade.co.business/run/",
    "metadata_url": "https://mktrade.co.business/app.json",
    "default_branch": "main",
    "source_visibility": "public",
}
REPOSITORY_URL = "https://github.com/" + EXPECTED["repository"]
TIMEOUT_SECONDS = 15
MAX_RESPONSE_BYTES = 2_000_000
PRIVATE_RESPONSE_BYTES = 16_000_000


def _reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_config(path: Path = CONFIG_PATH) -> dict[str, str]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_keys
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"cannot read a valid traceability.json: {exc}") from exc
    errors = validate_config(value)
    if errors:
        raise ValueError("invalid traceability mapping: " + "; ".join(errors))
    return value  # type: ignore[return-value]


def validate_config(
    value: object, *, expected: dict[str, str] | None = None
) -> list[str]:
    pinned = EXPECTED if expected is None else expected
    if not isinstance(value, dict):
        return ["traceability.json must contain one JSON object"]
    errors: list[str] = []
    actual_keys = set(value)
    expected_keys = set(pinned)
    if actual_keys != expected_keys:
        errors.append("traceability.json must contain only this app's mapping fields")
    for key, expected_value in pinned.items():
        if value.get(key) != expected_value:
            errors.append(
                f"traceability.json {key} must exactly match this repository's pinned mapping"
            )
    if value.get("source_visibility") not in {"public", "private"}:
        errors.append("source_visibility must be exactly public or private")
    for key in ("portal_url", "overview_url", "runtime_url", "metadata_url"):
        candidate = value.get(key)
        if not isinstance(candidate, str):
            continue
        try:
            parts = urllib.parse.urlsplit(candidate)
        except ValueError:
            errors.append(f"{key} is not a valid URL")
            continue
        if (
            parts.scheme != "https"
            or not parts.hostname
            or parts.username
            or parts.password
            or parts.port not in (None, 443)
        ):
            errors.append(
                f"{key} must be an HTTPS URL without credentials or a custom port"
            )
    return errors


def _css_hidden(attributes: dict[str, str | None]) -> bool:
    style = re.sub(r"\s+", "", (attributes.get("style") or "").casefold())
    classes = set((attributes.get("class") or "").casefold().split())
    return (
        "hidden" in attributes
        or bool(
            classes
            & {
                "d-none",
                "display-none",
                "hidden",
                "is-hidden",
                "sr-only",
                "visually-hidden",
            }
        )
        or (attributes.get("aria-hidden") or "").casefold() == "true"
        or "display:none" in style
        or "visibility:hidden" in style
        or "opacity:0" in style
    )


class _VisibleMarkup(HTMLParser):
    """Collect visible HTML text and nonempty visible anchor destinations."""

    VOID = {
        "area",
        "base",
        "br",
        "col",
        "embed",
        "hr",
        "img",
        "input",
        "link",
        "meta",
        "param",
        "source",
        "track",
        "wbr",
    }
    HIDDEN_TAGS = {"head", "script", "style", "template", "noscript"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[dict[str, object]] = []
        self.anchors: list[dict[str, str]] = []
        self.open_anchors: list[dict[str, str]] = []
        self.visible_text: list[str] = []

    def _hidden(self) -> bool:
        for index, entry in enumerate(self.stack):
            if entry["hidden"]:
                return True
            if entry["closed_details"]:
                # The summary of a closed details element is visible; its other
                # content is not present until a user opens the disclosure.
                if not any(
                    item["tag"] == "summary" for item in self.stack[index + 1 :]
                ):
                    return True
        return False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.casefold()
        attributes = {key.casefold(): value for key, value in attrs}
        own_hidden = tag in self.HIDDEN_TAGS or _css_hidden(attributes)
        if tag == "a":
            anchor = {"href": attributes.get("href") or "", "text": ""}
            self.anchors.append(anchor)
            self.open_anchors.append(anchor)
            if self._hidden() or own_hidden:
                anchor["href"] = ""
        entry: dict[str, object] = {
            "tag": tag,
            "hidden": own_hidden,
            "closed_details": tag == "details" and "open" not in attributes,
            "anchor": self.open_anchors[-1]
            if tag == "a" and self.open_anchors
            else None,
        }
        if tag == "img" and not self._hidden():
            alt = attributes.get("alt") or ""
            for anchor in self.open_anchors:
                anchor["text"] += alt
        if tag not in self.VOID:
            self.stack.append(entry)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        tag = tag.casefold()
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index]["tag"] == tag:
                removed = self.stack[index:]
                del self.stack[index:]
                for entry in reversed(removed):
                    anchor = entry.get("anchor")
                    if anchor is not None and anchor in self.open_anchors:
                        self.open_anchors.remove(anchor)  # type: ignore[arg-type]
                break

    def handle_data(self, data: str) -> None:
        if self._hidden():
            return
        if not self.stack:
            self.visible_text.append(data)
        for anchor in self.open_anchors:
            anchor["text"] += data


def _visible_markdown_text(markup: str) -> tuple[str, set[str]]:
    parser = _VisibleMarkup()
    parser.feed(markup)
    parser.close()
    visible = "".join(parser.visible_text)
    # Markdown code samples and inline code are not rendered as links.
    visible = re.sub(
        r"(?ms)^[ \t]{0,3}(`{3,}|~{3,})[^\r\n]*\r?\n.*?^[ \t]{0,3}\1[ \t]*\r?$",
        "",
        visible,
    )
    tick = chr(96)
    visible = re.sub(
        r"(?<!"
        + tick
        + ")"
        + tick
        + r"+[^"
        + tick
        + r"\r\n]*"
        + tick
        + r"+(?!"
        + tick
        + ")",
        "",
        visible,
    )
    hrefs = {
        item["href"] for item in parser.anchors if item["href"] and item["text"].strip()
    }
    return visible, hrefs


_MARKDOWN_LINK_RE = re.compile(
    r"(?<!!)\[((?:!\[[^\]\r\n]*\]\([^\)\r\n]*\)|[^\[\]\r\n])+?)\]\(\s*(<[^>\r\n]+>|[^\s)]+)"
    r"(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)"
)


def has_exact_visible_link(markup: str, url: str) -> bool:
    visible_text, html_hrefs = _visible_markdown_text(markup)
    if url in html_hrefs:
        return True
    for match in _MARKDOWN_LINK_RE.finditer(visible_text):
        label = match.group(1).strip()
        destination = match.group(2)
        if destination.startswith("<") and destination.endswith(">"):
            destination = destination[1:-1]
        if label and destination == url:
            return True
    return False


def check_readme(readme: str, config: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if not has_exact_visible_link(readme, config["portal_url"]):
        errors.append(
            "README is missing an exact visible Markdown or HTML link to the MKLab portal"
        )
    if not has_exact_visible_link(readme, config["overview_url"]):
        errors.append(
            "README is missing an exact visible Markdown or HTML link to this app overview"
        )
    return errors


def _http_get(url: str) -> tuple[int, str]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Encoding": "identity",
            "User-Agent": "mklab-traceability-checker/1.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
            if response.geturl() != url:
                raise RuntimeError(
                    f"endpoint redirected away from its exact configured URL: {url}"
                )
            limit = (
                PRIVATE_RESPONSE_BYTES
                if EXPECTED["source_visibility"] == "private"
                else MAX_RESPONSE_BYTES
            )
            body = response.read(limit + 1)
            if EXPECTED["source_visibility"] == "private" and len(body) > limit:
                raise RuntimeError(
                    f"public response exceeds the private-URL scan limit: {url}"
                )
            return response.status, body.decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read(64_000).decode("utf-8", "replace")


def _github_repo_get(repository: str, token: str) -> dict[str, object]:
    encoded = urllib.parse.quote(repository, safe="/")
    request = urllib.request.Request(
        "https://api.github.com/repos/" + encoded,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
            "User-Agent": "mklab-traceability-checker/1.0",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
        value = json.load(response, object_pairs_hook=_reject_duplicate_keys)
    if not isinstance(value, dict):
        raise RuntimeError("GitHub repository API returned a non-object response")
    return value


def validate_github_metadata(metadata: object, config: dict[str, str]) -> list[str]:
    if not isinstance(metadata, dict):
        return ["GitHub repository metadata must be a JSON object"]
    errors: list[str] = []
    for key, expected in (
        ("full_name", config["repository"]),
        ("default_branch", config["default_branch"]),
        ("homepage", config["overview_url"]),
    ):
        if metadata.get(key) != expected:
            errors.append(f"GitHub repository {key} must exactly equal {expected!r}")
    expected_private = config["source_visibility"] == "private"
    if metadata.get("private") is not expected_private:
        errors.append(
            f"GitHub repository visibility must be {'private' if expected_private else 'public'}"
        )
    return errors


def check_live(
    config: dict[str, str],
    *,
    get_url: Callable[[str], tuple[int, str]] | None = None,
    get_repo: Callable[[str, str], dict[str, object]] | None = None,
    token: str | None = None,
) -> list[str]:
    """Fail closed unless public endpoints and the owning GitHub mapping agree."""
    get_url = get_url or _http_get
    token = token if token is not None else os.environ.get("GH_TOKEN", "")
    errors: list[str] = []
    responses: dict[str, str] = {}
    urls = [
        ("portal", config["portal_url"]),
        ("app overview", config["overview_url"]),
        ("app runtime", config["runtime_url"]),
        ("app.json", config["metadata_url"]),
    ]
    is_public = config["source_visibility"] == "public"
    if is_public:
        urls.append(("public repository HTML", REPOSITORY_URL))
    for label, url in urls:
        try:
            status, body = get_url(url)
        except Exception as exc:
            errors.append(f"{label} request failed for {url}: {exc}")
            continue
        if status != 200:
            errors.append(f"{label} returned HTTP {status}: {url}")
        else:
            responses[label] = body
    if is_public:
        if "app overview" in responses and not _has_html_anchor(
            responses["app overview"], REPOSITORY_URL
        ):
            errors.append(
                f"app overview is missing an exact visible source anchor: {REPOSITORY_URL}"
            )
    else:
        private_reference_forms = {
            REPOSITORY_URL.casefold(),
            urllib.parse.quote(REPOSITORY_URL, safe="").casefold(),
            f"github.com/{config['repository']}".casefold(),
        }
        for label in ("portal", "app overview", "app runtime", "app.json"):
            body = responses.get(label, "")
            folded = urllib.parse.unquote(unescape(body)).casefold()
            if any(reference in folded for reference in private_reference_forms):
                errors.append(f"private repository URL is leaked in public {label}")
    if "app.json" in responses:
        try:
            app_metadata = json.loads(
                responses["app.json"], object_pairs_hook=_reject_duplicate_keys
            )
        except (json.JSONDecodeError, ValueError) as exc:
            errors.append(f"app.json is not valid unambiguous JSON: {exc}")
        else:
            if not isinstance(app_metadata, dict):
                errors.append("app.json must contain a JSON object")
            else:
                if app_metadata.get("url") != config["overview_url"]:
                    errors.append(
                        "app.json url must exactly equal the pinned overview URL"
                    )
                # Both published catalogue metadata schemas are supported. If both
                # runtime fields are present, neither may contradict the mapping.
                runtime_fields = [
                    key for key in ("applicationUrl", "runtime") if key in app_metadata
                ]
                if not runtime_fields:
                    # Older private editions identify only the overview in JSON.
                    # Bind their configured runtime through a named visible overview link.
                    parser = _VisibleMarkup()
                    parser.feed(responses.get("app overview", ""))
                    parser.close()
                    linked = any(
                        item["text"].strip()
                        and urllib.parse.urljoin(config["overview_url"], item["href"])
                        == config["runtime_url"]
                        for item in parser.anchors
                        if item["href"]
                    )
                    if not linked:
                        errors.append(
                            "metadata omits runtime; overview must visibly link the pinned runtime URL"
                        )
                for key in runtime_fields:
                    if app_metadata[key] != config["runtime_url"]:
                        errors.append(
                            f"app.json {key} must exactly equal {config['runtime_url']!r}"
                        )
                public_source = app_metadata.get("publicSource")
                if is_public and public_source != REPOSITORY_URL:
                    errors.append(
                        f"app.json publicSource must exactly equal {REPOSITORY_URL!r}"
                    )
                elif not is_public and public_source not in (None, ""):
                    errors.append(
                        "app.json must not publish a publicSource URL for a private mapping"
                    )
    if not token:
        errors.append(
            "GH_TOKEN is required for authenticated read-only repository metadata checks"
        )
    else:
        get_repo = get_repo or _github_repo_get
        try:
            metadata = get_repo(config["repository"], token)
        except Exception as exc:
            errors.append(
                f"GitHub repository metadata request failed for {config['repository']}: {exc}"
            )
        else:
            errors.extend(validate_github_metadata(metadata, config))
    return errors


def _has_html_anchor(markup: str, url: str) -> bool:
    parser = _VisibleMarkup()
    parser.feed(markup)
    parser.close()
    return any(item["href"] == url and item["text"].strip() for item in parser.anchors)


def run(*, live: bool = False, config_path: Path = CONFIG_PATH) -> list[str]:
    try:
        config = load_config(config_path)
    except ValueError as exc:
        return [str(exc)]
    try:
        readme = (config_path.parent / "README.md").read_text(encoding="utf-8")
    except OSError as exc:
        return [f"cannot read README.md: {exc}"]
    errors = check_readme(readme, config)
    if live:
        errors.extend(check_live(config))
    return errors


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live",
        action="store_true",
        help="make bounded HTTPS and read-only GitHub API checks",
    )
    args = parser.parse_args(argv)
    errors = run(live=args.live)
    if errors:
        for error in errors:
            print("FAIL: " + error, file=sys.stderr)
        return 1
    print(
        "Traceability checks passed."
        + (
            " Live endpoints and GitHub metadata verified."
            if args.live
            else " Local README and mapping verified."
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
