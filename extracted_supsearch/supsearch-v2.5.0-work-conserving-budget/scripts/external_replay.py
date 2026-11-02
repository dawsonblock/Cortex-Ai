#!/usr/bin/env python3
"""Evaluator-side single-use replay of frozen concept libraries.

Evaluator-owned task files, registry, binary, and source trust are ASSUMPTIONS.
This tool does not sandbox a malicious Rust binary, independently verify code
provenance, or establish true third-party custody on one host.

Must run under a separate evaluator account/VM with an evaluator-owned registry
and private final-test task directory for an independently administered replay.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
from typing import Any

from audit_run import audit_events
from evidence_integrity import library_entries, reconcile_library
from qualified_pipeline import (atomic_json, binary_format, checked_regular, digest,
                                execute, ids, load_state, paired_summary, parse_eval,
                                safe_binary)
from task_custody import scan_splits, assess_custody


MODEL = 'external-replay-v1'


def _inside(child: Path, parent: Path) -> bool:
    return child == parent or parent in child.parents


def _claim(registry: Path, experiment_key: str) -> Path:
    registry.mkdir(parents=True, exist_ok=True)
    claim = registry / f'{experiment_key}.consumed'
    fd = os.open(claim, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w', encoding='utf8') as f:
        f.write('consumed before any evaluator native subprocess; manual intervention required after failures\n')
        f.flush()
        os.fsync(f.fileno())
    return claim


def _fresh_source(run: Path, state: dict, binary: Path) -> dict:
    if state.get('phase') not in ('trained', 'evaluated'):
        raise ValueError('external evaluator requires frozen completed training')
    if digest(binary) != state.get('binary_sha256') or binary_format(binary) != state.get('binary_format'):
        raise ValueError('binary differs from trained experiment')
    library = checked_regular(run / 'inputs' / 'working.tsv')
    initial = checked_regular(run / 'inputs' / 'initial.tsv')
    ledger = checked_regular(run / 'results' / 'decisions.jsonl')
    if digest(library) != state.get('learning_library_sha256'):
        raise ValueError('trained library changed')
    if digest(ledger) != state.get('learning_ledger_sha256'):
        raise ValueError('trained learning ledger changed')
    for rel, expect in state.get('inputs', {}).items():
        if rel.startswith('sealed_test/'):
            continue  # External replay never opens the local prior final tests.
        p = checked_regular(run / rel)
        if digest(p) != expect:
            raise ValueError(f'original frozen input changed: {rel}')
    report = audit_events(ledger.read_text(encoding='utf8').splitlines())
    lineage = reconcile_library(ledger, initial, library)
    if not report['consistent'] or report['final_test_seen'] or report['runs'] != 1:
        raise ValueError('learning ledger audit did not pass')
    if lineage['final_concepts'] != len(library_entries(library)):
        raise ValueError('concept library count mismatch')
    return lineage


def _validate_tree(source: Path, registry: Path, out: Path, run: Path) -> None:
    if any(_inside(registry, p) for p in (run, source)):
        raise ValueError('evaluator registry must be outside the training and private-task trees')
    if any(_inside(out, p) for p in (run, source, registry)):
        raise ValueError('output must be outside training, source, and registry directories')
    if _inside(source, run) or _inside(run, source):
        raise ValueError('external source and training run must be separate directories')
    if registry.is_symlink() or out.is_symlink() or source.is_symlink():
        raise ValueError('symlink evaluator roots are unsupported')


def _run_eval(binary: Path, source: Path, task_names: list[str], lib: Path,
              out: Path, mode: str, budget: float, max_size: int, fuel: int, timeout: int,
              log: Path) -> dict[str, dict]:
    args = ['evaluate', str(source), '--tasks', ','.join(task_names),
            '--mode', mode, '--library', str(lib), '--out', str(out),
            '--budget', str(budget), '--max-size', str(max_size), '--fuel', str(fuel)]
    execute(str(binary), args, log, timeout)
    return parse_eval(out, task_names, mode, expected_concepts=(len(library_entries(lib)) if mode == 'concept' else 0),
                      expected_settings={'budget': budget, 'max_size': max_size, 'fuel': fuel})


def run(ns: argparse.Namespace) -> dict[str, Any]:
    run = ns.run.resolve()
    source = ns.source.resolve()
    registry = ns.registry.absolute()
    out = ns.out.absolute()
    if not run.is_dir() or not source.is_dir() or not registry.parent.is_dir() or not out.parent.is_dir():
        raise ValueError('run, source, and evaluator output/registry parents must exist')
    _validate_tree(source, registry, out, run)
    if out.exists():
        raise ValueError('evaluator output already exists: run is single-use')
    tasks = ids(ns.tasks, 'external evaluation tasks')
    if not (1 <= len(tasks) <= 200):
        raise ValueError('task count outside 1..200')
    if not (0 < ns.budget <= 3600 and 2 <= ns.max_size <= 64 and 0 < ns.fuel <= 10_000_000
            and 1 <= ns.timeout <= 86400):
        raise ValueError('invalid evaluator resource limits')
    state = load_state(run)
    binary = safe_binary(state['binary'])
    lineage = _fresh_source(run, state, binary)
    all_files: dict[str, Path] = {}
    assignments: dict[str, str] = {}
    for tid in state['train'] + state['dev']:
        all_files[tid] = checked_regular(run / 'learning_tasks' / f'{tid}.tsk')
        assignments[tid] = 'train' if tid in state['train'] else 'dev'
    for tid in tasks:
        if tid in all_files:
            raise ValueError('external IDs overlap training/development IDs')
        all_files[tid] = checked_regular(source / f'{tid}.tsk')
        assignments[tid] = 'test'
    audit = scan_splits(all_files, assignments)
    label = assess_custody(audit, fixture_mode=ns.fixture_mode,
                           require_family_disjoint=not ns.allow_related_families)
    if ns.fixture_mode:
        label = 'synthetic_fixture_not_holdout'
    if not ns.fixture_mode and state.get('has_candidates'):
        label = 'externally_seeded_candidates_not_autonomous'
    payload = {
        'schema': MODEL,
        'trained_library_sha256': digest(run / 'inputs' / 'working.tsv'),
        'initial_library_sha256': digest(run / 'inputs' / 'initial.tsv'),
        'learning_ledger_sha256': digest(run / 'results' / 'decisions.jsonl'),
        'binary_sha256': digest(binary),
        'task_sha256': {tid: digest(source / f'{tid}.tsk') for tid in tasks},
        'task_examples_sha256': {tid:audit['task_examples_sha256'][tid] for tid in tasks},
        'budget': ns.budget, 'max_size': ns.max_size, 'fuel': ns.fuel,
        'mode': 'per_task_counterbalanced' if ns.counterbalanced else 'batch_baseline_first',
    }
    key = sha256(json.dumps(payload, sort_keys=True, separators=(',', ':')).encode()).hexdigest()
    # Consume BEFORE opening / executing final tasks. An evaluator must retain the
    # registry in an independent, access-controlled storage domain for this to
    # be a meaningful single-use control.
    claim = _claim(registry, key)
    start = time.perf_counter()
    with tempfile.TemporaryDirectory(prefix='supsearch-external-replay-',dir=out.parent) as tmp:
        stage = Path(tmp)
        for name in ('inputs', 'private_tasks', 'results', 'logs'):
            (stage / name).mkdir()
        shutil.copyfile(binary, stage / 'inputs' / 'native_binary')
        (stage / 'inputs' / 'native_binary').chmod(0o700)
        for name in ('initial.tsv', 'working.tsv'):
            shutil.copyfile(run / 'inputs' / name, stage / 'inputs' / name)
        for tid in tasks:
            shutil.copyfile(source / f'{tid}.tsk', stage / 'private_tasks' / f'{tid}.tsk')
        for tid in tasks:
            if digest(stage / 'private_tasks' / f'{tid}.tsk') != payload['task_sha256'][tid]:
                raise ValueError('private task changed during staging')
        snapshot = {'trial_key': key, 'protocol': MODEL, 'source_payload': payload,
                    'overlap_audit': audit, 'label': label, 'lineage': lineage,
                    'limitations': ['External custody depends on separate evaluator governance',
                                    'All equivalence checks are finite-example checks',
                                    'No native binary attestation, sandbox, or software signature']}
        atomic_json(stage / 'snapshot.json', snapshot)
        records: dict[str, dict] = {'concept_baseline':{}, 'concept_upgraded':{}, 'raw_reference':{}}
        checks = [('concept_baseline', 'concept', 'initial.tsv'),
                  ('concept_upgraded', 'concept', 'working.tsv'),
                  ('raw_reference', 'raw', 'initial.tsv')]
        if ns.counterbalanced:
            for i, tid in enumerate(tasks):
                # Alternate condition order by task index, with one fresh native
                # invocation per condition. Run raw reference third.
                seq = checks[:2] if i % 2 == 0 else list(reversed(checks[:2]))
                for name, mode, library in seq + [checks[2]]:
                    dest = stage / 'results' / f'{name}__{tid}.jsonl'
                    got = _run_eval(stage / 'inputs' / 'native_binary', stage / 'private_tasks', [tid],
                                    stage / 'inputs' / library, dest, mode, ns.budget, ns.max_size,
                                    ns.fuel, ns.timeout, stage / 'logs' / f'{name}__{tid}.log')
                    records[name].update(got)
        else:
            for name, mode, library in checks:
                dest = stage / 'results' / f'{name}.jsonl'
                records[name] = _run_eval(stage / 'inputs' / 'native_binary', stage / 'private_tasks', tasks,
                                          stage / 'inputs' / library, dest, mode, ns.budget, ns.max_size,
                                          ns.fuel, ns.timeout, stage / 'logs' / f'{name}.log')
        pair = paired_summary(records['concept_baseline'], records['concept_upgraded'])
        elapsed = time.perf_counter() - start
        report = {
            'schema': MODEL, 'trial_key': key,
            'status': 'evaluator_side_replay_not_automatically_independent',
            'custody_label': label, 'counterbalanced': ns.counterbalanced,
            'candidate_origin': 'externally_seeded' if state.get('has_candidates') else 'native_mining_only',
            'tasks': len(tasks), 'concept_pair': pair,
            'raw_reference_solved': sum(x['solved'] for x in records['raw_reference'].values()),
            'promotions': lineage['promotions'],
            'evaluator_elapsed_seconds': elapsed,
            'result_hashes': {p.relative_to(stage).as_posix(): digest(p) for p in sorted((stage / 'results').glob('*.jsonl'))},
            'claimed_independent_validation': False,
            'caution': 'Separate custodial administration must be independently documented; no evidence of general-purpose intelligence.',
        }
        atomic_json(stage / 'report.json', report)
        # The receipt is reproducible given the report and input digests.
        receipt = {'schema': MODEL, 'trial_key': key,
                   'snapshot_sha256': digest(stage / 'snapshot.json'),
                   'report_sha256': digest(stage / 'report.json'),
                   'source_payload_sha256': sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest()}
        atomic_json(stage / 'receipt.json', receipt)
        # Output must not exist. Rename is atomic within out.parent filesystem.
        os.rename(stage, out)
    # Preserve claim as durable evidence of consumed evaluation, never clear.
    if not claim.exists():
        raise ValueError('evaluator registry claim disappeared')
    return report


def verify_result(out: Path) -> dict[str, Any]:
    from evidence_integrity import strict_json_loads
    receipt = strict_json_loads(checked_regular(out / 'receipt.json').read_text(encoding='utf8'))
    snapshot = strict_json_loads(checked_regular(out / 'snapshot.json').read_text(encoding='utf8'))
    report = strict_json_loads(checked_regular(out / 'report.json').read_text(encoding='utf8'))
    if receipt.get('schema') != MODEL or report.get('schema') != MODEL or snapshot.get('protocol') != MODEL:
        raise ValueError('evaluator protocol version mismatch')
    if receipt['trial_key'] != report.get('trial_key') or receipt['trial_key'] != snapshot.get('trial_key'):
        raise ValueError('evaluator trial key mismatch')
    if receipt['snapshot_sha256'] != digest(out / 'snapshot.json') or receipt['report_sha256'] != digest(out / 'report.json'):
        raise ValueError('evaluator receipt/checksum mismatch')
    payload = snapshot['source_payload']
    if sha256(json.dumps(payload,sort_keys=True,separators=(',',':')).encode()).hexdigest() != receipt['source_payload_sha256']:
        raise ValueError('source payload mismatch')
    for tid, hexdigest in payload['task_sha256'].items():
        if digest(checked_regular(out / 'private_tasks' / f'{tid}.tsk')) != hexdigest:
            raise ValueError('replay test task modified')
    if digest(checked_regular(out / 'inputs' / 'initial.tsv')) != payload['initial_library_sha256'] or \
       digest(checked_regular(out / 'inputs' / 'working.tsv')) != payload['trained_library_sha256'] or \
       digest(checked_regular(out / 'inputs' / 'native_binary')) != payload['binary_sha256']:
        raise ValueError('replay binary or concept libraries changed')
    actual={p.relative_to(out).as_posix():digest(checked_regular(p)) for p in sorted((out / 'results').glob('*.jsonl'))}
    if actual != report['result_hashes']:
        raise ValueError('replay evaluation evidence modified')
    tasks=list(payload['task_sha256'])
    records = {'concept_baseline':{}, 'concept_upgraded':{}, 'raw_reference':{}}
    specs={'concept_baseline':('concept','initial.tsv'),
           'concept_upgraded':('concept','working.tsv'),
           'raw_reference':('raw','initial.tsv')}
    for name,(mode,library) in specs.items():
        count=len(library_entries(out / 'inputs' / library)) if mode=='concept' else 0
        if payload['mode']=='per_task_counterbalanced':
            for tid in tasks:
                p=checked_regular(out / 'results' / f'{name}__{tid}.jsonl')
                records[name].update(parse_eval(p, [tid], mode, expected_concepts=count, expected_settings=payload))
        else:
            p=checked_regular(out / 'results' / f'{name}.jsonl')
            records[name] = parse_eval(p,tasks,mode,expected_concepts=count,expected_settings=payload)
    if paired_summary(records['concept_baseline'],records['concept_upgraded']) != report['concept_pair'] or \
       sum(x['solved'] for x in records['raw_reference'].values()) != report['raw_reference_solved']:
        raise ValueError('replay metrics inconsistent with evaluation rows')
    if len(tasks) != report['tasks'] or report.get('claimed_independent_validation') is not False:
        raise ValueError('replay claim or task count inconsistent')
    return {'verified_local_replay_artifacts': True, 'trial_key': receipt['trial_key'],
            'claimed_independent_validation': False, 'tasks': len(tasks)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    r = sub.add_parser('evaluate', help='consume evaluator-owned test set exactly once per registry/key')
    for name in ('run','source','registry','out'):
        r.add_argument('--'+name, type=Path, required=True)
    r.add_argument('--tasks',required=True)
    r.add_argument('--budget',type=float,default=0.5)
    r.add_argument('--max-size',type=int,default=13)
    r.add_argument('--fuel',type=int,default=20000)
    r.add_argument('--timeout',type=int,default=1800)
    r.add_argument('--counterbalanced',action='store_true')
    r.add_argument('--fixture-mode',action='store_true')
    r.add_argument('--allow-related-families',action='store_true')
    v = sub.add_parser('verify', help='recompute report figures from sealed evaluation artifacts')
    v.add_argument('--out',type=Path,required=True)
    ns=parser.parse_args(argv)
    try:
        if ns.command=='evaluate':
            print(json.dumps(run(ns),sort_keys=True,indent=2))
        else:
            print(json.dumps(verify_result(ns.out),sort_keys=True,indent=2))
        return 0
    except (OSError, ValueError, RuntimeError, KeyError, TypeError, TimeoutError) as e:
        print(f'external replay rejected: {e}',file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
