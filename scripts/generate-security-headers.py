#!/usr/bin/env python3
"""Generate deployment header values for the audited standalone HTML.

This writes an integration artifact. It never changes a server or CDN.
Run after the final HTML build; serve the headers with those exact bytes.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
from html.parser import HTMLParser
from pathlib import Path


class ScriptCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.in_script = False
        self.external = False
        self.parts: list[str] = []
        self.inline_scripts: list[str] = []
        self.external_sources: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        values = dict(attrs)
        self.in_script = True
        self.external = "src" in values
        self.parts = []
        if self.external:
            self.external_sources.append(values.get("src") or "")

    def handle_data(self, data: str) -> None:
        if self.in_script:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() != "script" or not self.in_script:
            return
        if not self.external:
            self.inline_scripts.append("".join(self.parts))
        self.in_script = False
        self.parts = []


def document_headers(path: Path) -> dict[str, object]:
    raw = path.read_bytes()
    # HTML input preprocessing normalizes CRLF and CR before CSP validation.
    html = raw.decode("utf-8-sig").replace("\r\n", "\n").replace("\r", "\n")
    parser = ScriptCollector()
    parser.feed(html)
    parser.close()
    if parser.in_script:
        raise ValueError("An inline script is not closed.")
    if len(parser.inline_scripts) != 3:
        raise ValueError(f"Expected the audited three inline scripts; found {len(parser.inline_scripts)}.")
    hashes = [
        "'sha256-" + base64.b64encode(hashlib.sha256(script.encode("utf-8")).digest()).decode("ascii") + "'"
        for script in parser.inline_scripts
    ]
    scripts = "'self' " + " ".join(dict.fromkeys(hashes))
    directives = [
        "default-src 'self'",
        "script-src " + scripts,
        "script-src-elem " + scripts,
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: blob:",
        "font-src 'self'",
        "connect-src 'self'",
        "worker-src 'self' blob:",
        "object-src 'none'",
        "base-uri 'self'",
        "frame-ancestors 'none'",
        "form-action 'self'",
    ]
    return {
        "document": path.name,
        "document_sha256": hashlib.sha256(raw).hexdigest(),
        "inline_script_hashes": hashes,
        "external_script_sources": parser.external_sources,
        "headers": {
            "Content-Security-Policy": "; ".join(directives),
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "camera=(), microphone=(), geolocation=()",
        },
        "integration_status": "Not deployed. Apply through the actual origin/CDN header configuration, then run the release verification suite.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("html", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    artifact = document_headers(args.html)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(artifact, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "document_sha256": artifact["document_sha256"], "script_count": len(artifact["inline_script_hashes"]), "external_script_count": len(artifact["external_script_sources"])}))


if __name__ == "__main__":
    main()
