"""Exercise SVG well-formedness and encoding-aware entity rejection."""

from __future__ import annotations

from pathlib import Path

import pytest
from defusedxml.common import DTDForbidden
from defusedxml.ElementTree import ParseError

from scripts.portfolio.validate_guide import validate_svg

ENCODINGS = [
    ("utf-8", "UTF-8"),
    ("utf-16", "UTF-16"),
    ("utf-16-le", "UTF-16LE"),
    ("utf-16-be", "UTF-16BE"),
]


@pytest.mark.parametrize(("encoding", "xml_encoding"), ENCODINGS)
def test_svg_accepts_safe_text_in_supported_xml_encodings(
    tmp_path: Path, encoding: str, xml_encoding: str
) -> None:
    svg = tmp_path / "safe.svg"
    xml = (
        f'<?xml version="1.0" encoding="{xml_encoding}"?>'
        '<svg xmlns="http://www.w3.org/2000/svg">'
        "<!-- A literal &lt;!DOCTYPE in explanatory text is safe. -->"
        "<text>Safe &amp; ordinary text</text></svg>"
    )
    svg.write_bytes(xml.encode(encoding))
    validate_svg(svg)


@pytest.mark.parametrize(("encoding", "xml_encoding"), ENCODINGS)
@pytest.mark.parametrize(
    "declaration",
    [
        '<!DOCTYPE svg [<!ENTITY internal "expanded text">]>',
        '<!DOCTYPE svg [<!ENTITY external SYSTEM "file:///etc/passwd">]>',
        '<!DOCTYPE svg SYSTEM "https://example.invalid/external.dtd">',
        '<!DOCTYPE svg [<!ENTITY % parameter SYSTEM "file:///etc/passwd">%parameter;]>',
    ],
)
def test_svg_rejects_dtds_and_entities_before_expansion_in_all_encodings(
    tmp_path: Path, encoding: str, xml_encoding: str, declaration: str
) -> None:
    svg = tmp_path / "untrusted.svg"
    xml = (
        f'<?xml version="1.0" encoding="{xml_encoding}"?>'
        + declaration
        + '<svg xmlns="http://www.w3.org/2000/svg"><text>unchanged</text></svg>'
    )
    svg.write_bytes(xml.encode(encoding))
    with pytest.raises(DTDForbidden):
        validate_svg(svg)


@pytest.mark.parametrize("xml", ["<svg><text></svg>", "<svg/ ><text/>", ""])
def test_svg_rejects_malformed_xml(tmp_path: Path, xml: str) -> None:
    svg = tmp_path / "malformed.svg"
    svg.write_text(xml, encoding="utf-8")
    with pytest.raises(ParseError):
        validate_svg(svg)
