#!/usr/bin/env python3
"""Create evaluator-owned fixed SHA-256 task/family map for transfer_campaign.

Family assignments are supplied by the custodian as JSON {task_id:family};
never infer family independence from a filename prefix. This utility reads
private tasks solely to calculate exact hashes and syntactic overlap. It does
not certify unseen-family semantics or prove a withheld task is truly unseen.
"""
from pathlib import Path
import argparse
import json
import sys
from transfer_campaign import load_object, validate_task_map, TASK_ID, FAMILY_ID
from qualified_pipeline import checked_regular, digest
from task_custody import canonical_examples


def build(source: Path, assignments: dict) -> dict:
    if not source.is_dir() or source.is_symlink():
        raise ValueError('source must be a normal task directory')
    if not isinstance(assignments, dict) or not 1 <= len(assignments) <= 1000:
        raise ValueError('family mapping must contain 1..1000 tasks')
    descriptions = {}
    seen = {}
    for tid, family in sorted(assignments.items()):
        if not isinstance(tid,str) or not TASK_ID.fullmatch(tid) or not isinstance(family,str) or not FAMILY_ID.fullmatch(family):
            raise ValueError('unsafe task ID or family label')
        path=checked_regular(source / f'{tid}.tsk')
        for ex in canonical_examples(path):
            if ex in seen:
                raise ValueError(f'cross-task example reuse: {seen[ex]} vs {tid}')
            seen[ex]=tid
        descriptions[tid]={'family':family,'sha256':digest(path)}
    return validate_task_map(descriptions)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--source',required=True,type=Path)
    p.add_argument('--families',required=True,type=Path,help='evaluator-curated {task_id: family} JSON')
    p.add_argument('--out',required=True,type=Path)
    ns=p.parse_args(argv)
    try:
        if ns.out.exists() or ns.out.is_symlink() or not ns.out.parent.is_dir():
            raise ValueError('output already exists or parent directory missing')
        data=build(ns.source,load_object(ns.families))
        with ns.out.open('x',encoding='utf8') as f:
            f.write(json.dumps(data,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'task_map_created':str(ns.out),'tasks':len(data)},sort_keys=True))
        return 0
    except (OSError,ValueError,TypeError,KeyError) as exc:
        print(f'cannot create task map: {exc}',file=sys.stderr)
        return 2
if __name__=='__main__': raise SystemExit(main())
