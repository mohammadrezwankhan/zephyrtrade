"""Tests for the end-to-end pipeline utilities."""

from __future__ import annotations

import hashlib

import pytest

from zephyrtrade.pipeline import file_sha256


def test_file_sha256_matches_standard_library(tmp_path) -> None:
    """The run manifest digest should be stable across chunk sizes."""
    source = tmp_path / "result.bin"
    content = b"zephyrtrade\x00deterministic-artifact" * 17
    source.write_bytes(content)

    expected = hashlib.sha256(content).hexdigest()
    assert file_sha256(source, chunk_size=7) == expected
    assert file_sha256(source, chunk_size=4096) == expected


def test_file_sha256_rejects_invalid_inputs(tmp_path) -> None:
    """Missing files and nonpositive chunk sizes should fail explicitly."""
    with pytest.raises(ValueError, match="positive"):
        file_sha256(tmp_path / "missing", chunk_size=0)
    with pytest.raises(FileNotFoundError, match="missing file"):
        file_sha256(tmp_path / "missing")
