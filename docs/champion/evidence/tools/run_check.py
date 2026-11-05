"""Run an explicitly supplied local command and preserve its bounded receipt."""

from __future__ import annotations

import argparse
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys
import time


def main(argv: list[str] | None = None) -> int:
    """Execute only the caller's command vector, with no shell or remote inputs."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=pathlib.Path, default=pathlib.Path("/mnt/data/work/evidence")
    )
    parser.add_argument("--timeout", type=float, default=2400)
    parser.add_argument("label")
    parser.add_argument("cwd", type=pathlib.Path)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", args.label):
        parser.error("The receipt label must be a simple nonempty file name.")
    if not 0 < args.timeout <= 2400:
        parser.error("The command timeout must be positive and at most 2400 seconds.")
    cwd = args.cwd.resolve(strict=True)
    if not cwd.is_dir():
        parser.error("The command working directory must be an existing directory.")
    command: list[str] = args.command
    if not command:
        parser.error("Supply an explicit command and its arguments.")
    executable = command[0]
    if pathlib.Path(executable).parent != pathlib.Path() or "/" in executable:
        executable = str((cwd / executable).absolute())
    resolved = shutil.which(executable)
    if resolved is None:
        parser.error("The requested command must resolve to a local executable.")
    # Keep virtual-environment executable symlinks: their path selects the environment.
    command = [str(pathlib.Path(resolved).absolute()), *command[1:]]
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    env = os.environ.copy()
    env["PYTHONPATH"] = str(cwd / "src")
    env.update(
        {"MPLBACKEND": "Agg", "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1"}
    )
    try:
        completed = subprocess.run(  # noqa: S603 -- explicit caller command; resolved executable, no shell
            command,
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=args.timeout,
        )
        output, exit_code = completed.stdout, completed.returncode
    except subprocess.TimeoutExpired as exc:
        partial = exc.stdout or ""
        output = (
            partial.decode("utf-8", "replace")
            if isinstance(partial, bytes)
            else partial
        )
        output += f"\nCommand exceeded {args.timeout:g} seconds.\n"
        exit_code = 124
    (out / f"{args.label}.log").write_text(output)
    record = {
        "id": args.label,
        "cwd": str(cwd),
        "command": command,
        "timestamp_utc": datetime.datetime.now(datetime.UTC).isoformat(),
        "exit_code": exit_code,
        "duration_seconds": round(time.perf_counter() - start, 3),
        "log": f"{args.label}.log",
    }
    with (out / "commands.jsonl").open("a") as stream:
        stream.write(json.dumps(record) + "\n")
    sys.stdout.write(json.dumps(record) + "\n" + output[-15000:] + "\n")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
