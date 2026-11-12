"""Atomic file helpers."""

import os
import tempfile
import time
from pathlib import Path

from todo.domain.errors import StorageError

__all__ = ["atomic_write_text", "read_bytes_if_exists"]


def read_bytes_if_exists(path: Path) -> bytes | None:
    """Return file bytes, or ``None`` when the file does not exist."""
    try:
        return path.read_bytes()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise StorageError(f"cannot read data file: {exc.strerror or 'I/O error'}") from exc


def _replace_with_retry(source: Path, target: Path, retries: int, delay: float) -> None:
    for attempt in range(retries + 1):
        try:
            os.replace(source, target)
        except PermissionError:
            if attempt == retries:
                raise
            time.sleep(delay)
        else:
            return


def atomic_write_text(path: Path, text: str, *, retries: int = 3, delay: float = 0.05) -> None:
    """Write ``text`` to ``path`` atomically (temp file + fsync + replace)."""
    temp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor, temp_name = tempfile.mkstemp(
            dir=path.parent, prefix=f".{path.name}.", suffix=".tmp"
        )
        temp_path = Path(temp_name)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        _replace_with_retry(temp_path, path, retries, delay)
    except OSError as exc:
        raise StorageError(f"cannot write data file: {exc.strerror or 'I/O error'}") from exc
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
