#!/usr/bin/env python3
"""Validate v1.7 native-search-work receipts; derive bounded payback analysis.

Evidence is a consistency check of self-reported *candidate expansions*. It
cannot attest binary provenance, miner CPU time, wall time, or independent transfer.
Older schema versions are rejected, not silently treated as complete evidence.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

MAX_JOURNAL = 8 * 1024 * 1024
MAX_WORK = 2**63 - 1


def unique_pairs(pairs):
    out = {}
    for key, value in pairs:
        if key in out:
            raise ValueError('duplicate JSON key: ' + key)
        out[key] = value
    return out


def nonnegative(value, label, maximum=MAX_WORK):
    if type(value) is not int or not 0 <= value <= maximum:
        raise ValueError('invalid nonnegative integer: ' + label)
    return value


def audit(path: Path) -> dict:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JOURNAL:
        raise ValueError('missing, symlinked or oversized native journal')
    data = path.read_bytes()
    if not data or not data.endswith(b'\n'):
        raise ValueError('missing/truncated native journal')
    records = []
    for i, line in enumerate(data.decode('utf8').splitlines(), 1):
        if not line or len(line.encode('utf8')) > 16384:
            raise ValueError(f'empty or oversized event at line {i}')
        r = json.loads(line, object_pairs_hook=unique_pairs,
                       parse_constant=lambda _: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if type(r) is not dict or type(r.get('event')) is not str:
            raise ValueError('malformed native event')
        records.append(r)
    starts = [e for e in records if e['event'] == 'start']
    if len(starts) != 1 or starts[0].get('schema_version') != 8:
        raise ValueError('requires exactly one v1.7 schema-8 session')
    start = starts[0]
    nrounds = nonnegative(start.get('rounds'), 'rounds', 100)
    dev_tasks = nonnegative(start.get('dev'), 'dev', 200)
    train_tasks = nonnegative(start.get('train'), 'train', 200)
    max_built = nonnegative(start.get('max_built'), 'max_built', 100_000_000)
    if not nrounds or not dev_tasks or not train_tasks:
        raise ValueError('empty learning session')
    summaries = {}
    observed = {i: {'train':0, 'baseline':None, 'trials':0, 'attempts':0, 'trial_count':0} for i in range(nrounds)}
    current = -1
    completed = False
    for e in records[1:]:
        kind = e['event']
        if completed:
            raise ValueError('events appear after completed session')
        if kind == 'session_completed':
            if e.get('rounds') != nrounds:
                raise ValueError('completion rounds mismatch')
            completed = True
            continue
        if kind in ('final_test_paired', 'final_test'):
            if len(summaries) != nrounds:
                raise ValueError('final evaluation before learning rounds complete')
            continue
        if kind in ('promotion_intent','promotion_committed','no_promotion'):
            if len(summaries) == nrounds:
                raise ValueError('promotion after all round receipts')
            continue
        if kind not in ('train_attempt','dev_baseline_work','candidate_trial','round_work'):
            raise ValueError('unrecognized accounting event: ' + kind)
        round_id = nonnegative(e.get('round'), 'round', nrounds-1)
        if round_id < current or round_id > current+1:
            raise ValueError('round order invalid')
        if round_id > current:
            if current >= 0 and current not in summaries:
                raise ValueError('previous round missing summary')
            current = round_id
        if round_id in summaries:
            raise ValueError('extra record after completed round')
        target = observed[round_id]
        if kind == 'train_attempt':
            if target['baseline'] is not None:
                raise ValueError('training after dev screening')
            b = nonnegative(e.get('built'), 'train built',2*max_built if max_built else MAX_WORK)
            cb = nonnegative(e.get('composed_built'), 'composed built',max_built if max_built else MAX_WORK)
            rb = nonnegative(e.get('raw_built'), 'raw built',max_built if max_built else MAX_WORK)
            if b != cb+rb:
                raise ValueError('training fallback work omitted or forged')
            target['train'] += b
            target['attempts'] += 1
        elif kind == 'dev_baseline_work':
            if target['baseline'] is not None:
                raise ValueError('duplicate development baseline')
            if e.get('tasks') != dev_tasks:
                raise ValueError('development task count mismatch')
            target['baseline'] = nonnegative(e.get('built'),'dev baseline',dev_tasks*max_built if max_built else MAX_WORK)
        elif kind == 'candidate_trial':
            if target['baseline'] is None:
                raise ValueError('candidate trial before development baseline')
            target['trials'] += nonnegative(e.get('built'),'candidate trial',dev_tasks*max_built if max_built else MAX_WORK)
            target['trial_count'] += 1
        elif kind == 'round_work':
            if target['baseline'] is None:
                raise ValueError('round work before development baseline')
            expected = {'train_built':target['train'], 'dev_baseline_built':target['baseline'],
                        'dev_trial_built':target['trials'],
                        'measured_built':target['train']+target['baseline']+target['trials']}
            for label, value in expected.items():
                if nonnegative(e.get(label),label) != value:
                    raise ValueError('round receipt disagrees with detailed work: '+label)
            summaries[round_id] = dict(expected,round=round_id,train_attempts=target['attempts'],
                                       candidate_trials=target['trial_count'])
    if not completed or set(summaries) != set(range(nrounds)):
        raise ValueError('unfinished session or missing accounting summaries')
    total = sum(s['measured_built'] for s in summaries.values())
    return {'schema':'search-work-v170', 'source':'schema-8-self-reported-native-journal',
            'rounds':[summaries[i] for i in range(nrounds)],
            'training_built':sum(s['train_built'] for s in summaries.values()),
            'dev_baseline_built':sum(s['dev_baseline_built'] for s in summaries.values()),
            'dev_candidate_trial_built':sum(s['dev_trial_built'] for s in summaries.values()),
            'accounted_search_expansions_lower_bound':total,
            'unmetered':['abstraction mining','term normalisation','verification CPU',
                         'journal I/O','failed startup','independent evaluation'],
            'complete_expansion_cost':False,
            'native_execution_independently_attested':False,
            'qualification':'local_receipt_consistency_only'}


def amortization(work:dict, final_base:int, final_learned:int, repetitions:int=1) ->dict:
    if type(repetitions) is not int or not 1 <= repetitions <= 1_000_000:
        raise ValueError('repetitions out of range')
    base = nonnegative(final_base,'final baseline')
    learned = nonnegative(final_learned,'final learned')
    lower_bound = nonnegative(work['accounted_search_expansions_lower_bound'],'learning lower bound')
    saved_per_batch = base-learned
    # Training cost is only a lower bound; break-even is therefore a lower bound
    # on repetitions, not a demonstrated actual payback.
    break_even_lower_bound = (lower_bound+saved_per_batch-1)//saved_per_batch if saved_per_batch>0 else None
    net_upper_bound = repetitions*saved_per_batch-lower_bound
    return {'final_work_baseline':base,'final_work_learned':learned,
            'saved_search_expansions_per_final_batch':saved_per_batch,
            'repetitions_assumed':repetitions,
            'net_search_expansion_savings_upper_bound':net_upper_bound,
            'minimum_repeats_to_recoup_measured_learning_lower_bound':break_even_lower_bound,
            'fully_amortized':False,
            'reason':'mining overhead and other learning costs are not measured; evaluation batch may not repeat',
            'net_positive_under_current_assumptions_possible':net_upper_bound>0}


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('journal',type=Path)
    p.add_argument('--baseline-built',type=int)
    p.add_argument('--learned-built',type=int)
    p.add_argument('--repetitions',type=int,default=1)
    p.add_argument('--out',type=Path)
    ns=p.parse_args(argv)
    try:
        result=audit(ns.journal)
        if (ns.baseline_built is None) != (ns.learned_built is None):
            raise ValueError('provide both final-work values')
        if ns.baseline_built is not None:
            result['amortization']=amortization(result,ns.baseline_built,ns.learned_built,ns.repetitions)
        encoded=json.dumps(result,indent=2,sort_keys=True,allow_nan=False)+'\n'
        if ns.out:
            with ns.out.open('x') as f:f.write(encoded)
        else: print(encoded,end='')
    except (OSError,ValueError,UnicodeError) as exc:
        p.exit(2,'learning-work audit rejected: '+str(exc)+'\n')
    return 0

if __name__=='__main__':
    raise SystemExit(main())
