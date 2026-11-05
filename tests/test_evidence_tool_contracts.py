"""Verify bounded local receipt execution and wheel source confinement."""

from __future__ import annotations

import json
import sys
import zipfile
from pathlib import Path

import pytest

from docs.champion.evidence.tools import run_check, verify_wheel_install


def test_command_receipt_preserves_arguments_environment_and_interpreter(
    tmp_path: Path,
) -> None:
    out = tmp_path / "receipts"
    argument = "$(must-remain-literal); spaces and --flags"
    program = (
        "import json,os,sys; print(json.dumps({'prefix':sys.prefix,"
        "'argument':sys.argv[1],'source':os.environ['PYTHONPATH']}))"
    )
    assert (
        run_check.main(
            [
                "--output",
                str(out),
                "success",
                str(tmp_path),
                sys.executable,
                "-c",
                program,
                argument,
            ]
        )
        == 0
    )
    output = json.loads((out / "success.log").read_text())
    assert output == {
        "prefix": sys.prefix,
        "argument": argument,
        "source": str(tmp_path / "src"),
    }
    receipt = json.loads((out / "commands.jsonl").read_text())
    assert receipt["exit_code"] == 0
    assert receipt["command"] == [sys.executable, "-c", program, argument]
    assert receipt["cwd"] == str(tmp_path)


def test_command_receipt_retains_failure_and_timeout_output(tmp_path: Path) -> None:
    arguments = ["--output", str(tmp_path)]
    assert (
        run_check.main(
            [
                *arguments,
                "failure",
                str(tmp_path),
                sys.executable,
                "-c",
                "print('observed failure'); raise SystemExit(7)",
            ]
        )
        == 7
    )
    assert "observed failure" in (tmp_path / "failure.log").read_text()
    assert (
        run_check.main(
            [
                *arguments,
                "--timeout",
                ".2",
                "timeout",
                str(tmp_path),
                sys.executable,
                "-c",
                "import time; print('started', flush=True); time.sleep(2)",
            ]
        )
        == 124
    )
    output = (tmp_path / "timeout.log").read_text()
    assert "started" in output
    assert "exceeded 0.2 seconds" in output
    receipts = [
        json.loads(line)
        for line in (tmp_path / "commands.jsonl").read_text().splitlines()
    ]
    assert [item["exit_code"] for item in receipts] == [7, 124]


@pytest.mark.parametrize("label", ["../escape", ".", "name/escape", ""])
def test_command_receipt_rejects_path_like_labels(tmp_path: Path, label: str) -> None:
    with pytest.raises(SystemExit) as error:
        run_check.main(
            ["--output", str(tmp_path), label, str(tmp_path), sys.executable]
        )
    assert error.value.code == 2
    assert not (tmp_path / "commands.jsonl").exists()


@pytest.mark.parametrize("timeout", ["0", "-1", "2401", "nan", "inf"])
def test_command_receipt_rejects_unbounded_timeouts(
    tmp_path: Path, timeout: str
) -> None:
    with pytest.raises(SystemExit) as error:
        run_check.main(
            [
                "--output",
                str(tmp_path),
                "--timeout",
                timeout,
                "invalid",
                str(tmp_path),
                sys.executable,
            ]
        )
    assert error.value.code == 2


@pytest.mark.parametrize("command", [[], ["missing-zephyr-executable-for-test"]])
def test_command_receipt_requires_an_explicit_existing_executable(
    tmp_path: Path,
    command: list[str],
) -> None:
    with pytest.raises(SystemExit) as error:
        run_check.main(["--output", str(tmp_path), "invalid", str(tmp_path), *command])
    assert error.value.code == 2


def test_command_receipt_requires_an_existing_directory(tmp_path: Path) -> None:
    file = tmp_path / "file"
    file.touch()
    with pytest.raises(SystemExit) as error:
        run_check.main(
            ["--output", str(tmp_path), "invalid", str(file), sys.executable]
        )
    assert error.value.code == 2
    with pytest.raises(FileNotFoundError):
        run_check.main(
            [
                "--output",
                str(tmp_path),
                "missing",
                str(tmp_path / "missing"),
                sys.executable,
            ]
        )


@pytest.mark.parametrize("source_text", [None, "current source"])
def test_wheel_verifier_rejects_empty_or_stale_sources_before_install(
    tmp_path: Path,
    source_text: str | None,
) -> None:
    root = tmp_path / "checkout"
    wheel = root / "dist/zephyrtrade-1.1.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    source = root / "src/zephyrtrade/__init__.py"
    source.parent.mkdir(parents=True)
    if source_text is not None:
        source.write_text(source_text)
    with zipfile.ZipFile(wheel, "w") as archive:
        archive.writestr("zephyrtrade/__init__.py", "stale source")
    with pytest.raises(ValueError, match=r"No Python|source mismatch"):
        verify_wheel_install.verify_wheel(root)


def test_wheel_verifier_refuses_a_wheel_outside_the_checkout(tmp_path: Path) -> None:
    outside = tmp_path / "outside.whl"
    outside.touch()
    root = tmp_path / "checkout"
    wheel = root / "dist/zephyrtrade-1.1.0-py3-none-any.whl"
    wheel.parent.mkdir(parents=True)
    wheel.symlink_to(outside)
    with pytest.raises(ValueError, match="inside its repository"):
        verify_wheel_install.verify_wheel(root)
