"""Check installed package isolation, exact assets, and real loopback HTTP."""

from __future__ import annotations

import argparse
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def require(condition: bool, message: str) -> None:
    """Keep wheel verification active when Python optimization is enabled."""
    if not condition:
        raise ValueError(message)


PROGRAM = r"""
import http.client
import json
import sys
import threading
from pathlib import Path

def require(condition, detail):
    if not condition:
        raise ValueError(detail)

sys.path.insert(0, sys.argv[1])
import zephyrtrade
from zephyrtrade.app import LocalServer, WEB_ROOT
require(zephyrtrade.__version__ == '1.1.0', 'installed package version')
require(Path(zephyrtrade.__file__).is_relative_to(Path(sys.argv[1])),
        'package must be imported from the isolated installation')
for name in ('index.html', 'styles.css', 'engine.js', 'app.js', 'snapshot.js'):
    require((WEB_ROOT / name).is_file(), 'missing installed asset: ' + name)
server = LocalServer(0)
thread = threading.Thread(target=server.serve_forever, daemon=True)
thread.start()
port = server.server_address[1]
try:
    conn = http.client.HTTPConnection('127.0.0.1', port, timeout=10)
    conn.request('GET', '/api/health')
    response = conn.getresponse()
    data = json.loads(response.read())
    require(response.status == 200 and data['version'] == '1.1.0', data)
    for endpoint in ('/', '/styles.css', '/engine.js', '/app.js', '/snapshot.js'):
        conn.request('GET', endpoint)
        response = conn.getresponse()
        body = response.read()
        require(response.status == 200 and body, endpoint)
    inputs = dict(capacity=30, da=400, up=600, down=200, hours=1,
                  scenarios=[2, 8, 20], probabilities=[.2, .5, .3])
    conn.request('POST', '/api/optimize', body=json.dumps(inputs), headers={
        'Content-Type': 'application/json',
        'Origin': f'http://127.0.0.1:{port}',
    })
    response = conn.getresponse()
    result = json.loads(response.read())
    require(response.status == 200, result)
    require(abs(result['offer_mw'] - 8) < 1e-7, result)
    require(abs(result['expected_revenue_dkk'] - 3200) < 1e-7, result)
    conn.close()
    sys.stdout.write(json.dumps({
        'status': 'PASS',
        'installed_import': str(zephyrtrade.__file__),
        'version': zephyrtrade.__version__,
        'verified': 'five static assets, health and real loopback SciPy solve',
        'solution': result,
        'limitations': (
            'Existing system scientific dependencies reused; not a clean '
            'dependency-resolution environment, normal browser session, '
            'Windows execution or deployment.'
        ),
    }, indent=2) + '\n')
finally:
    server.shutdown()
    server.server_close()
    thread.join(5)
"""


def verify_wheel(root: Path) -> None:
    """Verify a repository-owned wheel before installing it without dependencies."""
    root = root.resolve(strict=True)
    wheel = (root / "dist/zephyrtrade-1.1.0-py3-none-any.whl").resolve(strict=True)
    require(wheel.is_relative_to(root), "The wheel must remain inside its repository")
    with zipfile.ZipFile(wheel) as archive:
        require(archive.testzip() is None, "Wheel ZIP integrity failed")
        paths = [
            "zephyrtrade/" + path.relative_to(root / "src/zephyrtrade").as_posix()
            for path in (root / "src/zephyrtrade").rglob("*")
            if path.is_file() and path.suffix in {".py", ".html", ".css", ".js"}
        ]
        require(bool(paths), "No Python or browser sources were found")
        for relative in paths:
            require(
                archive.read(relative) == (root / "src" / relative).read_bytes(),
                "Wheel source mismatch: " + relative,
            )
    sys.stdout.write(f"Wheel matches all {len(paths)} final Python/web source files.\n")
    with tempfile.TemporaryDirectory(prefix="zephyr-wheel-check-") as directory:
        subprocess.run(  # noqa: S603 -- current Python installs only the verified local wheel; no index or dependencies
            [
                sys.executable,
                "-m",
                "pip",
                "install",
                "--no-index",
                "--no-deps",
                "--target",
                directory,
                str(wheel),
            ],
            check=True,
            timeout=120,
        )
        subprocess.run(  # noqa: S603 -- current Python runs the fixed verifier; the temporary path is a separate argument
            [sys.executable, "-c", PROGRAM, directory],
            check=True,
            cwd=directory,
            timeout=120,
        )
    sys.stdout.write(
        "Wheel ZIP integrity, exact-source parity and installed-package "
        "HTTP smoke: PASS.\n"
    )


def main(argv: list[str] | None = None) -> None:
    """Verify the checked-out package or an explicitly supplied repository root."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[4]
    )
    args = parser.parse_args(argv)
    verify_wheel(args.root)


if __name__ == "__main__":
    main()
