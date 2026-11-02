#!/usr/bin/env python3
"""Preregistered, family-aware evaluation of supsearch EXTERNAL replay artifacts.

This is a local evaluator helper, NOT third-party custody or a proof of
improved general intelligence. A frozen campaign document and its digest are
not independently timestamped. An evaluator must own the preregistration,
replay inputs, and secret separately from the training operator.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from hashlib import sha256
import json
import math
from pathlib import Path
import random
import re
import sys
from typing import Any

from evidence_integrity import strict_json_loads
from external_replay import verify_result
from qualified_pipeline import parse_eval, checked_regular, binary_format
from evidence_integrity import library_entries
from paired_statistics import exact_mcnemar
from task_custody import canonical_examples

SCHEMA = 'supsearch-transfer-campaign-v2'
LEGACY_SCHEMA = 'supsearch-transfer-campaign-v1'
TASK_ID = re.compile(r'^[A-Za-z0-9_-]{1,96}$')
FAMILY_ID = re.compile(r'^[A-Za-z0-9_-]{1,96}$')
MAX_TASKS = 1000
MAX_REPLAYS = 100
MAX_JSON = 1024 * 1024


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def load_object(path: Path) -> dict:
    checked_regular(path)
    if path.stat().st_size > MAX_JSON:
        raise ValueError('campaign input exceeds 1 MiB')
    obj = strict_json_loads(path.read_text(encoding='utf8'))
    if not isinstance(obj, dict):
        raise ValueError('campaign input must be a JSON object')
    return obj


def validate_task_map(mapping: dict) -> dict:
    if not isinstance(mapping, dict) or not 1 <= len(mapping) <= MAX_TASKS:
        raise ValueError('task map must contain 1..1000 entries')
    result = {}
    hashes = set()
    for name, data in mapping.items():
        if not isinstance(name, str) or not TASK_ID.fullmatch(name):
            raise ValueError('invalid task ID')
        if not isinstance(data, dict) or set(data) != {'family', 'sha256'}:
            raise ValueError('task descriptors must contain family and sha256 only')
        family, value = data['family'], data['sha256']
        if not isinstance(family, str) or not FAMILY_ID.fullmatch(family):
            raise ValueError(f'bad family for {name}')
        if not isinstance(value, str) or not re.fullmatch('[0-9a-f]{64}', value):
            raise ValueError(f'bad task hash for {name}')
        if value in hashes:
            raise ValueError('duplicate task file digests in campaign task map')
        hashes.add(value)
        result[name] = {'family': family, 'sha256': value}
    return dict(sorted(result.items()))


def make_protocol(tasks: dict, *, min_families: int = 3, min_tasks: int = 20,
                  min_new: int = 3, min_effect: float = 0.05,
                  max_lost: int = 0, alpha: float = 0.05,
                  min_positive_families: int = 2, min_family_size: int = 2,
                  schema: str = SCHEMA, require_native_mined: bool = True) -> dict:
    if schema not in (SCHEMA, LEGACY_SCHEMA):
        raise ValueError('unsupported preregistration schema')
    tasks = validate_task_map(tasks)
    for name, value in [('min_families', min_families), ('min_tasks', min_tasks),
                        ('min_new', min_new), ('max_lost', max_lost),
                        ('min_positive_families', min_positive_families),
                        ('min_family_size', min_family_size)]:
        if type(value) is not int or value < 0 or value > MAX_TASKS:
            raise ValueError(f'invalid {name}')
    if not isinstance(min_effect, (int,float)) or not math.isfinite(min_effect) or not 0 <= min_effect <= 1:
        raise ValueError('invalid min_effect')
    if not isinstance(alpha, (int,float)) or not math.isfinite(alpha) or not 0 < alpha < 1:
        raise ValueError('invalid alpha')
    if type(require_native_mined) is not bool:
        raise ValueError('invalid require_native_mined')
    if schema == SCHEMA and min_positive_families > min_families:
        raise ValueError('minimum positive families exceeds minimum families')
    if schema == SCHEMA and min_family_size < 1:
        raise ValueError('minimum tasks per family must be positive')
    content = {'schema': schema, 'tasks': tasks,
               'gate': {'min_families': min_families, 'min_tasks': min_tasks,
                        'min_newly_solved': min_new, 'max_regressions': max_lost,
                        'min_paired_success_difference': float(min_effect),
                        'alpha': float(alpha), 'require_native_mined': require_native_mined},
               'metric': 'paired_success_gain_with_cluster_bootstrap_and_exact_mcnemar',
               'role': 'preregistration_not_independent_timestamp'}
    if schema == SCHEMA:
        content['gate']['min_positive_families'] = min_positive_families
        content['gate']['min_family_size'] = min_family_size
    return {**content, 'content_sha256': sha256(canonical(content)).hexdigest()}


def validate_protocol(obj: dict) -> dict:
    if set(obj) != {'schema','tasks','gate','metric','role','content_sha256'} or obj.get('schema') not in (SCHEMA, LEGACY_SCHEMA):
        raise ValueError('unrecognized protocol')
    expected = make_protocol(obj['tasks'], min_families=obj['gate']['min_families'],
                             min_tasks=obj['gate']['min_tasks'], min_new=obj['gate']['min_newly_solved'],
                             min_effect=obj['gate']['min_paired_success_difference'],
                             max_lost=obj['gate']['max_regressions'], alpha=obj['gate']['alpha'],
                             require_native_mined=obj['gate']['require_native_mined'],
                             min_positive_families=obj['gate'].get('min_positive_families', 0),
                             min_family_size=obj['gate'].get('min_family_size', 1),
                             schema=obj['schema'])
    if obj != expected:
        raise ValueError('preregistered protocol content or digest changed')
    return obj


def cluster_ci(rows: list[tuple[str,int]], alpha: float, *, reps: int = 10000, seed: int = 808) -> list[float]:
    """Percentile cluster bootstrap; families sampled with replacement, tasks kept together.

    Task-weighted success-difference statistic is maintained on each cluster
    resample. This reflects between-family uncertainty, not independent tasks.
    """
    groups = defaultdict(list)
    for fam, delta in rows:
        groups[fam].append(delta)
    families = sorted(groups)
    if len(families) < 2:
        raise ValueError('at least two families are needed for cluster uncertainty')
    rng = random.Random(seed)
    counts = [len(groups[f]) for f in families]
    totals = [sum(groups[f]) for f in families]
    n = len(families)
    bootstrap = []
    for _ in range(reps):
        picked = [rng.randrange(n) for _ in range(n)]
        denom = sum(counts[i] for i in picked)
        bootstrap.append(sum(totals[i] for i in picked) / denom)
    bootstrap.sort()
    lo = max(0, min(reps - 1, int((alpha/2) * reps)))
    hi = max(0, min(reps - 1, int((1-alpha/2) * reps)))
    return [bootstrap[lo], bootstrap[hi]]


def _replay_records(out: Path) -> tuple[dict,dict,dict,dict,dict]:
    # verify_result independently recomputes the report's per-task metrics
    # against immutable local files before we parse them again.
    verify_result(out)
    snapshot = load_object(out / 'snapshot.json')
    report = load_object(out / 'report.json')
    payload = snapshot['source_payload']
    tasks = sorted(payload['task_sha256'])
    records = {}
    specs = {'base':('concept_baseline', 'initial.tsv'),
             'learned':('concept_upgraded','working.tsv')}
    for category, (name, lib) in specs.items():
        library_size = len(library_entries(out / 'inputs' / lib))
        if payload['mode'] == 'per_task_counterbalanced':
            data = {}
            for tid in tasks:
                path = checked_regular(out / 'results' / f'{name}__{tid}.jsonl')
                data.update(parse_eval(path,[tid],'concept',expected_concepts=library_size,expected_settings=payload))
        elif payload['mode'] == 'batch_baseline_first':
            path = checked_regular(out / 'results' / f'{name}.jsonl')
            data = parse_eval(path,tasks,'concept',expected_concepts=library_size,expected_settings=payload)
        else:
            raise ValueError('unsupported evaluation order protocol')
        records[category] = data
    return snapshot, report, payload, records['base'], records['learned']


def evaluate(protocol: dict, replay_dirs: list[Path], *, attestation_key: Path | None = None,
             native_qualification: Path | None = None) -> dict:
    protocol = validate_protocol(protocol)
    if not 1 <= len(replay_dirs) <= MAX_REPLAYS:
        raise ValueError('1..100 replay directories required')
    task_map = protocol['tasks']
    seen_tasks: set[str] = set()
    seen_trials: set[str] = set()
    rows: list[tuple[str,int]] = []
    lineage = set()
    orders = set()
    training = set()
    successes = {'base':0, 'learned':0, 'new':0, 'lost':0}
    claims = []
    promotions = []
    seen_examples: dict[str,str] = {}
    attest_key_id = None
    native_proof = load_object(native_qualification) if native_qualification is not None else None
    if native_proof is not None and (native_proof.get('schema') != 'supsearch-native-gate-v1'
        or native_proof.get('state') != 'native_compiled_smoke_passed'
        or native_proof.get('binary_format') not in ('elf','mach_o','pe')
        or native_proof.get('independent_holdout_run') is not False
        or type(native_proof.get('binary_sha256')) is not str):
        raise ValueError('invalid native qualification report')
    for out in replay_dirs:
        if out.is_symlink() or not out.is_dir():
            raise ValueError('unsafe replay directory')
        snapshot, report, payload, base, learned = _replay_records(out)
        if binary_format(checked_regular(out / 'inputs' / 'native_binary')) not in ('elf', 'mach_o', 'pe'):
            raise ValueError('non-native executable: mock and script replays cannot qualify')
        trial = report['trial_key']
        if trial in seen_trials:
            raise ValueError('duplicate evaluation trial key')
        seen_trials.add(trial)
        if report.get('custody_label') == 'synthetic_fixture_not_holdout':
            raise ValueError('synthetic evaluation cannot be admitted to a transfer campaign')
        if report.get('custody_label') == 'local_related_prefix_holdout_not_independent':
            raise ValueError('evaluation allowed overlapping train/dev/test prefix families')
        if snapshot.get('label') != report.get('custody_label'):
            raise ValueError('custody mismatch')
        if report.get('claimed_independent_validation') is not False:
            raise ValueError('invalid independence assertion')
        lineage.add((payload['binary_sha256'],payload['initial_library_sha256'],payload['trained_library_sha256'],payload['learning_ledger_sha256']))
        orders.add(payload['mode'])
        training.add(report['candidate_origin'])
        promotions.append(report['promotions'])
        if attestation_key is not None:
            from attested_replay import verify as verify_attested
            proof = verify_attested(out, attestation_key)
            if not proof['authenticated_evidence'] or proof['trial_key'] != trial:
                raise ValueError('attestation does not match replay')
            if attest_key_id is None:
                attest_key_id = proof['key_id']
            if proof['key_id'] != attest_key_id:
                raise ValueError('multiple attestation signers in a single campaign')
        for tid, before in base.items():
            if tid not in task_map or tid in seen_tasks:
                raise ValueError(f'unpreregistered or duplicate task: {tid}')
            seen_tasks.add(tid)
            descriptor = task_map[tid]
            # The native replay's task inputs are retained in the sealed tree.
            # Check test-versus-test examples across ALL replay batches as well.
            for example in canonical_examples(out / 'private_tasks' / f'{tid}.tsk'):
                prior = seen_examples.get(example)
                if prior is not None and prior != tid:
                    raise ValueError(f'cross-task test example reused: {prior}, {tid}')
                seen_examples[example] = tid
            if descriptor['sha256'] != payload['task_sha256'][tid]:
                raise ValueError(f'task digest not preregistered: {tid}')
            if tid not in learned:
                raise ValueError('missing upgraded evaluation row')
            after = learned[tid]
            b,a = bool(before['solved']),bool(after['solved'])
            successes['base'] += b
            successes['learned'] += a
            successes['new'] += int(a and not b)
            successes['lost'] += int(b and not a)
            rows.append((descriptor['family'],int(a)-int(b)))
        claims.append({'trial_key': trial,'task_count':len(base), 'custody_label':report['custody_label']})
    if seen_tasks != set(task_map):
        raise ValueError(f'campaign incomplete: {len(set(task_map)-seen_tasks)} preregistered tasks were not evaluated')
    if len(lineage) != 1:
        raise ValueError('different binaries or concept-learning lineages within campaign')
    if len(orders) != 1:
        raise ValueError('mixed counterbalancing schemes within campaign')
    if len(training) != 1:
        raise ValueError('mixed learning origins within campaign')
    if len(set(promotions)) != 1:
        raise ValueError('inconsistent promotion counts across repeated replays')
    n = len(rows)
    families = set(f for f,_ in rows)
    family_delta = {fam: sum(delta for f, delta in rows if f == fam) for fam in sorted(families)}
    family_sizes = {fam: sum(1 for f, _ in rows if f == fam) for fam in sorted(families)}
    positive_families = sum(delta > 0 for delta in family_delta.values())
    loo_effects = {fam: (sum(d for f,d in rows if f != fam) /
                         max(1, sum(f != fam for f,_ in rows))) for fam in sorted(families)}
    effect = (successes['learned']-successes['base'])/n
    gate = protocol['gate']
    interval = cluster_ci(rows,gate['alpha']) if len(families)>=2 else None
    p = exact_mcnemar(successes['new'],successes['lost'])
    failures = []
    if n < gate['min_tasks']: failures.append('insufficient_tasks')
    if len(families) < gate['min_families']: failures.append('insufficient_independent_families')
    if any(size < gate.get('min_family_size', 1) for size in family_sizes.values()):
        failures.append('undersampled_task_family')
    if positive_families < gate.get('min_positive_families', 0):
        failures.append('effect_concentrated_in_too_few_families')
    if successes['new'] < gate['min_newly_solved']: failures.append('too_few_new_solutions')
    if successes['lost'] > gate['max_regressions']: failures.append('too_many_regressions')
    if effect < gate['min_paired_success_difference']: failures.append('effect_below_preregistered_threshold')
    if interval is None or interval[0] <= 0: failures.append('cluster_uncertainty_not_excluding_zero')
    if p > gate['alpha']: failures.append('exact_paired_test_not_significant')
    if gate['require_native_mined'] and training != {'native_mining_only'}: failures.append('external_candidate_proposals')
    if promotions[0] < 1: failures.append('no_promotions')
    if native_proof is None or native_proof['binary_sha256'] != next(iter(lineage))[0]:
        failures.append('native_build_qualification_missing_or_wrong_binary')
    if len(orders)==1 and 'per_task_counterbalanced' not in orders: failures.append('test_order_not_counterbalanced')
    # Explicitly separates local passing of preregistered thresholds from
    # independent scientific replication; no local file can establish custody.
    return {'schema':protocol['schema'], 'protocol_sha256':protocol['content_sha256'],
            'status':'local_evidence_qualified' if not failures else 'local_evidence_not_qualified',
            'independently_validated':False,
            'statistical_significance_is_not_causal_proof':True,
            'task_count':n, 'family_count':len(families), 'replay_count':len(replay_dirs),
            'positive_family_count':positive_families, 'family_net_deltas':family_delta,
            'family_task_counts':family_sizes,
            'leave_one_family_out_effects':loo_effects,
            'promotion_count':promotions[0], 'candidate_origin':next(iter(training)),
            'evaluation_order':next(iter(orders)),
            'baseline_solved':successes['base'],'learned_solved':successes['learned'],
            'newly_solved':successes['new'],'regressions':successes['lost'],
            'paired_success_difference':effect, 'family_bootstrap_ci':interval,
            'exact_mcnemar_p':p, 'attested_hmac_key_id':attest_key_id,
            'native_qualification_checked':native_proof is not None and native_proof['binary_sha256']==next(iter(lineage))[0],
            'attestation_supplies_integrity_not_external_custody':True,
            'failures':failures, 'trials':claims,
            'limitations':['Only finite-example correctness; no universal program proof',
                           'Family-bootstrap assumes families are exchangeable',
                           'Fixed tasks and threshold selection require genuinely prospective evaluator custody',
                           'This program cannot assert operator/evaluator independence']}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest='operation', required=True)
    freeze = sub.add_parser('freeze',help='freeze evaluator-owned task/family/digest map BEFORE replays')
    freeze.add_argument('--task-map',type=Path,required=True)
    freeze.add_argument('--out',type=Path,required=True)
    freeze.add_argument('--min-tasks',type=int,default=20)
    freeze.add_argument('--min-families',type=int,default=3)
    freeze.add_argument('--min-positive-families',type=int,default=2,
                        help='at least this many families must have net positive outcomes')
    freeze.add_argument('--min-family-size',type=int,default=2,
                        help='minimum evaluation tasks in every declared family')
    freeze.add_argument('--min-new',type=int,default=3)
    freeze.add_argument('--min-effect',type=float,default=0.05)
    freeze.add_argument('--max-lost',type=int,default=0)
    freeze.add_argument('--alpha',type=float,default=0.05)
    assess = sub.add_parser('assess',help='verify all replays and score against frozen criteria')
    assess.add_argument('--protocol',type=Path,required=True)
    assess.add_argument('--replay',type=Path,action='append',required=True)
    assess.add_argument('--attestation-key',type=Path)
    assess.add_argument('--native-qualification',type=Path,help='native_gate.py qualification.json for the exact evaluated executable')
    assess.add_argument('--out',type=Path,required=True)
    ns=p.parse_args(argv)
    try:
        if ns.out.exists() or ns.out.is_symlink() or not ns.out.parent.is_dir():
            raise ValueError('output must have an existing parent and must not already exist')
        if ns.operation=='freeze':
            doc=make_protocol(load_object(ns.task_map),min_families=ns.min_families,
                              min_tasks=ns.min_tasks,min_new=ns.min_new,
                              min_effect=ns.min_effect,max_lost=ns.max_lost,alpha=ns.alpha,
                              min_positive_families=ns.min_positive_families,
                              min_family_size=ns.min_family_size)
        else:
            doc=evaluate(load_object(ns.protocol),ns.replay,attestation_key=ns.attestation_key,
                         native_qualification=ns.native_qualification)
        # O_EXCL avoids clobbering prior frozen criteria or reports.
        with ns.out.open('x',encoding='utf8') as f:
            f.write(json.dumps(doc,sort_keys=True,indent=2,allow_nan=False)+'\n')
        print(json.dumps({'written':str(ns.out),'status':doc.get('status','protocol_frozen'),
                          'tasks':doc.get('task_count',len(doc.get('tasks',{})))},sort_keys=True))
        return 0
    except (ValueError,OSError,KeyError,TypeError,IndexError,ZeroDivisionError) as exc:
        print(f'transfer campaign rejected: {exc}',file=sys.stderr)
        return 2

if __name__ == '__main__':
    raise SystemExit(main())
