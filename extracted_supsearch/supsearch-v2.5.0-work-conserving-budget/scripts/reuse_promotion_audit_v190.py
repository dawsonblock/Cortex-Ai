#!/usr/bin/env python3
"""Reconcile v1.9 optional search-expansion payback gate from native journal.

This is a deterministic consistency verifier over local, self-reported records.
It is NOT a CPU-time measurement, independent attestation, or future-reuse proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
from learning_work_audit_v170 import audit as work_audit, nonnegative, unique_pairs, MAX_JOURNAL, MAX_WORK


def bounded_signed(v, name):
    if type(v) is not int or abs(v) > MAX_WORK:
        raise ValueError(f'invalid signed integer: {name}')
    return v


def audit(path: Path) -> dict:
    work = work_audit(path)  # Reconcile all train, dev, candidate and round receipts first.
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JOURNAL:
        raise ValueError('missing, symlinked or oversized journal')
    raw = path.read_bytes()
    if not raw.endswith(b'\n') or not raw:
        raise ValueError('truncated journal')
    events = [json.loads(s, object_pairs_hook=unique_pairs,
                         parse_constant=lambda n: (_ for _ in ()).throw(ValueError('nonfinite: '+n)))
              for s in raw.decode('utf-8').splitlines()]
    initial = events[0]
    horizon = nonnegative(initial.get('expected_reuses'), 'expected_reuses', 1_000_000)
    cost_by_round = {r['round']: r['measured_built'] for r in work['rounds']}
    trial_by_key = {}
    intents = []
    for event in events[1:]:
        kind = event['event']
        if kind == 'candidate_trial':
            key = (event.get('round'), event.get('term'), event.get('origin'), event.get('arity'))
            if key in trial_by_key or type(key[0]) is not int or not isinstance(key[1],str) or not isinstance(key[2],str) or type(key[3]) is not int:
                raise ValueError('duplicate or malformed candidate trial')
            trial_by_key[key] = event
            bounded_signed(event.get('paired_savings'), 'trial paired savings')
        elif kind == 'promotion_intent':
            intents.append(event)
    seen_rounds = set()
    forecasts = []
    for event in intents:
        r = nonnegative(event.get('round'), 'promotion round', len(cost_by_round)-1)
        if r in seen_rounds:
            raise ValueError('multiple promotion intents in one round')
        seen_rounds.add(r)
        key = (r, event.get('term'), event.get('origin'), event.get('arity'))
        trial = trial_by_key.get(key)
        if trial is None or trial.get('accepted') is not True:
            raise ValueError('promotion not linked to eligible trial')
        savings = bounded_signed(event.get('paired_savings'), 'intent paired savings')
        if savings != trial['paired_savings']:
            raise ValueError('promotion savings mismatch trial')
        cost = nonnegative(event.get('round_measured_acquisition'), 'acquisition work')
        if cost != cost_by_round[r]:
            raise ValueError('promotion measured cost does not reconcile with round work')
        if nonnegative(event.get('assumed_reuses'), 'assumed_reuses', 1_000_000) != horizon:
            raise ValueError('promotion changed frozen horizon')
        if horizon:
            if savings <= 0:
                raise ValueError('cost-aware promotion has no paired savings')
            if savings*horizon < cost:
                raise ValueError('cost-aware promotion cannot break even within horizon')
            required = (cost + savings-1)//savings
        else:
            required = None
        forecasts.append({'round':r,'concept':event.get('name'),
                          'measured_acquisition_expansions':cost,'paired_dev_batch_savings':savings,
                          'assumed_reuses':horizon,'minimum_reuses_lower_bound':required})
    return {'schema':'reuse-gate-audit-v190','promotion_forecasts':forecasts,
            'expected_reuses':horizon, 'validated_local_receipt_consistency':True,
            'full_compute_cost_known':False,'future_task_reuse_demonstrated':False,
            'independently_attested':False, 'rounds':len(cost_by_round)}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('journal',type=Path)
    p.add_argument('--out',type=Path)
    args=p.parse_args(argv)
    try:
        result=audit(args.journal)
        encoded=json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n'
        if args.out:
            with args.out.open('x',encoding='utf8') as f: f.write(encoded)
        else: print(encoded,end='')
    except (OSError,ValueError,UnicodeError,KeyError) as exc:
        p.exit(2,'reuse gate audit rejected: '+str(exc)+'\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
