#!/usr/bin/env python3
"""Evaluator-held HMAC-SHA256 sealing of a previously verified external replay.

This is authenticated evidence only if the secret is held by an independent,
trustworthy evaluator. It cannot prove binary provenance, task independence,
or valid learning. Never ship the key with the archived project or run.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import hmac
import json
import os
from pathlib import Path
import stat
import sys
from typing import Any

from evidence_integrity import strict_json_loads
from external_replay import verify_result

SCHEMA = 'supsearch-attested-replay-v1'
EXCLUDE = 'attestation.json'
MAX_FILES = 1024
MAX_FILE_SIZE = 64 * 1024 * 1024


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _digest(path: Path) -> str:
    h = sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def _load_key(path: Path, output: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise ValueError('HMAC key must be a non-symlink regular file')
    if path.resolve().is_relative_to(output.resolve()):
        raise ValueError('evaluator secret must be stored outside the replay directory')
    if os.name == 'posix' and (path.stat().st_mode & 0o077):
        raise ValueError('evaluator secret must have mode 0600 or stricter')
    if path.stat().st_size != 32:
        raise ValueError('HMAC key must contain exactly 32 random bytes')
    return path.read_bytes()


def _inventory(directory: Path) -> list[dict[str, object]]:
    if directory.is_symlink() or not directory.is_dir():
        raise ValueError('replay root must be a non-symlink directory')
    result: list[dict[str, object]] = []
    for path in sorted(directory.rglob('*')):
        if path.is_symlink():
            raise ValueError(f'symlink forbidden in sealed replay: {path}')
        if path.is_dir():
            continue
        if not path.is_file():
            raise ValueError(f'non-regular evidence entry: {path}')
        rel = path.relative_to(directory).as_posix()
        if rel == EXCLUDE:
            continue
        size = path.stat().st_size
        if size > MAX_FILE_SIZE:
            raise ValueError(f'evidence file larger than {MAX_FILE_SIZE}: {rel}')
        result.append({'path': rel, 'sha256': _digest(path), 'size': size})
        if len(result) > MAX_FILES:
            raise ValueError('evidence tree exceeds maximum file count')
    return result


def _unsigned(directory: Path, key: bytes) -> dict:
    verified = verify_result(directory)  # Recompute all protocol evidence before sealing.
    files = _inventory(directory)
    return {'schema': SCHEMA, 'trial_key': verified['trial_key'],
            'key_id': sha256(key).hexdigest()[:16], 'files': files,
            'evidence_status': 'authenticated_replay_not_independent_validation'}


def init_key(path: Path) -> dict:
    if not path.parent.is_dir() or path.is_symlink():
        raise ValueError('key parent must exist and key target cannot be a symlink')
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(os.urandom(32))
        f.flush()
        os.fsync(f.fileno())
    return {'key_created': str(path), 'key_must_remain_evaluator_private': True}


def seal(directory: Path, key_path: Path) -> dict:
    key = _load_key(key_path, directory)
    attestation_path = directory / EXCLUDE
    if attestation_path.exists() or attestation_path.is_symlink():
        raise ValueError('attestation already exists: refusing overwrite')
    metadata = _unsigned(directory, key)
    tag = hmac.new(key, _canonical(metadata), sha256).hexdigest()
    attestation = {**metadata, 'hmac_sha256': tag}
    fd = os.open(attestation_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'wb') as f:
        f.write(_canonical(attestation) + b'\n')
        f.flush()
        os.fsync(f.fileno())
    return {'sealed': True, 'trial_key': metadata['trial_key'], 'key_id': metadata['key_id'],
            'claimed_independent_validation': False}


def verify(directory: Path, key_path: Path) -> dict:
    key = _load_key(key_path, directory)
    path = directory / EXCLUDE
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1_000_000:
        raise ValueError('missing/unsafe attestation')
    stored = strict_json_loads(path.read_text(encoding='utf8'))
    if not isinstance(stored, dict) or type(stored.get('hmac_sha256')) is not str:
        raise ValueError('invalid attestation format')
    expected = _unsigned(directory, key)
    signed = {k: v for k, v in stored.items() if k != 'hmac_sha256'}
    if signed != expected or not hmac.compare_digest(stored['hmac_sha256'], hmac.new(key, _canonical(expected), sha256).hexdigest()):
        raise ValueError('HMAC or evidence-manifest mismatch')
    return {'authenticated_evidence': True, 'trial_key': expected['trial_key'],
            'key_id': expected['key_id'], 'claimed_independent_validation': False}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    x = sub.add_parser('init-key'); x.add_argument('--key', type=Path, required=True)
    for cmd in ('seal', 'verify'):
        p = sub.add_parser(cmd)
        p.add_argument('--out', type=Path, required=True)
        p.add_argument('--key', type=Path, required=True)
    ns = parser.parse_args(argv)
    try:
        if ns.operation == 'init-key': result = init_key(ns.key)
        elif ns.operation == 'seal': result = seal(ns.out, ns.key)
        else: result = verify(ns.out, ns.key)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except (ValueError, OSError, KeyError, TypeError) as error:
        print(f'attested replay rejected: {error}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
