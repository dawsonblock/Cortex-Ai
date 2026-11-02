#!/usr/bin/env python3
"""Audit TWO native same-algorithm evaluation receipts under an identical state cap.

This tool never invokes the synthesizer, cannot authenticate results, and cannot
certify independently held-out tasks. Its numbers are descriptive comparisons
of input JSONL records. Native compilation and genuinely new data are separate.
"""
from __future__ import annotations
import argparse
from hashlib import sha256
import json
import math
from pathlib import Path
import re

from qualified_pipeline import parse_eval


def checked_regular(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 32 * 1024 * 1024:
        raise ValueError(f"unsafe, absent or oversized evaluation input: {path}")
    return path.read_bytes()


def compare_native_reports(base: Path, learned: Path, tasks: list[str], *,
                           budget: float, max_size: int, fuel: int, max_built: int) -> dict:
    if not tasks or len(tasks) > 200 or len(set(tasks)) != len(tasks):
        raise ValueError('task IDs must be nonempty, unique, and <= 200')
    if any(re.fullmatch(r'[A-Za-z0-9_-]+', t) is None for t in tasks):
        raise ValueError('unsafe task ID')
    if (type(max_built) is not int or not 1 <= max_built <= 100_000_000 or
        type(max_size) is not int or not 2 <= max_size <= 64 or
        type(fuel) is not int or not 1 <= fuel <= 10_000_000 or
        not math.isfinite(budget) or not 0 < budget <= 3600):
        raise ValueError('invalid frozen search settings')
    if base.resolve() == learned.resolve():
        raise ValueError('baseline and upgraded receipts must be distinct')
    prior_bytes, improved_bytes = checked_regular(base), checked_regular(learned)
    settings = {'budget': budget, 'max_size': max_size, 'fuel': fuel, 'max_built': max_built}
    b = parse_eval(base, tasks, 'concept', expected_settings=settings)
    u = parse_eval(learned, tasks, 'concept', expected_settings=settings)
    # The evaluator emits the native concept count in its first record.
    bm = json.loads(prior_bytes.splitlines()[0]); um = json.loads(improved_bytes.splitlines()[0])
    if (type(bm.get('concept_count')) is not int or type(um.get('concept_count')) is not int or
        bm['concept_count'] >= um['concept_count']):
        raise ValueError('upgraded concept library must have strictly more concepts')
    newly_solved = [t for t in tasks if u[t]['solved'] and not b[t]['solved']]
    lost = [t for t in tasks if b[t]['solved'] and not u[t]['solved']]
    common = [t for t in tasks if b[t]['solved'] and u[t]['solved']]
    before_cost = sum(b[t]['built'] for t in common)
    after_cost = sum(u[t]['built'] for t in common)
    return {
        'schema': 'supsearch-capped-paired-report-v1',
        'result_type': 'local_descriptive_comparison_not_independent_evidence',
        'native_execution_verified_by_this_script': False,
        'heldout_custody_verified_by_this_script': False,
        'frozen_settings': settings,
        'task_ids': tasks,
        'baseline_sha256': sha256(prior_bytes).hexdigest(),
        'upgraded_sha256': sha256(improved_bytes).hexdigest(),
        'initial_concepts': bm['concept_count'],
        'learned_concepts': um['concept_count'],
        'baseline_solved': sum(b[t]['solved'] for t in tasks),
        'learned_solved': sum(u[t]['solved'] for t in tasks),
        'newly_solved': newly_solved,
        'lost_solutions': lost,
        'common_solved': len(common),
        'common_solved_states_baseline': before_cost,
        'common_solved_states_learned': after_cost,
        'relative_state_saving_common_solved': ((before_cost-after_cost)/before_cost if before_cost else None),
        'per_task': [{'id':t, 'baseline_solved':b[t]['solved'], 'learned_solved':u[t]['solved'],
                      'baseline_built':b[t]['built'], 'learned_built':u[t]['built']} for t in tasks],
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline', type=Path, required=True)
    p.add_argument('--learned', type=Path, required=True)
    p.add_argument('--tasks', required=True, help='comma-separated frozen task IDs')
    p.add_argument('--budget', required=True, type=float)
    p.add_argument('--max-size', required=True, type=int)
    p.add_argument('--fuel', required=True, type=int)
    p.add_argument('--max-built', required=True, type=int)
    p.add_argument('--out', required=True, type=Path)
    ns = p.parse_args()
    if ns.out.is_symlink() or ns.out.resolve() in (ns.baseline.resolve(),ns.learned.resolve()):
        raise ValueError('report may not overwrite an input')
    report = compare_native_reports(ns.baseline, ns.learned, ns.tasks.split(','),
                                    budget=ns.budget,max_size=ns.max_size,fuel=ns.fuel,max_built=ns.max_built)
    # Exclusive create: a previous output cannot be silently overwritten.
    with ns.out.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps({'output':str(ns.out), 'baseline_solved':report['baseline_solved'],
                      'learned_solved':report['learned_solved'],
                      'new_solved':len(report['newly_solved']),
                      'lost':len(report['lost_solutions'])},sort_keys=True))


if __name__ == '__main__':
    main()
