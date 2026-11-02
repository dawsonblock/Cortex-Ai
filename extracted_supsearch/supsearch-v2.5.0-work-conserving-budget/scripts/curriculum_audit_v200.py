"""Fail-closed, read-only curriculum-ledger check for Supsearch v2.0.

Checks *internal consistency* of selections vs actual train_attempt events.
It cannot certify the executable, task custody, transfer, or external validity.
"""
import argparse
import json
from pathlib import Path

MAX_BYTES=8*1024*1024

def _strict_pairs(pairs):
    out={}
    for k,v in pairs:
        if k in out: raise ValueError(f"duplicate JSON key: {k}")
        out[k]=v
    return out

def audit(path:Path, train_ids:set[str]) -> dict:
    if not train_ids: raise ValueError("empty training task allowlist")
    if not all(isinstance(t,str) and t and t.replace('_','').replace('-','').isalnum() for t in train_ids):
        raise ValueError("invalid training task ID")
    if path.is_symlink() or not path.is_file() or path.stat().st_size>MAX_BYTES:
        raise ValueError("unsafe or oversized journal")
    data=path.read_bytes()
    if not data or not data.endswith(b'\n'): raise ValueError("missing final newline or empty journal")
    if len(data)>MAX_BYTES: raise ValueError("journal exceeds bound")
    rows=[]
    for line in data.decode('utf-8').splitlines():
        if not line or len(line)>16384: raise ValueError("empty or oversized journal record")
        row=json.loads(line,object_pairs_hook=_strict_pairs,
                       parse_constant=lambda s: (_ for _ in ()).throw(ValueError('nonfinite JSON')))
        if not isinstance(row,dict) or not isinstance(row.get('event'),str):
            raise ValueError("journal row must be JSON object with event")
        rows.append(row)
    starts=[x for x in rows if x['event']=='start']
    if not starts: raise ValueError('no start event')
    rounds=[]
    in_session=False
    frozen_mode=None
    plan={}
    attempts={}
    for row in rows:
        event=row['event']
        if event=='start':
            if in_session: raise ValueError('nested start')
            in_session=True
            plan={}; attempts={}
            frozen_mode=row.get('curriculum_policy')
            if frozen_mode not in ('heuristic','adaptive'): raise ValueError('missing/invalid curriculum policy')
            if type(row.get('train')) is not int or row['train']!=len(train_ids):
                raise ValueError('train count inconsistent with allowlist')
        elif event=='curriculum_selection':
            if not in_session: raise ValueError('selection outside session')
            rn=row.get('round')
            if type(rn) is not int or rn<0 or rn in plan: raise ValueError('duplicate/invalid selection round')
            if row.get('policy')!=frozen_mode: raise ValueError('selection changed policy')
            names=row.get('tasks')
            if not isinstance(names,str): raise ValueError('invalid task names')
            names=names.split(',') if names else []
            if not names or len(names)!=len(set(names)) or set(names)-train_ids:
                raise ValueError('duplicate/unknown/empty selection')
            families={}
            for name in names:
                fam=name.split('_',1)[0]
                families[fam]=families.get(fam,0)+1
                if families[fam]>2: raise ValueError('too many tasks from same family')
            plan[rn]=names
            attempts[rn]=[]
        elif event=='train_attempt':
            if not in_session: raise ValueError('training outside session')
            rn=row.get('round'); task=row.get('task')
            if type(rn) is not int or rn not in plan or task not in train_ids:
                raise ValueError('unexpected training attempt')
            if len(attempts[rn])>=len(plan[rn]) or task!=plan[rn][len(attempts[rn])]:
                raise ValueError('training attempts do not match selection order')
            attempts[rn].append(task)
            built=row.get('built')
            if type(built) is not int or built<0: raise ValueError('invalid built count')
        elif event=='session_completed':
            if not in_session: raise ValueError('orphan session completion')
            if type(row.get('rounds')) is not int or set(plan)!=set(range(row['rounds'])):
                raise ValueError('round count or selection sequence inconsistent')
            for rn, names in plan.items():
                if attempts[rn]!=names: raise ValueError('missing task attempts for round')
            rounds.append({'policy':frozen_mode,'rounds':len(plan),'attempts':sum(map(len,attempts.values()))})
            in_session=False
    if in_session: raise ValueError('incomplete session')
    if not rounds: raise ValueError('no completed session')
    return {'qualified_as':'internal_ledger_consistency_only','sessions':rounds}

def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--ledger',required=True,type=Path)
    ap.add_argument('--train',required=True,help='Comma-separated training IDs')
    args=ap.parse_args()
    print(json.dumps(audit(args.ledger,set(args.train.split(','))),indent=2))

if __name__=='__main__':main()
