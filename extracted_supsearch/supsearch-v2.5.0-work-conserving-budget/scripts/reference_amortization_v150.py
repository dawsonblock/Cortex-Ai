#!/usr/bin/env python3
"""Measure TOTAL reference-learning work, including unsuccessful solves.

All fixtures here are known synthetic tasks; this is descriptive and not a
statistical or external qualification. Uses the unchanged v1.4 reference solver.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import hashlib
from reference_learning_v140 import (experiment,fixture,synthesize,var,seal,canonical,
                                      add,mine_from_training,checks_template_definition)


def evaluate_cost(*,max_size:int=9,max_built:int=30000,min_gain:float=.05) -> dict:
    record=experiment(max_size=max_size,max_built=max_built,require_gain=min_gain)
    tasks=fixture()
    train_cost=sum(synthesize(t,concept=None,max_size=max_size,max_built=max_built).built for t in tasks['training'])
    dev_before=sum(x['built'] for x in record['development']['before'].values())
    dev_after=sum(x['built'] for x in record['development']['after'].values())
    final_before=sum(x['built'] for x in record['final']['before'].values())
    final_after=sum(x['built'] for x in record['final']['after'].values())
    # Negative-control cost must also be included in discovery experimentation.
    null_cost=sum(synthesize(t,concept=var(0),max_size=max_size,max_built=max_built).built for t in tasks['development'])
    adaptation_cost=train_cost+dev_before+dev_after+null_cost
    dev_savings=dev_before-dev_after
    return {
        'schema':'reference-amortization-v150',
        'qualification_scope':'bundled synthetic Python reference only',
        'native_rust_executed':False,
        'independent_holdout':False,
        'learning_cost_includes_negative_control':True,
        'training_candidate_builds':train_cost,
        'development_baseline_builds':dev_before,
        'development_learned_builds':dev_after,
        'development_negative_control_builds':null_cost,
        'total_pre_final_experimental_builds':adaptation_cost,
        'dev_work_savings_per_full_repeated_batch':dev_savings,
        'dev_batch_repeats_to_recoup_experiment': (
            (adaptation_cost+dev_savings-1)//dev_savings if dev_savings>0 else None),
        'final_total_work_baseline':final_before,
        'final_total_work_learned':final_after,
        'final_all_task_work_delta':final_before-final_after,
        'final_new_solved':len(record['final']['metrics']['new_solved']),
        'final_lost_solved':len(record['final']['metrics']['lost_solved']),
        'note':'full-work costs include failed attempts and represent build counts, not time; comparisons over task families are synthetic and not independent',
        'reference_v140_sha256':hashlib.sha256(canonical(record)).hexdigest(),
    }


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out',type=Path)
    ns=p.parse_args()
    result=seal(evaluate_cost())
    data=json.dumps(result,indent=2,sort_keys=True)+'\n'
    if ns.out:
        with ns.out.open('x',encoding='utf8') as f:f.write(data)
    else:print(data)
    return 0

if __name__=='__main__':
    raise SystemExit(main())
