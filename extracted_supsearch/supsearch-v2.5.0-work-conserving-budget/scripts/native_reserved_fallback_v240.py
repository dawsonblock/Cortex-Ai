#!/usr/bin/env python3
"""Qualify the REAL nonempty-concept / reserved-raw-fallback path.

This is a native smoke, not a benchmark or proof of generalization. Unlike
v2.3's empty-library smoke, this probe requires that the concept solver was
entered, exhausted its tiny allocation, and handed a positive budget to the
raw solver. Any missing event, fake allocation or missing binary fails closed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

from evidence_integrity import strict_jsonl
from qualified_pipeline import binary_format
from search_budget_audit_v230 import audit as budget_audit

TOTAL = 20
RESERVE = 95
EXPECTED_COMPOSED_CAP = 1
SEED_NAME = 'probe_seed_mul'


def validate_native_probe(ledger: Path, library: Path, *, require_terminal: bool = True) -> dict:
    """Audit a ledger produced by a native command; NOT proof of execution alone."""
    receipt = budget_audit(ledger)
    events = strict_jsonl(ledger, max_bytes=8*1024*1024)
    starts = [r for r in events if r.get('event') == 'start']
    trains = [r for r in events if r.get('event') == 'train_attempt']
    if len(starts) != 1 or len(trains) != 1:
        raise ValueError('expected one native session and exactly one training attempt')
    s, t = starts[0], trains[0]
    if (s.get('initial_concepts') != 1 or s.get('max_built') != TOTAL
        or s.get('raw_reserve_pct') != RESERVE):
        raise ValueError('probe requires exactly one preloaded concept and frozen budget configuration')
    if t.get('composed_limit') != EXPECTED_COMPOSED_CAP:
        raise ValueError('nonempty concept probe did not reserve the intended raw budget')
    if t.get('kind') != 'raw':
        raise ValueError('probe did not enter raw fallback')
    if not 0 < t.get('composed_built', -1) <= EXPECTED_COMPOSED_CAP:
        raise ValueError('concept search did not consume positive bounded work')
    if not 0 < t.get('raw_built', -1) <= t['raw_limit']:
        raise ValueError('raw fallback did not perform positive bounded work')
    if t['raw_limit'] < TOTAL - EXPECTED_COMPOSED_CAP:
        raise ValueError('raw fallback reservation was starved')
    if require_terminal and events[-1].get('event') != 'session_completed':
        raise ValueError('probe session incomplete')
    if not library.is_file() or library.is_symlink():
        raise ValueError('concept library missing or symlinked')
    active = [r for r in library.read_text(encoding='utf8').splitlines() if r and not r.startswith('#')]
    if not active or not active[0].startswith(SEED_NAME + '\t2\t'):
        raise ValueError('original preloaded concept was replaced or lost')
    return {
        'schema': 'supsearch-native-reserved-fallback-v240',
        'scope': 'one nonempty-library native fallback smoke; not learning or independent transfer proof',
        'initial_concepts': 1,
        'concept_search_executed': True,
        'raw_fallback_executed': True,
        'composed_built': t['composed_built'],
        'raw_built': t['raw_built'],
        'shared_built': t['built'],
        'max_built': TOTAL,
        'raw_reserve_pct': RESERVE,
        'self_reported_budget_audited': receipt['self_reported_allocation_consistent'],
    }


def run_native_probe(binary: Path, source: Path, output: Path, *, timeout: int = 90) -> dict:
    binary = binary.resolve(strict=True)
    source = source.resolve(strict=True)
    if binary_format(binary) not in ('elf', 'mach_o', 'pe'):
        raise ValueError('native Rust executable required; scripts and stubs are not accepted')
    if not source.joinpath('Cargo.toml').is_file():
        raise ValueError('source tree missing Cargo.toml')
    if not 1 <= timeout <= 3600:
        raise ValueError('invalid timeout')
    if output.exists():
        raise ValueError('output already exists; rerun into a fresh directory')
    if output.resolve().is_relative_to(source) or source.is_relative_to(output.resolve()):
        raise ValueError('native qualification output must be outside the source tree')
    output.mkdir(mode=0o700)
    task_dir = output/'tasks'
    task_dir.mkdir()
    # Deliberately difficult task, different from the supplied multiplication
    # seed. A 1-expansion concept budget must give raw search the next chance.
    for original, alias in [('ctre_rev','probe_train'), ('cnat_mul','probe_dev')]:
        shutil.copyfile(source/'bench'/f'{original}.tsk', task_dir/f'{alias}.tsk')
    seed_src = source/'examples'/'v240_preloaded_library.tsv'
    if seed_src.is_symlink() or not seed_src.is_file():
        raise ValueError('preloaded library fixture unavailable')
    lib = output/'preloaded_concepts.tsv'
    shutil.copyfile(seed_src, lib)
    before = hashlib.sha256(lib.read_bytes()).hexdigest()
    journal = output/'native_probe.jsonl'
    cmd = [str(binary), 'learn', str(task_dir), '--train', 'probe_train',
           '--dev', 'probe_dev', '--library', str(lib), '--ledger', str(journal),
           '--rounds','1', '--budget','0.2', '--max-size','4', '--fuel','1000',
           '--top-tasks','1','--max-candidates','1','--max-arity','1',
           '--require-native-mined','true', '--max-built',str(TOTAL),
           '--raw-reserve-pct',str(RESERVE), '--shared-time-budget', 'true']
    try:
        completed = subprocess.run(cmd, cwd=source, capture_output=True, text=True,
                                   timeout=timeout, check=False)
    except subprocess.TimeoutExpired as exc:
        (output/'FAILURE.txt').write_text('Native probe timed out.\n')
        raise RuntimeError('native fallback probe timed out') from exc
    (output/'native_probe.log').write_text('COMMAND: '+repr(cmd)+'\nEXIT: '+str(completed.returncode)
        +'\nSTDOUT:\n'+completed.stdout+'\nSTDERR:\n'+completed.stderr,encoding='utf8')
    if completed.returncode:
        raise RuntimeError('native fallback probe failed (see native_probe.log)')
    report = validate_native_probe(journal, lib)
    report['binary_sha256'] = hashlib.sha256(binary.read_bytes()).hexdigest()
    report['initial_library_sha256'] = before
    report['native_executable_ran'] = True
    report['concept_library_after_probe_modified'] = before != hashlib.sha256(lib.read_bytes()).hexdigest()
    (output/'probe_qualification.json').write_text(json.dumps(report, sort_keys=True, indent=2)+'\n')
    return report


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary', type=Path, required=True)
    p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--out', type=Path, required=True)
    p.add_argument('--timeout', type=int, default=90)
    ns = p.parse_args(argv)
    try:
        print(json.dumps(run_native_probe(ns.binary, ns.source, ns.out, timeout=ns.timeout), indent=2))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'nonempty-library native fallback qualification FAILED: {exc}', file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
