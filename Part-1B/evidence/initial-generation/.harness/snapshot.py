"""Back up a generation: python .harness/snapshot.py initial-generation | final-generation

Copies the code under evaluation into evidence/<name>/ and writes evidence/<name>.sha256 (per-file + overall digest).
"""

from __future__ import annotations

import hashlib
import shutil
import sys
from pathlib import Path

from common import ROOT

INCLUDE = ["src", "tests", ".harness", "evals/run_eval.py", "pyproject.toml"]
SKIP = {"__pycache__", ".pytest_cache", ".ruff_cache"}


def _files(base: Path) -> list[Path]:
    if base.is_file():
        return [base]
    return sorted(p for p in base.rglob("*") if p.is_file() and not (set(p.parts) & SKIP) and p.suffix != ".pyc")


def snapshot(name: str) -> str:
    target = ROOT / "evidence" / name
    if target.exists():
        shutil.rmtree(target)
    lines, overall = [], hashlib.sha256()
    for item in INCLUDE:
        for path in _files(ROOT / item):
            rel = path.relative_to(ROOT)
            dest = target / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, dest)
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            overall.update(f"{rel.as_posix()}:{digest}\n".encode())
            lines.append(f"{digest}  {rel.as_posix()}")
    lines.append(f"{overall.hexdigest()}  OVERALL ({len(lines)} files)")
    (ROOT / "evidence" / f"{name}.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return overall.hexdigest()


if __name__ == "__main__":
    print(snapshot(sys.argv[1]))
