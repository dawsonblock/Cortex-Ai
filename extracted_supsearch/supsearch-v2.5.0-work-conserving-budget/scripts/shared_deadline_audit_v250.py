#!/usr/bin/env python3
"""Fail-closed consistency audit for v2.5 shared-phase time allowances.

The values are self-reported by the native Rust process. This does NOT
prove that a real executable ran, that wall-clock time was perfectly bounded,
or that learning transferred to unseen tasks.
"""
from __future__ import annotations
import argparse
import json
import math
from pathlib import Path
from evidence_integrity import strict_jsonl


def number(obj, key):
    value = obj.get(key)
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        raise ValueError('invalid finite time field: ' + key)
    return float(value)


def audit(path: Path) -> dict:
    if not path.is_file() or path.is_symlink() or not path.read_bytes().endswith(b'\n'):
        raise ValueError('missing, symlinked, or incomplete journal')
    rows = strict_jsonl(path, max_bytes=8*1024*1024)
    if len(rows) < 3 or rows[0].get('event') != 'start' or rows[-1].get('event') != 'session_completed':
        raise ValueError('complete native session required')
    start = rows[0]
    if start.get('schema_version') != 8 or type(start.get('shared_time_budget')) is not bool:
        raise ValueError('v2.5 shared-time metadata required')
    total = number(start, 'time_budget_secs')
    if total <= 0 or total > 3600:
        raise ValueError('invalid configured time budget')
    shared = start['shared_time_budget']
    count = 0
    tol = 0.000002  # serializer uses nine decimal places
    for event in rows[1:-1]:
        if event.get('event') != 'train_attempt':
            continue
        count += 1
        concept = number(event, 'composed_elapsed_secs')
        raw_limit = number(event, 'raw_time_limit_secs')
        raw_elapsed = number(event, 'raw_elapsed_secs')
        wall = number(event, 'wall_elapsed_secs')
        if wall + tol < max(concept, concept + raw_elapsed):
            raise ValueError('phase elapsed times exceed total reported wall time')
        if event.get('kind') not in ('composed','raw'):
            raise ValueError('unrecognized solve kind')
        if event['kind'] == 'composed' and (raw_limit != 0 or raw_elapsed != 0):
            raise ValueError('composed result executed unexpected raw phase')
        if shared and raw_limit > max(0.0, total-concept) + tol:
            raise ValueError('raw fallback received replenished time budget')
        if not shared and event['kind'] == 'raw' and abs(raw_limit-total) > tol:
            raise ValueError('legacy fallback time budget differs from configuration')
        if raw_elapsed > 0 and raw_limit <= 0:
            raise ValueError('raw solver ran after time budget exhausted')
        # The Rust solver checks time periodically; actual elapsed may exceed
        # the assigned duration, and this is explicitly NOT a hard SLA.
    if count == 0:
        raise ValueError('no train attempts recorded')
    return {'schema':'supsearch-shared-time-v250',
            'train_attempts_checked':count, 'configured_time_budget_secs':total,
            'shared_time_budget':shared,
            'self_reported_phase_accounting_consistent':True,
            'native_execution_independently_verified':False,
            'hard_wall_clock_enforced':False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger', type=Path, required=True)
    args=parser.parse_args()
    try:
        print(json.dumps(audit(args.ledger),sort_keys=True,indent=2))
    except (ValueError,OSError,UnicodeError) as e:
        parser.exit(2,'v2.5 deadline audit failed: '+str(e)+'\n')

if __name__=='__main__':
    main()
