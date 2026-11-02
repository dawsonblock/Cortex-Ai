#!/usr/bin/env python3
"""Local consistency audit for v2.2 optional concept admission gates.

Verifies that each promotion is linked to a measured candidate trial and
satisfies the session's frozen optional corpus-MDL/family thresholds. The
journal is *self-reported* and does not independently reconstruct the Rust
corpus or verify the claimed task-family structure. This is not a proof.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from reuse_promotion_audit_v190 import audit as audit_economic_receipts
from learning_work_audit_v170 import unique_pairs, nonnegative, MAX_JOURNAL


def signed(value, name):
    if type(value) is not int or not -(2**63) <= value <= 2**63 - 1:
        raise ValueError('invalid signed integer: ' + name)
    return value


def audit(path: Path):
    economic = audit_economic_receipts(path)
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_JOURNAL:
        raise ValueError('unsafe or oversized journal')
    raw = path.read_bytes()
    if not raw or not raw.endswith(b'\n'):
        raise ValueError('incomplete journal')
    events = [json.loads(x, object_pairs_hook=unique_pairs,
                         parse_constant=lambda x: (_ for _ in ()).throw(ValueError('nonfinite number')))
              for x in raw.decode('utf8').splitlines()]
    if not events or events[0].get('schema_version') != 8:
        raise ValueError('expected native schema-8 journal')
    cfg = events[0]
    if 'min_mdl_gain' not in cfg or 'min_positive_families' not in cfg:
        raise ValueError('missing v2.2 gate settings in start event')
    threshold_mdl = nonnegative(cfg['min_mdl_gain'],'min_mdl_gain',1_000_000)
    threshold_families = nonnegative(cfg['min_positive_families'],'min_positive_families',128)
    dev_count = nonnegative(cfg.get('dev'),'dev',200)
    if threshold_families > dev_count:
        raise ValueError('positive-family threshold exceeds development task count')
    trials={}
    promoted=[]
    for event in events[1:]:
        kind = event.get('event')
        if kind not in ('candidate_trial','promotion_intent'):
            continue
        key = (event.get('round'),event.get('term'),event.get('origin'),event.get('arity'))
        if type(key[0]) is not int or key[0] < 0 or type(key[1]) is not str or type(key[2]) is not str or type(key[3]) is not int or key[3] <= 0:
            raise ValueError('invalid candidate identity')
        mdl = signed(event.get('mdl_gain'),'mdl_gain')
        positive = nonnegative(event.get('positive_families'),'positive_families',dev_count)
        if kind == 'candidate_trial':
            if key in trials:
                raise ValueError('duplicate candidate trial')
            trials[key]=(mdl,positive)
        else:
            if key not in trials or trials[key] != (mdl,positive):
                raise ValueError('promotion disagrees with candidate evidence')
            if threshold_mdl and mdl < threshold_mdl:
                raise ValueError('promoted candidate fails corpus-compression gate')
            if positive < threshold_families:
                raise ValueError('promoted candidate fails development-family gate')
            promoted.append({'round':key[0],'concept':event.get('name'),
                             'net_training_corpus_ast_nodes':mdl,
                             'positive_development_families_claimed':positive})
    return {'schema':'concept-admission-audit-v220',
            'local_receipts_reconciled':True,
            'compression_gate':threshold_mdl,
            'development_family_gate':threshold_families,
            'promotions':promoted,
            'reuse_audit_rounds':economic['rounds'],
            'independent_corpus_recalculation':False,
            'independent_family_holdout':False,
            'native_binary_execution_confirmed':False,
            'note':'self-reported receipt consistency only; native qualification requires Cargo and an external evaluator'}


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('journal',type=Path)
    parser.add_argument('--out',type=Path)
    args=parser.parse_args(argv)
    try:
        result=audit(args.journal)
        encoded=json.dumps(result,sort_keys=True,indent=2,allow_nan=False)+'\n'
        if args.out:
            with args.out.open('x',encoding='utf8') as f: f.write(encoded)
        else:
            print(encoded,end='')
    except (KeyError,OSError,ValueError,UnicodeError) as exc:
        parser.exit(2,'concept admission audit rejected: '+str(exc)+'\n')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
