#!/usr/bin/env python3
"""Execute same-algorithm concept-vs-concept paired evaluations with a native binary.

This program never performs training or promotion and never claims independent
custody. Passing an executable is NOT proof it was built from this source tree.
A script executable is permitted only through --allow-script-test-double, in
which case the report explicitly says no native executable was qualified.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
from typing import Any

MAX_FILE = 2 * 1024 * 1024


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def only_object(pairs):
    value = {}
    for k, v in pairs:
        if k in value:
            raise ValueError('duplicate JSON object key: '+k)
        value[k] = v
    return value


def reject_constant(value):
    raise ValueError('nonfinite JSON number: '+value)


def parse_jsonl(path: Path, *, task_ids: list[str], config: dict[str, Any], arm: str) -> dict:
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_FILE:
        raise ValueError('missing/unsafe/oversized evaluation report')
    raw = path.read_text(encoding='utf-8')
    if not raw.endswith('\n'):
        raise ValueError('truncated JSONL report')
    lines = raw.splitlines()
    if len(lines) != len(task_ids)+1:
        raise ValueError('unexpected evaluation record count')
    records = [json.loads(line, object_pairs_hook=only_object,
                          parse_constant=reject_constant) for line in lines]
    meta = records[0]
    if not isinstance(meta, dict) or meta.get('event') != 'evaluation_meta' or meta.get('schema_version') != 5:
        raise ValueError('invalid evaluator schema')
    if meta.get('mode') != 'concept' or meta.get('task_count') != len(task_ids):
        raise ValueError('not the requested concept-mode task batch')
    for key in ('budget','max_size','fuel','max_built'):
        value = meta.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value != config[key]:
            raise ValueError('evaluation settings mismatch for '+key)
    concept_count = meta.get('concept_count')
    if type(concept_count) is not int or concept_count < 0 or concept_count > 256:
        raise ValueError('invalid concept count')
    out = {}
    for task, row in zip(task_ids, records[1:]):
        if not isinstance(row, dict) or row.get('event') != 'evaluation' or row.get('task') != task or row.get('mode') != 'concept':
            raise ValueError('out-of-order, duplicate, or malformed task result')
        if type(row.get('solved')) is not bool or type(row.get('aborted')) is not bool:
            raise ValueError('invalid result booleans')
        for field in ('built','kept'):
            if type(row.get(field)) is not int or row[field] < 0 or row[field] > config['max_built']:
                raise ValueError('invalid work count: '+field)
        if row['kept'] > row['built']:
            raise ValueError('more retained than built candidates')
        elapsed = row.get('elapsed_secs')
        if type(elapsed) not in (int, float) or not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError('invalid elapsed time')
        if row['solved'] and row['aborted']:
            raise ValueError('solved but aborted')
        out[task] = row
    return {'concept_count':concept_count,'rows':out, 'sha256':digest(path), 'arm':arm}


def compare(base: dict, improved: dict, max_regression: float, min_gain: float) -> dict:
    a, b = base['rows'], improved['rows']
    new = sorted(k for k in a if not a[k]['solved'] and b[k]['solved'])
    lost = sorted(k for k in a if a[k]['solved'] and not b[k]['solved'])
    shared = sorted(k for k in a if a[k]['solved'] and b[k]['solved'])
    old_work = sum(a[k]['built'] for k in shared)
    new_work = sum(b[k]['built'] for k in shared)
    regression = sorted(k for k in shared if b[k]['built'] > (1+max_regression)*max(1,a[k]['built']) + 2)
    gain = (old_work-new_work)/old_work if old_work else None
    accepted = (not lost and not regression and (bool(new) or (gain is not None and gain >= min_gain)))
    return {'baseline_solved':sum(r['solved'] for r in a.values()),
            'learned_solved':sum(r['solved'] for r in b.values()),
            'newly_solved':new, 'lost_solved':lost,'severe_regressions':regression,
            'jointly_solved':len(shared),'shared_work_baseline':old_work,
            'shared_work_learned':new_work,'shared_work_reduction':gain,
            'local_screen_passed':accepted,
            'note':'local diagnostic screen only; not a promotion authorization or independent holdout'}


def is_native_executable(path: Path) -> bool:
    with path.open('rb') as file:
        prefix = file.read(4)
    return (prefix == b'\x7fELF' or prefix[:2] == b'MZ' or
            prefix in (b'\xcf\xfa\xed\xfe',b'\xfe\xed\xfa\xcf',
                       b'\xca\xfe\xba\xbe',b'\xbe\xba\xfe',b'\xce\xfa\xed\xfe'))


def protect_paths(taskdir: Path, base: Path, upgraded: Path, binary: Path, out: Path) -> None:
    for p in (taskdir,base,upgraded,binary):
        if p.is_symlink() or not p.exists():
            raise ValueError('missing or symlinked input: '+str(p))
    for p in (base,upgraded,binary):
        if not p.is_file() or p.stat().st_size > 32 * MAX_FILE:
            raise ValueError('invalid library or binary: '+str(p))
    if not taskdir.is_dir():
        raise ValueError('invalid task directory')
    dst = out.resolve()
    for input_path in (taskdir, base, upgraded, binary):
        inp = input_path.resolve()
        if dst == inp or dst.is_relative_to(inp) or inp.is_relative_to(dst):
            raise ValueError('output overlaps protected input')
    if out.exists():
        raise ValueError('output directory already exists')


def run(ns: argparse.Namespace) -> dict:
    protect_paths(ns.tasks_dir, ns.baseline_library, ns.learned_library, ns.binary, ns.out_dir)
    binary=ns.binary.resolve()
    tasksdir=ns.tasks_dir.resolve()
    baseline=ns.baseline_library.resolve()
    learned=ns.learned_library.resolve()
    out=ns.out_dir.resolve()
    ids=[x.strip() for x in ns.tasks.split(',')]
    if not 1 <= len(ids) <= 200 or any(not x or not all(c.isascii() and (c.isalnum() or c in '_-') for c in x) for x in ids) or len(set(ids))!=len(ids):
        raise ValueError('invalid or duplicate task ID')
    if not (0 < ns.budget <= 3600 and 2 <= ns.max_size <= 64 and
            0 < ns.fuel <= 10_000_000 and 0 < ns.max_built <= 100_000_000 and
            0 <= ns.min_gain <= 1 and 0 <= ns.max_regression <= 10):
        raise ValueError('invalid evaluation limits')
    if not 0 < ns.timeout <= 3600 or not math.isfinite(ns.timeout):
        raise ValueError("invalid subprocess timeout")
    native=is_native_executable(binary)
    if not native and not ns.allow_script_test_double:
        raise ValueError('not a native executable; test doubles require explicit opt-in')
    task_hashes={}
    for id in ids:
        p=tasksdir/(id+'.tsk')
        if not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_FILE:
            raise ValueError('missing, symlinked or oversized task: '+id)
        task_hashes[id]=digest(p)
    config={'budget':ns.budget,'max_size':ns.max_size,'fuel':ns.fuel,'max_built':ns.max_built}
    prior={'binary':digest(binary),'baseline_library':digest(baseline),
           'learned_library':digest(learned), 'tasks':task_hashes}
    out.mkdir(parents=True,exist_ok=False)
    arms={}
    # Both arms use precisely the same native concept-search algorithm.
    for name, lib in [('baseline',baseline),('learned',learned)]:
        output=out/(name+'.jsonl')
        command=[str(binary),'evaluate',str(tasksdir),'--tasks',','.join(ids),
                 '--mode','concept','--library',str(lib),'--out',str(output),
                 '--budget',str(ns.budget),'--max-size',str(ns.max_size),
                 '--fuel',str(ns.fuel),'--max-built',str(ns.max_built)]
        try:
            proc=subprocess.run(command,capture_output=True,text=True,
                                timeout=ns.timeout,check=False)
        except subprocess.TimeoutExpired as e:
            raise ValueError(name+' evaluation timed out; partial output quarantined') from e
        if proc.returncode != 0:
            raise ValueError(name+' evaluation failed (exit '+str(proc.returncode)+'): '+proc.stderr[:400])
        arms[name]=parse_jsonl(output,task_ids=ids,config=config,arm=name)
    now={'binary':digest(binary),'baseline_library':digest(baseline),
         'learned_library':digest(learned),
         'tasks':{id:digest(tasksdir/(id+'.tsk')) for id in ids}}
    if prior != now:
        raise ValueError('input changed during evaluation; output quarantined')
    report={'schema_version':'native-paired-v150','qualification_scope':
            'local_native_executable_not_independent' if native else 'test_double_not_native',
            'native_binary_format_detected':native,
            'rust_source_build_verified':False,
            'independent_holdout':False,
            'promotion_authorization':False,
            'solver_algorithm_both_arms':'concept_solve',
            'inputs_sha256':prior,'limits':config,
            'baseline':{'concept_count':arms['baseline']['concept_count'],'sha256':arms['baseline']['sha256']},
            'learned':{'concept_count':arms['learned']['concept_count'],'sha256':arms['learned']['sha256']},
            'metrics':compare(arms['baseline'],arms['learned'],ns.max_regression,ns.min_gain)}
    path=out/'report.json'
    with path.open('x',encoding='utf-8') as f:
        json.dump(report,f,sort_keys=True,indent=2,allow_nan=False)
        f.write('\n')
    return report


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--binary',required=True,type=Path)
    p.add_argument('--tasks-dir',required=True,type=Path)
    p.add_argument('--tasks',required=True)
    p.add_argument('--baseline-library',required=True,type=Path)
    p.add_argument('--learned-library',required=True,type=Path)
    p.add_argument('--out-dir',required=True,type=Path)
    p.add_argument('--budget',type=float,default=1.0)
    p.add_argument('--max-size',type=int,default=13)
    p.add_argument('--fuel',type=int,default=20000)
    p.add_argument('--max-built',type=int,default=30000)
    p.add_argument('--min-gain',type=float,default=.1)
    p.add_argument('--max-regression',type=float,default=.15)
    p.add_argument('--timeout',type=float,default=120.0)
    p.add_argument('--allow-script-test-double',action='store_true')
    ns=p.parse_args(argv)
    try: report=run(ns)
    except (ValueError, OSError) as e:
        p.exit(2,'paired evaluation rejected: '+str(e)+'\n')
    print(json.dumps({'status':'local_pair_executed','qualification_scope':report['qualification_scope'],
                      'metrics':report['metrics']},sort_keys=True))
    return 0

if __name__=='__main__':
    raise SystemExit(main())
