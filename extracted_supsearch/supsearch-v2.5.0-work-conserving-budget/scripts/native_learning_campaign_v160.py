#!/usr/bin/env python3
"""Run a *local* end-to-end Supsearch native-mining campaign and paired final replay.

Requires two physically separate task directories. Final tasks are never passed to
`supsearch learn`. The learner may still have ambient filesystem access; therefore
this is NOT adversarial evaluator isolation or an independent holdout. The native
binary and its source provenance need external qualification.

Fail closed on input changes, overlap, missing/foreign promotions, timeouts and
malformed evidence. A Python test-double is allowed only with explicit opt-in and
can NEVER qualify as native.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys

from journal_preflight_v110 import audit as audit_journal
from native_paired_v150 import run as paired_run, is_native_executable
from task_custody import scan_splits

MAX_TASK = 2 * 1024 * 1024
MAX_LIBRARY = 2 * 1024 * 1024


def sha(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(65536), b''):
            h.update(block)
    return h.hexdigest()


def safe_file(p: Path, limit: int) -> None:
    if p.is_symlink() or not p.is_file() or not 0 <= p.stat().st_size <= limit:
        raise ValueError('missing, symlinked or oversized input: ' + str(p))


def ids(value: str, label: str) -> list[str]:
    values = value.split(',')
    if not values or len(values) > 200 or len(values) != len(set(values)):
        raise ValueError('missing/duplicate/oversized '+label+' task list')
    if any(not v or not all(c.isascii() and (c.isalnum() or c in '_-') for c in v) for v in values):
        raise ValueError('unsafe '+label+' task ID')
    return values


def unique_pairs(pairs):
    result = {}
    for k, v in pairs:
        if k in result:
            raise ValueError('duplicate JSON key: '+k)
        result[k] = v
    return result


def journal_lineage(path: Path) -> dict:
    events = [json.loads(row, object_pairs_hook=unique_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError('invalid JSON constant')))
              for row in path.read_text(encoding='utf8').splitlines()]
    starts = [e for e in events if e.get('event') == 'start']
    intents = [e for e in events if e.get('event') == 'promotion_intent']
    commits = [e for e in events if e.get('event') == 'promotion_committed']
    if len(starts) != 1 or len(intents) != len(commits):
        raise ValueError('unexpected sessions or incomplete promotions')
    if any(e.get('origin') != 'native_mining' for e in intents):
        raise ValueError('non-native candidate entered promoted concept lineage')
    trials = [e for e in events if e.get('event') == 'candidate_trial']
    train_attempts = [e for e in events if e.get('event') == 'train_attempt']
    if not train_attempts:
        raise ValueError('no native training attempts recorded')
    lower = 0
    for e in train_attempts:
        value = e.get('built')
        if type(value) is not int or value < 0:
            raise ValueError('invalid training expansion count')
        lower += value
    return {'native_mined_promotion_count_reported':len(commits),
            'training_attempts':len(train_attempts),
            'training_built_lower_bound':lower,
            'candidate_trial_records':len(trials),
            'total_learning_work_known':False,
            'note':'trial and development cost is not fully logged by the Rust learner'}


def prepare(ns):
    train = ids(ns.train, 'training')
    dev = ids(ns.dev, 'development')
    final = ids(ns.final, 'final')
    if len(set(train+dev+final)) != len(train+dev+final):
        raise ValueError('task IDs overlap across splits')
    if not (0 < ns.budget <= 3600 and 2 <= ns.max_size <= 64 and
            0 < ns.fuel <= 10_000_000 and 1 <= ns.max_built <= 100_000_000 and
            1 <= ns.rounds <= 100 and 0 < ns.timeout <= 3600 and
            0 <= ns.min_gain <= 1 and 0 <= ns.max_regression <= 10 and
            all(math.isfinite(v) for v in (ns.budget,ns.timeout,ns.min_gain,ns.max_regression))):
        raise ValueError('invalid campaign budget or limits')
    safe_file(ns.binary, 256 * 1024 * 1024)
    native = is_native_executable(ns.binary)
    safe_file(ns.baseline_library, MAX_LIBRARY)
    if not native and not ns.allow_script_test_double:
        raise ValueError('not a native executable; script double forbidden unless explicitly opted in')
    for source in (ns.learn_tasks, ns.final_tasks):
        if source.is_symlink() or not source.is_dir():
            raise ValueError('task directories must be existing real directories')
    tdir, fdir, output = ns.learn_tasks.resolve(), ns.final_tasks.resolve(), ns.out_dir.resolve()
    if tdir == fdir or tdir.is_relative_to(fdir) or fdir.is_relative_to(tdir):
        raise ValueError('final task directory must be physically separate from learning tasks')
    for source in (tdir, fdir, ns.binary.resolve(), ns.baseline_library.resolve()):
        if output == source or output.is_relative_to(source) or source.is_relative_to(output):
            raise ValueError('campaign output must not overlap any protected input')
    if ns.out_dir.exists():
        raise ValueError('fresh output path required; existing evidence is immutable')
    filemap = {}
    assignment = {}
    for label, names, base in (('train',train,tdir),('dev',dev,tdir),('final',final,fdir)):
        for name in names:
            path = base / (name+'.tsk')
            safe_file(path, MAX_TASK)
            filemap[name], assignment[name] = path, label
    scan = scan_splits(filemap, assignment)
    if scan['cross_split_example_overlaps']:
        raise ValueError('cross-split example leakage detected; campaign rejected')
    # Family-wise transfer should not quietly reuse a previously named family.
    # This checks declared ID prefixes, NOT semantic equivalence.
    prefixes = {name:name.split('_', 1)[0] for name in filemap}
    prior_families = {prefixes[name] for name in train + dev}
    if any(prefixes[name] in prior_families for name in final):
        raise ValueError('final task-family ID prefix also appears in training or development')
    prior = {'binary':sha(ns.binary), 'baseline_library':sha(ns.baseline_library),
             'tasks':{name:sha(path) for name,path in sorted(filemap.items())}}
    return train, dev, final, native, filemap, scan, prior


def execute(ns):
    train, dev, final, native, filemap, scan, prior = prepare(ns)
    output = ns.out_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    learning_dir = output / 'learn'; learning_dir.mkdir()
    learned = learning_dir / 'concepts.tsv'
    shutil.copyfile(ns.baseline_library, learned)
    ledger = learning_dir / 'journal.jsonl'
    command = [str(ns.binary.resolve()), 'learn', str(ns.learn_tasks.resolve()),
               '--train', ','.join(train), '--dev', ','.join(dev),
               '--library', str(learned), '--ledger', str(ledger),
               '--rounds', str(ns.rounds), '--budget', str(ns.budget),
               '--max-size', str(ns.max_size), '--fuel', str(ns.fuel),
               '--max-built', str(ns.max_built), '--require-native-mined', 'true']
    try:
        proc = subprocess.run(command, capture_output=True, text=True,
                              timeout=ns.timeout, check=False)
    except subprocess.TimeoutExpired as e:
        raise ValueError('native learning timed out; quarantine incomplete output') from e
    (learning_dir/'stdout.txt').write_text(proc.stdout[:1024*1024],encoding='utf8')
    (learning_dir/'stderr.txt').write_text(proc.stderr[:1024*1024],encoding='utf8')
    if proc.returncode:
        raise ValueError(f'native learning failed (exit {proc.returncode}); outputs quarantined')
    safe_file(learned, MAX_LIBRARY)
    preflight = audit_journal(ledger, learned)
    lineage = journal_lineage(ledger)
    if lineage['native_mined_promotion_count_reported'] != preflight['commits']:
        raise ValueError('promotion records differ from journal auditor')
    # Freeze and re-check the exact prelearning inputs before exposing final tasks.
    current = {'binary':sha(ns.binary),'baseline_library':sha(ns.baseline_library),
               'tasks':{name:sha(path) for name,path in sorted(filemap.items())}}
    if current != prior:
        raise ValueError('inputs modified during learning')
    paired_args = argparse.Namespace(binary=ns.binary, tasks_dir=ns.final_tasks,
       tasks=','.join(final), baseline_library=ns.baseline_library,
       learned_library=learned, out_dir=output/'paired', budget=ns.budget,
       max_size=ns.max_size, fuel=ns.fuel, max_built=ns.max_built,
       min_gain=ns.min_gain, max_regression=ns.max_regression,
       timeout=ns.timeout, allow_script_test_double=ns.allow_script_test_double)
    paired = paired_run(paired_args)
    # Do not accept a final evaluator that reports concept-library sizes
    # inconsistent with the independently parsed promotion journal.
    expected_base = preflight['concept_count'] - preflight['commits']
    if (paired['baseline']['concept_count'] != expected_base or
            paired['learned']['concept_count'] != preflight['concept_count']):
        raise ValueError('paired evaluator concept counts conflict with journal lineage')
    current = {'binary':sha(ns.binary),'baseline_library':sha(ns.baseline_library),
               'tasks':{name:sha(path) for name,path in sorted(filemap.items())}}
    if current != prior:
        raise ValueError('input modified during final evaluation')
    metrics = paired['metrics']
    # Work on EVERY final attempt, including unsolved tasks. Discovery and
    # unsuccessful candidate trials are not completely measured by journal.
    from native_paired_v150 import parse_jsonl
    config = {'budget':ns.budget,'max_size':ns.max_size,'fuel':ns.fuel,'max_built':ns.max_built}
    a = parse_jsonl(output/'paired/baseline.jsonl',task_ids=final,config=config,arm='baseline')
    b = parse_jsonl(output/'paired/learned.jsonl',task_ids=final,config=config,arm='learned')
    cost = {'final_built_all_baseline':sum(v['built'] for v in a['rows'].values()),
            'final_built_all_learned':sum(v['built'] for v in b['rows'].values())}
    cost['final_work_saved_including_failures'] = cost['final_built_all_baseline']-cost['final_built_all_learned']
    report = {'schema':'native-learning-campaign-v160',
              'qualification_scope':'local_native_custody_not_independent' if native else 'test_double_not_native',
              'native_binary_format_detected':native,'rust_source_build_verified':False,
              'independent_holdout':False,'external_replication':False,
              'native_learning_executed':native,
              'autonomous_concept_promoted':native and preflight['commits'] > 0,
              'transfer_improvement_demonstrated':native and preflight['commits'] > 0 and metrics['local_screen_passed'],
              'paired_screen_passed':metrics['local_screen_passed'],
              'source_sha256':prior,'custody_scan':scan,'journal_audit':preflight,
              'lineage':lineage,'paired_report_sha256':sha(output/'paired/report.json'),
              'learned_library_sha256':sha(learned),'ledger_sha256':sha(ledger),
              'paired_metrics':metrics,'work_accounting':cost,
              'qualification_warning':'Even positive local results need independent held-out tasks and source-to-binary reproduction.'}
    (output/'report.json').write_text(json.dumps(report,sort_keys=True,indent=2,allow_nan=False)+'\n',encoding='utf8')
    return report


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for flag in ('binary','learn-tasks','final-tasks','baseline-library','out-dir'):
        p.add_argument('--'+flag,required=True,type=Path)
    for flag in ('train','dev','final'):
        p.add_argument('--'+flag,required=True)
    p.add_argument('--rounds',type=int,default=3)
    p.add_argument('--budget',type=float,default=1.0)
    p.add_argument('--max-size',type=int,default=13)
    p.add_argument('--max-built',type=int,default=30000)
    p.add_argument('--fuel',type=int,default=20000)
    p.add_argument('--timeout',type=float,default=120)
    p.add_argument('--min-gain',type=float,default=.1)
    p.add_argument('--max-regression',type=float,default=.15)
    p.add_argument('--allow-script-test-double',action='store_true',help='tests ONLY; report cannot qualify as native')
    ns=p.parse_args(argv)
    try:
        result=execute(ns)
    except (OSError,ValueError,UnicodeError,subprocess.SubprocessError) as e:
        p.exit(2,'campaign rejected: '+str(e)+'\n')
    print(json.dumps({'qualification_scope':result['qualification_scope'],
        'native_mined_commits':result['lineage']['native_mined_promotion_count_reported'],
        'local_screen_passed':result['paired_screen_passed']}))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
