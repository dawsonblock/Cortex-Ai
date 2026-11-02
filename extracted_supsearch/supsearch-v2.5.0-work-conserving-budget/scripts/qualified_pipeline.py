#!/usr/bin/env python3
"""Governed local supsearch experiments (stdlib only).

Do not confuse local folder separation with independent evaluator custody.
No cryptographic signing, remote attestation, OS isolation or universal proofs.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any

from audit_run import audit_events
from candidate_lineage_v100 import verify_file as verify_candidate_lineage
from evidence_integrity import (strict_jsonl, strict_json_loads, library_entries,
                                reconcile_library, result_gate)
from task_custody import scan_splits, assess_custody
from paired_statistics import exact_mcnemar, paired_bootstrap_success_ci, paired_work_geometric_ratio
from contextlib import contextmanager
import math

VALID_ID = re.compile(r'^[a-zA-Z0-9_-]+$')


def digest(path: Path) -> str:
    h = sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def atomic_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', encoding='utf8', dir=path.parent,
                                     prefix='state-', suffix='.tmp', delete=False) as f:
        tmp = Path(f.name)
        try:
            json.dump(data, f, sort_keys=True, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            tmp.unlink(missing_ok=True)
            raise
    os.replace(tmp, path)


def load_state(run: Path) -> dict[str, Any]:
    return strict_json_loads((run / 'state.json').read_text(encoding='utf8'))


def ids(text: str, label: str, allow_empty: bool = False) -> list[str]:
    result = [s.strip() for s in text.split(',')]
    if (not allow_empty or text) and (not result or any(not VALID_ID.fullmatch(x) for x in result)):
        raise ValueError(f'{label}: invalid task ID')
    if len(result) != len(set(result)):
        raise ValueError(f'{label}: duplicate task ID')
    return [] if allow_empty and not text else result


def checked_regular(path: Path) -> Path:
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'expected non-symlink regular file: {path}')
    return path


def safe_binary(path: str) -> Path:
    binary = checked_regular(Path(path).expanduser().resolve())
    if not os.access(binary, os.X_OK):
        raise ValueError(f'binary not executable: {binary}')
    return binary


def binary_format(path: Path) -> str:
    """Header classification only; not an attestation that Rust compiled it."""
    with path.open('rb') as f:
        magic = f.read(4)
    if magic == b'\x7fELF':
        return 'elf'
    if magic in (b'\xfe\xed\xfa\xce', b'\xce\xfa\xed\xfe',
                 b'\xfe\xed\xfa\xcf', b'\xcf\xfa\xed\xfe',
                 b'\xca\xfe\xba\xbe'):
        return 'mach_o'
    if magic.startswith(b'MZ'):
        return 'pe'
    if magic.startswith(b'#!'):
        return 'script'
    return 'unknown'


def assert_inputs(run: Path, state: dict[str, Any], *, include_test: bool) -> None:
    for rel, expected in state['inputs'].items():
        if not include_test and rel.startswith('sealed_test/'):
            continue
        current = checked_regular(run / rel)
        if digest(current) != expected:
            raise ValueError(f'frozen input changed: {rel}')
    binary = checked_regular(Path(state['binary']))
    if digest(binary) != state['binary_sha256']:
        raise ValueError('supsearch binary no longer matches frozen digest')
    if binary_format(binary) != state['binary_format']:
        raise ValueError('supsearch executable header changed')


@contextmanager
def exclusive_run(run: Path):
    """An O_EXCL phase lock; crash leaves a fail-closed lock for manual review.

    Advisory to this CLI only. Does NOT protect against hostile OS processes.
    """
    lock_path = run / 'OPERATION_IN_PROGRESS.lock'
    try:
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    except FileExistsError as exc:
        raise ValueError('run operation locked; review an interrupted run manually') from exc
    with os.fdopen(fd, 'w', encoding='utf8') as f:
        f.write(f'pid={os.getpid()}\n')
        f.flush()
        os.fsync(f.fileno())
    try:
        yield
    finally:
        lock_path.unlink(missing_ok=True)


def prepare(ns: argparse.Namespace) -> None:
    run = ns.run.absolute()
    if run.exists():
        raise ValueError('run directory exists; create a new run ID instead of overwriting')
    train, dev, test = (ids(getattr(ns, k), k) for k in ('train', 'dev', 'test'))
    if not test:
        raise ValueError('the qualification pipeline requires final evaluation tasks')
    if len(train + dev + test) != len(set(train + dev + test)):
        raise ValueError('split ID overlap')
    binary = safe_binary(ns.binary)
    source = ns.source.resolve()
    source_files: dict[str, Path] = {}
    hashes = {}
    for tid in train + dev + test:
        p = checked_regular(source / f'{tid}.tsk')
        h = digest(p)
        if h in hashes:
            raise ValueError(f'EXACT content duplicate across tasks {hashes[h]} and {tid}')
        hashes[h] = tid
        source_files[tid] = p
    custody = scan_splits(source_files, {tid: split for split, group in [('train', train), ('dev', dev), ('test', test)] for tid in group})
    custody_label = assess_custody(custody, fixture_mode=ns.fixture_mode, require_family_disjoint=ns.disjoint_families)
    candidate = checked_regular(ns.candidates.resolve()) if ns.candidates else None
    initial = checked_regular(ns.initial_library.resolve()) if ns.initial_library else None
    run.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='supsearch-prepare-', dir=run.parent) as d:
        staging = Path(d) / 'new_run'
        for sub in ('learning_tasks', 'sealed_test', 'inputs', 'results', 'logs'):
            (staging / sub).mkdir(parents=True)
        for tid in train + dev:
            shutil.copyfile(source_files[tid], staging / 'learning_tasks' / f'{tid}.tsk')
        for tid in test:
            shutil.copyfile(source_files[tid], staging / 'sealed_test' / f'{tid}.tsk')
        if candidate:
            shutil.copyfile(candidate, staging / 'inputs' / 'candidates.txt')
        if initial:
            shutil.copyfile(initial, staging / 'inputs' / 'initial.tsv')
        else:
            (staging / 'inputs' / 'initial.tsv').write_text('# zero initial concepts\n', encoding='utf8')
        shutil.copyfile(staging / 'inputs' / 'initial.tsv', staging / 'inputs' / 'working.tsv')
        immutable_paths = [p for sub in ('learning_tasks', 'sealed_test')
                           for p in (staging / sub).iterdir()]
        immutable_paths.extend([staging / 'inputs' / 'initial.tsv'])
        if candidate:
            immutable_paths.append(staging / 'inputs' / 'candidates.txt')
        fingerprints = {p.relative_to(staging).as_posix(): digest(p) for p in immutable_paths}
        state: dict[str, Any] = {
            'format': 1, 'phase': 'frozen', 'binary': str(binary),
            'binary_sha256': digest(binary), 'binary_format': binary_format(binary), 'train': train, 'dev': dev, 'test': test,
            'inputs': fingerprints, 'rounds': ns.rounds, 'budget': ns.budget,
            'max_size': ns.max_size, 'fuel': ns.fuel, 'timeout': ns.timeout,
            'has_candidates': bool(candidate), 'label': custody_label,
            'custody_audit': custody, 'protocol_version': 'v0.5', 'minimum_final_tasks': ns.minimum_final_tasks,
        }
        atomic_json(staging / 'state.json', state)
        os.rename(staging, run)
    print(json.dumps({'phase': 'frozen', 'run': str(run), 'train': len(train),
                      'dev': len(dev), 'test': len(test),
                      'custody_label': custody_label,
                      'example_overlap_pairs': len(custody['cross_split_example_overlaps'])}, indent=2))


def execute(binary: str, command: list[str], stdout: Path, timeout: int) -> None:
    """Fail closed; no shell, no arbitrary user-defined command templating."""
    result = subprocess.run([binary, *command], capture_output=True, text=True,
                            timeout=timeout, check=False)
    stdout.parent.mkdir(parents=True, exist_ok=True)
    stdout.write_text('stdout:\n' + result.stdout + '\nstderr:\n' + result.stderr, encoding='utf8')
    if result.returncode:
        raise RuntimeError(f'supsearch exited {result.returncode}; see {stdout}')


def train_run(ns: argparse.Namespace) -> None:
    run = ns.run.absolute()
    state = load_state(run)
    if state['phase'] != 'frozen':
        raise ValueError('train is single-use; start another qualified run')
    assert_inputs(run, state, include_test=False)
    # Consume training permission BEFORE launching the Rust process.
    state['phase'] = 'training_consumed'
    atomic_json(run / 'state.json', state)
    command = ['learn', str(run / 'learning_tasks'), '--train', ','.join(state['train']),
               '--dev', ','.join(state['dev']), '--rounds', str(state['rounds']),
               '--budget', str(state['budget']), '--max-size', str(state['max_size']),
               '--fuel', str(state['fuel']), '--library', str(run / 'inputs' / 'working.tsv'),
               '--ledger', str(run / 'results' / 'decisions.jsonl')]
    # v1 native learner enforces that nothing imported can receive native-only status.
    command += ['--require-native-mined', 'false' if state['has_candidates'] else 'true']
    if state['has_candidates']:
        command += ['--candidates', str(run / 'inputs' / 'candidates.txt')]
    execute(state['binary'], command, run / 'logs' / 'train.txt', state['timeout'])
    ledger = run / 'results' / 'decisions.jsonl'
    review = audit_events(ledger.read_text(encoding='utf8').splitlines())
    lineage = reconcile_library(ledger, run / 'inputs' / 'initial.tsv', run / 'inputs' / 'working.tsv')
    # Enforce native candidate provenance when a v1.0 ledger is observed. This
    # gate is NOT retroactively applied to older v0.9 ledgers without origin.
    first = strict_jsonl(ledger)[0]
    if first.get('schema_version') == 6:
        verify_candidate_lineage(ledger, require_native_mined=not state['has_candidates'],
                                 initial=run / 'inputs' / 'initial.tsv',
                                 learned=run / 'inputs' / 'working.tsv')
    if not lineage['append_only_reconciled'] or not review['consistent'] or review['final_test_seen'] or review['runs'] != 1:
        raise ValueError(f'learning audit failed: {review}')
    state['learning_library_sha256'] = digest(run / 'inputs' / 'working.tsv')
    state['learning_ledger_sha256'] = digest(ledger)
    state['phase'] = 'trained'
    atomic_json(run / 'state.json', state)
    print(json.dumps({'phase': 'trained', 'audit': review, 'lineage': lineage}, indent=2))


def parse_eval(path: Path, tasks: list[str], mode: str, *, expected_concepts: int | None = None,
               expected_settings: dict | None = None) -> dict[str, dict[str, Any]]:
    lines = strict_jsonl(path)
    if not lines or not isinstance(lines[0], dict) or lines[0].get('event') != 'evaluation_meta' or lines[0].get('mode') != mode:
        raise ValueError(f'{path}: invalid evaluation metadata')
    if lines[0].get('task_count') != len(tasks) or len(lines) != len(tasks) + 1:
        raise ValueError(f'{path}: incorrect row count')
    meta=lines[0]
    if type(meta.get('concept_count')) is not int or meta['concept_count'] < 0:
        raise ValueError(f'{path}: missing or invalid concept_count')
    if meta['task_count'] != len(tasks):
        raise ValueError(f'{path}: incorrect task_count')
    if expected_concepts is not None and meta['concept_count'] != expected_concepts:
        raise ValueError(f'{path}: concept_count disagrees with frozen library')
    if expected_settings is not None:
        for field in ('budget', 'max_size', 'fuel'):
            actual = meta.get(field)
            target = expected_settings[field]
            if type(actual) not in (int, float) or not math.isfinite(actual) or actual != target:
                raise ValueError(f'{path}: {field} disagrees with frozen evaluation configuration')
    # v1.3 permits state-capped experiments, but earlier campaign protocols
    # freeze no state cap. A nonzero cap cannot be smuggled into those runs.
    cap = meta.get('max_built', 0)
    required_cap = expected_settings.get('max_built', 0) if expected_settings is not None else None
    if type(cap) is not int or not 0 <= cap <= 100_000_000:
        raise ValueError(f'{path}: invalid max_built')
    if required_cap is not None and cap != required_cap:
        raise ValueError(f'{path}: max_built disagrees with frozen evaluation configuration')
    records = {}
    for x in lines[1:]:
        if not isinstance(x, dict):
            raise ValueError(f'{path}: evaluation row is not an object')
        tid = x.get('task')
        if x.get('event') != 'evaluation' or x.get('mode') != mode or tid not in tasks or tid in records:
            raise ValueError(f'{path}: unexpected or duplicated task record')
        if (type(x.get('solved')) is not bool or
            type(x.get('built')) is not int or x['built'] < 0 or
            type(x.get('kept',0)) is not int or x.get('kept',0) < 0 or
            type(x.get('aborted',0)) is not int or x.get('aborted',0) < 0 or
            type(x.get('elapsed_secs')) not in (int, float) or
            not math.isfinite(x['elapsed_secs']) or x['elapsed_secs'] < 0):
            raise ValueError(f'{path}: invalid metric field')
        if cap and x['built'] > cap:
            raise ValueError(f'{path}: built count exceeds frozen state cap')
        records[tid] = x
    if set(records) != set(tasks):
        raise ValueError(f'{path}: incomplete task coverage')
    return records


def paired_summary(base: dict, upgraded: dict) -> dict:
    common = base.keys() & upgraded.keys()
    bs = sum(base[x]['solved'] for x in common)
    us = sum(upgraded[x]['solved'] for x in common)
    new = sorted(x for x in common if not base[x]['solved'] and upgraded[x]['solved'])
    lost = sorted(x for x in common if base[x]['solved'] and not upgraded[x]['solved'])
    both = [x for x in common if base[x]['solved'] and upgraded[x]['solved']]
    bwork = sum(base[x]['built'] for x in both)
    uwork = sum(upgraded[x]['built'] for x in both)
    return {'tasks': len(common), 'baseline_solved': bs, 'upgraded_solved': us,
            'paired_success_difference': (us-bs)/len(common) if common else None,
            'paired_success_bootstrap_95pct': paired_bootstrap_success_ci(base, upgraded),
            'exact_mcnemar_two_sided_p': exact_mcnemar(len(new), len(lost)),
            'jointly_solved_geometric_work_ratio': paired_work_geometric_ratio(base, upgraded),
            'jointly_solved_count': len(both),
            'newly_solved': new, 'regressions': lost,
            'paired_built_baseline': bwork, 'paired_built_upgraded': uwork,
            'paired_built_improvement_fraction': (bwork-uwork)/bwork if bwork else None,
            'note': 'Only concept-versus-concept is a same-algorithm comparison; task fixtures remain local.'}


def evaluate_run(ns: argparse.Namespace) -> None:
    run = ns.run.absolute()
    state = load_state(run)
    if state['phase'] != 'trained':
        raise ValueError('final evaluation is single-use and requires completed training')
    assert_inputs(run, state, include_test=True)
    if digest(run / 'inputs' / 'working.tsv') != state['learning_library_sha256']:
        raise ValueError('trained concept library changed since training')
    if digest(run / 'results' / 'decisions.jsonl') != state['learning_ledger_sha256']:
        raise ValueError('learning evidence changed since training')
    # O_EXCL is a second barrier against repeated concurrent final evaluations.
    marker = run / 'results' / 'FINAL_EVALUATION_CONSUMED'
    fd = os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    with os.fdopen(fd, 'w') as f:
        f.write('Final evaluation cannot be replayed within this run.\n')
    state['phase'] = 'evaluation_consumed'
    atomic_json(run / 'state.json', state)
    specs = [('concept_baseline', 'concept', 'initial.tsv'),
             ('concept_upgraded', 'concept', 'working.tsv'),
             ('raw_reference', 'raw', 'initial.tsv')]
    results: dict[str, dict] = {}
    for name, mode, library in specs:
        outfile = run / 'results' / f'{name}.jsonl'
        command = ['evaluate', str(run / 'sealed_test'), '--tasks', ','.join(state['test']),
                   '--mode', mode, '--library', str(run / 'inputs' / library),
                   '--out', str(outfile), '--budget', str(state['budget']),
                   '--max-size', str(state['max_size']), '--fuel', str(state['fuel'])]
        execute(state['binary'], command, run / 'logs' / f'{name}.txt', state['timeout'])
        expected_count = len(library_entries(run / 'inputs' / library)) if mode == 'concept' else 0
        results[name] = parse_eval(outfile, state['test'], mode, expected_concepts=expected_count,
                                   expected_settings=state)
    lineage = reconcile_library(run / 'results' / 'decisions.jsonl',
                                run / 'inputs' / 'initial.tsv', run / 'inputs' / 'working.tsv')
    pair = paired_summary(results['concept_baseline'], results['concept_upgraded'])
    gate = result_gate(pair, task_count=len(state['test']), custody_label=state['label'],
                       has_candidates=state['has_candidates'], promotions=lineage['promotions'],
                       min_tasks=state['minimum_final_tasks'])
    if state['binary_format'] not in ('elf', 'mach_o', 'pe'):
        gate['reasons'].append('non_native_executable')
        gate['local_screen_passed'] = False
    report = {'status': 'local_final_test_not_independent',
              'binary_format': state['binary_format'],
              'candidate_origin': 'externally_seeded' if state['has_candidates'] else 'native_mining_only',
              'promotion_lineage': lineage,
              'quality_gate': gate,
              'custody_label': state['label'],
              'custody_audit': state['custody_audit'],
              'concept_pair': pair,
              'raw_reference': {'solved': sum(x['solved'] for x in results['raw_reference'].values()),
                                'task_count': len(state['test'])},
              'results_sha256': {name: digest(run / 'results' / f'{name}.jsonl') for name, _, _ in specs},
              'binary_sha256': state['binary_sha256'],
              'statistical_caution': 'Paired descriptive analysis only; McNemar ignores task-family dependence and selection; bootstrap assumes exchangeable tasks; not independent replication.'}
    atomic_json(run / 'results' / 'report.json', report)
    state['report_sha256'] = digest(run / 'results' / 'report.json')
    state['phase'] = 'evaluated'
    atomic_json(run / 'state.json', state)
    print(json.dumps(report, indent=2))


def verify(ns: argparse.Namespace) -> None:
    run = ns.run.absolute()
    state = load_state(run)
    assert_inputs(run, state, include_test=True)
    if state['phase'] not in ('trained','evaluated'):
        raise ValueError('run is not complete')
    if digest(run / 'inputs' / 'working.tsv') != state['learning_library_sha256']:
        raise ValueError('concept library digest mismatch')
    ledger = run / 'results' / 'decisions.jsonl'
    if digest(ledger) != state['learning_ledger_sha256']:
        raise ValueError('ledger digest mismatch')
    review = audit_events(ledger.read_text(encoding='utf8').splitlines())
    lineage = reconcile_library(ledger, run / 'inputs' / 'initial.tsv', run / 'inputs' / 'working.tsv')
    # Enforce native candidate provenance when a v1.0 ledger is observed. This
    # gate is NOT retroactively applied to older v0.9 ledgers without origin.
    first = strict_jsonl(ledger)[0]
    if first.get('schema_version') == 6:
        verify_candidate_lineage(ledger, require_native_mined=not state['has_candidates'],
                                 initial=run / 'inputs' / 'initial.tsv',
                                 learned=run / 'inputs' / 'working.tsv')
    if not review['consistent'] or review['final_test_seen']:
        raise ValueError('invalid learning audit')
    if state['phase'] == 'evaluated':
        if digest(run / 'results' / 'report.json') != state['report_sha256']:
            raise ValueError('report digest mismatch')
        report = strict_json_loads((run / 'results' / 'report.json').read_text(encoding='utf8'))
        for name, expected in report['results_sha256'].items():
            if digest(run / 'results' / f'{name}.jsonl') != expected:
                raise ValueError(f'evaluation result digest mismatch: {name}')
        if set(report['results_sha256']) != {'concept_baseline', 'concept_upgraded', 'raw_reference'}:
            raise ValueError('evaluation artifacts incomplete')
        original = parse_eval(run / 'results' / 'concept_baseline.jsonl', state['test'], 'concept',
                              expected_concepts=len(library_entries(run / 'inputs' / 'initial.tsv')),
                              expected_settings=state)
        learned = parse_eval(run / 'results' / 'concept_upgraded.jsonl', state['test'], 'concept',
                             expected_concepts=len(library_entries(run / 'inputs' / 'working.tsv')),
                             expected_settings=state)
        raw = parse_eval(run / 'results' / 'raw_reference.jsonl', state['test'], 'raw',
                         expected_concepts=0, expected_settings=state)
        pair = paired_summary(original, learned)
        if report['concept_pair'] != pair:
            raise ValueError('report metrics disagree with evaluation data')
        if report['raw_reference'] != {'solved': sum(x['solved'] for x in raw.values()),
                                     'task_count': len(state['test'])}:
            raise ValueError('raw reference metrics disagree with evaluation data')
        expected_gate = result_gate(pair, task_count=len(state['test']), custody_label=state['label'],
                                    has_candidates=state['has_candidates'], promotions=lineage['promotions'],
                                    min_tasks=state['minimum_final_tasks'])
        if state['binary_format'] not in ('elf','mach_o','pe'):
            expected_gate['reasons'].append('non_native_executable')
            expected_gate['local_screen_passed'] = False
        if report.get('binary_format') != state['binary_format']:
            raise ValueError('binary format claim inconsistent')
        if report.get('quality_gate') != expected_gate or report.get('promotion_lineage') != lineage:
            raise ValueError('result gate or promotion lineage inconsistent')
        if report.get('candidate_origin') != ('externally_seeded' if state['has_candidates'] else 'native_mining_only'):
            raise ValueError('candidate origin inconsistent')
        if report['custody_label'] != state['label'] or report['custody_audit'] != state['custody_audit']:
            raise ValueError('report custody metadata inconsistent')
    print(json.dumps({'verified_local_artifacts': True, 'phase': state['phase'],
                      'audit': review, 'warning': 'Not independently signed or externally attested'},indent=2))


def audit_splits(ns: argparse.Namespace) -> None:
    train, dev, test = (ids(getattr(ns, k), k) for k in ('train', 'dev', 'test'))
    if len(train + dev + test) != len(set(train + dev + test)):
        raise ValueError('split ID overlap')
    files = {tid: checked_regular(ns.source / f'{tid}.tsk') for tid in train + dev + test}
    group = {tid: split for split, ids_ in [('train', train), ('dev', dev), ('test', test)] for tid in ids_}
    scan = scan_splits(files, group)
    label = assess_custody(scan, fixture_mode=ns.fixture_mode, require_family_disjoint=ns.disjoint_families)
    print(json.dumps({'label': label, **scan}, indent=2))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='command', required=True)
    freeze = sub.add_parser('prepare')
    freeze.add_argument('--source', type=Path, required=True)
    freeze.add_argument('--train', required=True)
    freeze.add_argument('--dev', required=True)
    freeze.add_argument('--test', required=True)
    freeze.add_argument('--run', type=Path, required=True)
    freeze.add_argument('--binary', required=True)
    freeze.add_argument('--candidates', type=Path)
    freeze.add_argument('--initial-library', type=Path)
    freeze.add_argument('--rounds', type=int, default=2)
    freeze.add_argument('--minimum-final-tasks', type=int, default=20,
                        help='advisory local evidence screen; not independent qualification')
    freeze.add_argument('--budget', type=float, default=0.5)
    freeze.add_argument('--max-size', type=int, default=13)
    freeze.add_argument('--fuel', type=int, default=20000)
    freeze.add_argument('--timeout', type=int, default=1800)
    freeze.add_argument('--fixture-mode', action='store_true', help='explicitly allow leaking synthetic demonstrations; NOT holdout evidence')
    freeze.add_argument('--disjoint-families', action='store_true', help='reject family-prefix overlap across train/dev/test')
    audit = sub.add_parser('audit-splits', help='screen dataset leakage without Rust binary')
    audit.add_argument('--source', type=Path, required=True)
    audit.add_argument('--train', required=True)
    audit.add_argument('--dev', required=True)
    audit.add_argument('--test', required=True)
    audit.add_argument('--fixture-mode', action='store_true')
    audit.add_argument('--disjoint-families', action='store_true')
    for command in ('train','evaluate','verify'):
        sub.add_parser(command).add_argument('--run', type=Path, required=True)
    a=p.parse_args(argv)
    if a.command=='prepare':
        if not (1 <= a.minimum_final_tasks <= 100000 and 1 <= a.rounds <= 100 and 0 < a.budget <= 3600 and 2 <= a.max_size <= 64 and
                0 < a.fuel <= 10_000_000 and 1 <= a.timeout <= 86400):
            p.error('invalid experiment limits')
    try:
        if a.command == 'prepare':
            prepare(a)
        elif a.command == 'audit-splits':
            audit_splits(a)
        else:
            with exclusive_run(a.run.absolute()):
                {'train': train_run, 'evaluate': evaluate_run, 'verify': verify}[a.command](a)
        return 0
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        print(f'qualification error: {e}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
