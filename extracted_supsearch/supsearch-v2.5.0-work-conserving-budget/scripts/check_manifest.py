#!/usr/bin/env python3
"""Verify a local SHA-256 inventory and detect missing, modified or unexpected files.

This inventory is NOT authenticated and does NOT defend against an attacker who
can replace both the source and the manifest. Ignore build/output caches only.
"""
from pathlib import Path
from hashlib import sha256
import re
import sys

IGNORED_DIRECTORIES = {'.git', '.venv', '__pycache__', '.pytest_cache',
                       '.mypy_cache', '.ruff_cache', 'target', 'out'}
IGNORED_FILES = {'MANIFEST.sha256', '.DS_Store'}


def check(root: Path) -> dict:
    manifest = root / 'MANIFEST.sha256'
    missing, mismatched, unsafe, unexpected = [], [], [], []
    seen = set()
    for line in manifest.read_text(encoding='utf8').splitlines():
        if not line.strip():
            continue
        digest, sep, rel = line.partition('  ')
        if not sep or not re.fullmatch('[0-9a-f]{64}', digest):
            raise ValueError(f'invalid manifest record: {line!r}')
        p = Path(rel)
        if not rel or p.is_absolute() or '..' in p.parts or rel in seen or rel in IGNORED_FILES:
            raise ValueError(f'unsafe or duplicated manifest path: {rel!r}')
        seen.add(rel)
        path = root / rel
        if path.is_symlink():
            unsafe.append(rel)
        elif not path.is_file():
            missing.append(rel)
        elif sha256(path.read_bytes()).hexdigest() != digest:
            mismatched.append(rel)
    for path in root.rglob('*'):
        rel = path.relative_to(root)
        if set(rel.parts) & IGNORED_DIRECTORIES:
            continue
        if rel.name in IGNORED_FILES:
            continue
        if path.is_symlink():
            unsafe.append(rel.as_posix())
        elif path.is_file() and rel.as_posix() not in seen:
            unexpected.append(rel.as_posix())
    return {'checked': len(seen), 'missing': missing, 'mismatched': mismatched,
            'unexpected': sorted(unexpected), 'unsafe_symlinks': sorted(set(unsafe)),
            'valid': bool(seen) and not (missing or mismatched or unexpected or unsafe)}


if __name__ == '__main__':
    package = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parents[1]
    result = check(package)
    print(result)
    raise SystemExit(0 if result['valid'] else 2)
