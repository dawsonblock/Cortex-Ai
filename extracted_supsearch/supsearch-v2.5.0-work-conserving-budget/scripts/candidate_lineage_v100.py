#!/usr/bin/env python3
"""Fail-closed internal lineage verifier for Supsearch v1.0.0 learning ledgers.

This only establishes consistency of locally supplied records; records can be
fabricated together. It is NOT a signature, proof, or independent evaluator.
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys

from evidence_integrity import strict_jsonl, reconcile_library

VALID_ORIGINS = frozenset({'native_mining', 'imported_candidate'})


def _integer(x, *, minimum=0):
    return type(x) is int and x >= minimum


def _trial_key(obj):
    if not _integer(obj.get('round')) or not _integer(obj.get('arity'), minimum=1) or obj['arity'] > 5:
        raise ValueError('invalid candidate round or composition arity')
    term, origin = obj.get('term'), obj.get('origin')
    if not isinstance(term, str) or not term or len(term) > 16384 or origin not in VALID_ORIGINS:
        raise ValueError('candidate term or origin invalid/missing')
    return (obj['round'], term, obj['arity'], origin)


def inspect(events, *, require_native_mined=False, require_final=False):
    if type(require_native_mined) is not bool or type(require_final) is not bool:
        raise ValueError('boolean enforcement arguments required')
    if not isinstance(events, list) or not events:
        raise ValueError('empty learning ledger')
    start = None
    trials = {}
    commits = []
    commit_origins = []
    pending = None
    phase = 'init'
    final_paired = False
    final_rows = 0
    for number, obj in enumerate(events, 1):
        if type(obj) is not dict or type(obj.get('event')) is not str:
            raise ValueError(f'line {number}: invalid event')
        kind = obj['event']
        if kind == 'start':
            if start is not None or phase != 'init':
                raise ValueError('more than one training session in ledger')
            if not _integer(obj.get('initial_concepts')):
                raise ValueError('invalid initial concept count')
            start = obj
            phase = 'train'
        elif phase == 'init':
            raise ValueError('ledger must start with start event')
        elif kind == 'candidate_trial':
            if phase != 'train' or pending is not None:
                raise ValueError('trial out of order')
            key = _trial_key(obj)
            if key in trials:
                raise ValueError('duplicated candidate trial')
            if type(obj.get('accepted')) is not bool:
                raise ValueError('candidate admission decision missing')
            for field in ('new_solved', 'lost_solved', 'severe_regressions'):
                if not _integer(obj.get(field)):
                    raise ValueError(f'invalid {field}')
            improvement = obj.get('improvement')
            if type(improvement) not in (int, float) or not math.isfinite(improvement):
                raise ValueError('invalid improvement')
            trials[key] = obj
        elif kind == 'promotion_intent':
            if phase != 'train' or pending is not None:
                raise ValueError('nested or late promotion intent')
            key = _trial_key(obj)
            matching = trials.get(key)
            if matching is None or not matching['accepted']:
                raise ValueError('promotion lacks matching accepted trial')
            if require_native_mined and obj['origin'] != 'native_mining':
                raise ValueError('imported candidate promotion forbidden')
            name = obj.get('name')
            if not isinstance(name, str) or not name or name in commits:
                raise ValueError('invalid/duplicate concept name')
            for attr in ('new_solved','lost_solved','severe_regressions'):
                if matching[attr] != obj.get(attr):
                    raise ValueError('promotion metrics disagree with trial')
            if obj.get('lost_solved') or obj.get('severe_regressions'):
                raise ValueError('promoted regressing candidate')
            if not _integer(obj.get('baseline_solved')) or not _integer(obj.get('candidate_solved')):
                raise ValueError('missing paired solved counts')
            if (obj['candidate_solved'] - obj['baseline_solved']) != obj['new_solved'] - obj['lost_solved']:
                raise ValueError('inconsistent paired solved counts')
            if abs(float(obj.get('improvement', float('nan'))) - float(matching['improvement'])) > 0.000002:
                raise ValueError('promotion improvement disagrees with trial')
            pending = name
            pending_origin = obj['origin']
        elif kind == 'promotion_committed':
            if phase != 'train' or pending is None or obj.get('name') != pending:
                raise ValueError('commit without matching promotion intent')
            if not _integer(obj.get('concept_count')) or obj['concept_count'] != start['initial_concepts'] + len(commits) + 1:
                raise ValueError('incorrect concept_count')
            commits.append(pending)
            commit_origins.append(pending_origin)
            pending = None
        elif kind == 'final_test_paired':
            if phase != 'train' or pending is not None or final_paired:
                raise ValueError('invalid final evaluation timing')
            if not _integer(obj.get('base_solved')) or not _integer(obj.get('learned_solved')):
                raise ValueError('incomplete final evaluation')
            if obj.get('learned_concepts') != start['initial_concepts'] + len(commits):
                raise ValueError('final concept count inconsistent')
            if obj.get('internal_test_only') is not True:
                raise ValueError('final result must be identified as internal')
            final_paired = True
            phase = 'final'
        elif kind == 'final_test':
            if phase != 'final' or not isinstance(obj.get('task'),str) or type(obj.get('solved')) is not bool:
                raise ValueError('invalid per-task final evidence')
            final_rows += 1
        elif kind in {'train_attempt','no_promotion','dev_baseline_work','round_work'}:
            if phase != 'train' or pending is not None:
                raise ValueError('training event after final or during promotion')
        else:
            raise ValueError(f'unknown event {kind}')
    if pending is not None:
        raise ValueError('unreconciled promotion intent')
    if require_final and (not final_paired or final_rows == 0):
        raise ValueError('final test missing')
    return {'schema': 'supsearch-concept-lineage-v1', 'consistent_local_record': True,
            'native_mined_promotions_only': set(commit_origins) <= {'native_mining'},
            'promotions': len(commits), 'promotion_origins': commit_origins, 'evaluated_candidate_arities': len(trials),
            'final_test_paired_record': final_paired, 'final_test_rows': final_rows,
            'independent_validation': False,
            'warning': 'Internal consistency only; no cryptographic attestation of execution'}


def verify_file(path: Path, *, require_native_mined=False, require_final=False, initial=None, learned=None):
    events = strict_jsonl(path)
    result = inspect(events, require_native_mined=require_native_mined, require_final=require_final)
    if (initial is None) != (learned is None):
        raise ValueError('initial and learned libraries must be supplied together')
    if initial is not None:
        result['library_reconciliation'] = reconcile_library(path, initial, learned)
    return result


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('ledger', type=Path)
    p.add_argument('--initial', type=Path)
    p.add_argument('--learned', type=Path)
    p.add_argument('--require-native-mined', action='store_true')
    p.add_argument('--require-final', action='store_true')
    ns=p.parse_args(argv)
    try:
        print(json.dumps(verify_file(ns.ledger, require_native_mined=ns.require_native_mined,
                                    require_final=ns.require_final, initial=ns.initial,
                                    learned=ns.learned), indent=2, sort_keys=True))
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f'learning lineage NOT qualified: {exc}', file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
