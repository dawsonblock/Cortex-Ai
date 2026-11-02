#!/usr/bin/env python3
"""Fail-closed native Rust qualification smoke gate (not a learning benchmark).

Builds from the checked-out source and executes actual native Rust commands.
This is not an independent evaluator: it confirms build/runtime operation only.
"""
from __future__ import annotations
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone

from qualified_pipeline import binary_format, digest, parse_eval
from evidence_integrity import strict_jsonl
from journal_preflight_v110 import audit as audit_learning_journal
from concept_admission_audit_v220 import audit as audit_concept_admission
from search_budget_audit_v230 import audit as audit_search_budget
from native_reserved_fallback_v240 import run_native_probe


def _exec(argv: list[str], cwd: Path, log: Path, seconds: int, *, env: dict[str, str] | None = None) -> None:
    try:
        result = subprocess.run(argv, cwd=cwd, timeout=seconds, capture_output=True, text=True, check=False, env=env)
    except subprocess.TimeoutExpired as e:
        log.write_text('TIMED OUT\n', encoding='utf8')
        raise RuntimeError(f'command timed out: {argv[0]}') from e
    log.write_text('COMMAND: '+repr(argv)+'\nEXIT: '+str(result.returncode)+'\nSTDOUT:\n'+result.stdout+'\nSTDERR:\n'+result.stderr, encoding='utf8')
    if result.returncode:
        raise RuntimeError(f'command exited {result.returncode}: {argv[0]}; inspect {log}')


def check_prerequisites(source: Path, cargo: str = 'cargo') -> dict:
    exe = shutil.which(cargo)
    if not exe:
        raise RuntimeError('Rust Cargo is unavailable. Native compilation is NOT verified; install Rust and rerun this gate.')
    if not (source / 'Cargo.toml').is_file() or not (source / 'Cargo.lock').is_file():
        raise RuntimeError('Cargo.toml and Cargo.lock required for reproducible qualification')
    return {'cargo': exe, 'project': str(source.resolve())}


def qualify(source: Path, output: Path, cargo: str, timeout: int) -> dict:
    pre = check_prerequisites(source, cargo)
    if output.exists():
        raise ValueError('qualification output exists; use a new path')
    if source.resolve().is_relative_to(output.resolve()) or output.resolve().is_relative_to(source.resolve()):
        raise ValueError('qualification output and source tree must be separate')
    if timeout < 1 or timeout > 86400:
        raise ValueError('invalid timeout')
    if not output.parent.is_dir():
        raise ValueError('output parent directory does not exist')
    output.mkdir(mode=0o700)
    logdir = output / 'logs'; logdir.mkdir()
    try:
        # Clean, isolated Cargo target: never mistake a previous checkout's
        # binary for a successful build from this source. This project has no
        # external Cargo dependencies, so fail closed when offline.
        build_env = os.environ.copy()
        build_env['CARGO_TARGET_DIR'] = str((output/'target').resolve())
        build_env['CARGO_INCREMENTAL'] = '0'
        _exec([pre['cargo'], 'test', '--locked', '--offline'], source, logdir/'cargo-test.log', timeout, env=build_env)
        _exec([pre['cargo'], 'build', '--release', '--locked', '--offline'], source, logdir/'cargo-build.log', timeout, env=build_env)
        exe = output / 'target' / 'release' / ('supsearch.exe' if os.name=='nt' else 'supsearch')
        if not exe.is_file() or binary_format(exe) not in ('elf', 'mach_o', 'pe'):
            raise RuntimeError('no native executable of a supported binary format was produced')
        # Empty concept library is an honest same-algorithm control; raw is a separate reference.
        empty = output / 'initial.tsv'; empty.write_text('# no concepts\n', encoding='utf8')
        records = {}
        for name, mode in [('concept_empty','concept'), ('raw_reference','raw')]:
            res = output / f'{name}.jsonl'
            _exec([str(exe.resolve()), 'evaluate', str((source / 'bench').resolve()),
                   '--tasks','cnat_add', '--mode',mode, '--library',str(empty),
                   '--out',str(res), '--budget','0.05','--max-size','4','--fuel','1000'],
                  source,logdir/f'{name}.log', timeout)
            records[name] = parse_eval(res, ['cnat_add'], mode, expected_concepts=0,
                                       expected_settings={'budget':0.05,'max_size':4,'fuel':1000})
        # Native capped work checks. Both evaluator modes must respect the
        # exact state-count ceiling even if the wall-clock timeout is generous.
        for name, mode in [('capped_raw', 'raw'), ('capped_concept', 'concept')]:
            res = output / f'{name}.jsonl'
            _exec([str(exe.resolve()), 'evaluate', str((source / 'bench').resolve()),
                   '--tasks', 'cnat_add', '--mode', mode, '--library', str(empty),
                   '--out', str(res), '--budget', '1', '--max-size', '5',
                   '--fuel', '1000', '--max-built', '1'],
                  source, logdir / f'{name}.log', timeout)
            rows = parse_eval(res, ['cnat_add'], mode, expected_concepts=0,
                              expected_settings={'budget': 1, 'max_size': 5,
                                                 'fuel': 1000, 'max_built': 1})
            if rows['cnat_add']['built'] > 1:
                raise RuntimeError(f'{name}: native solver exceeded max-built=1')
        # Run the actual learning command; outcomes may include zero promotions.
        tmp_tasks = output / 'training_tasks'; tmp_tasks.mkdir()
        for original, alias in [('cnat_add','learn_train'),('cnat_mul','learn_dev')]:
            shutil.copyfile(source/'bench'/f'{original}.tsk', tmp_tasks/f'{alias}.tsk')
        library = output / 'concepts.tsv'; ledger = output / 'decisions.jsonl'
        _exec([str(exe.resolve()), 'learn', str(tmp_tasks), '--train','learn_train',
               '--dev','learn_dev','--library',str(library),'--ledger',str(ledger),
               '--rounds','1','--budget','0.05','--max-size','4','--fuel','1000',
               '--top-tasks','1','--max-candidates','1','--max-arity','1',
               '--max-built','1000','--raw-reserve-pct','25'],
              source,logdir/'learn-smoke.log',timeout)
        events = strict_jsonl(ledger)
        if (not events or events[0].get('event') != 'start'
            or events[0].get('schema_version') != 8
            or events[0].get('max_built') != 1000
            or events[-1].get('event') != 'session_completed'
            or not any(x.get('event') in ('no_promotion','promotion_committed') for x in events)):
            raise RuntimeError('learning command failed to produce a terminal schema-v8 round ledger')
        budget_receipt = audit_search_budget(ledger)
        if not budget_receipt['self_reported_allocation_consistent']:
            raise RuntimeError('v2.3 budget allocation not reconciled')
        audit_receipt = audit_learning_journal(ledger, library)
        concept_receipt = audit_concept_admission(ledger)
        if not concept_receipt['local_receipts_reconciled']:
            raise RuntimeError('v2.2 concept admission receipt reconciliation failed')
        if audit_receipt['concept_count'] != events[-1]['concept_count']:
            raise RuntimeError('concept library count differs from native learning terminal event')
        # v2.4 adds a distinct, REAL native test with an already-populated
        # concept library. The old empty-library smoke cannot exercise reserve.
        fallback_report = run_native_probe(exe, source, output/'nonempty-fallback', timeout=timeout)
        if not (fallback_report['concept_search_executed'] and fallback_report['raw_fallback_executed']):
            raise RuntimeError('v2.4 nonempty-library native fallback qualification incomplete')
        result = {'schema': 'supsearch-native-gate-v1' , 'state': 'native_compiled_smoke_passed',
                  'qualification_scope': 'native build, tests, evaluator and learning smoke only',
                  'timestamp_utc': datetime.now(timezone.utc).isoformat(),
                  'binary_sha256': digest(exe), 'binary_format': binary_format(exe),
                  'cargo_path': pre['cargo'], 'learning_events': len(events),
                  'learn_promotions_in_smoke': audit_receipt['commits'],
                  'journal_complete_and_library_reconciled': True,
                  'state_cap_native_raw_and_concept_checked': True,
                  'v220_concept_admission_receipts_reconciled': True,
                  'v230_search_budget_receipts_reconciled': True,
                  'v240_nonempty_library_fallback_native_qualified': True,
                  'v240_nonempty_library_fallback_receipt': fallback_report,
                  'independent_holdout_run': False, 'improved_transfer_demonstrated': False}
        (output/'qualification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
        return result
    except BaseException as exc:
        (output/'FAILURE.txt').write_text(f'{type(exc).__name__}: {exc}\nNative qualification not passed.\n')
        raise


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    p.add_argument('--out', type=Path)
    p.add_argument('--cargo', default='cargo')
    p.add_argument('--timeout', type=int, default=600)
    p.add_argument('--preflight', action='store_true')
    ns=p.parse_args(argv)
    try:
        if ns.preflight:
            result=check_prerequisites(ns.source,ns.cargo)
        else:
            if ns.out is None: raise ValueError('--out is required for full qualification')
            result=qualify(ns.source,ns.out,ns.cargo,ns.timeout)
        print(json.dumps(result,indent=2,sort_keys=True))
        return 0
    except (OSError, ValueError, RuntimeError) as exc:
        print(f'native qualification failed: {exc}', file=sys.stderr)
        return 2

if __name__=='__main__':
    raise SystemExit(main())
