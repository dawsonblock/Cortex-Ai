#!/usr/bin/env python3
"""Validate the internal JSONL learning audit log's basic consistency.

This is not a signature, a proof of good evaluation, or tamper resistance.
"""
import argparse
import json
from pathlib import Path


def audit_events(lines):
    intents = {}
    committed = set()
    tests_started = False
    promotions = 0
    trials = 0
    dangling_all = []
    run = 0
    for index, line in enumerate(lines, 1):
        if not line.strip():
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f'line {index}: invalid JSON: {exc}') from exc
        if not isinstance(event, dict) or not isinstance(event.get('event'), str):
            raise ValueError(f'line {index}: missing event kind')
        kind = event['event']
        if kind == 'start':
            dangling_all.extend(f'run{run}:{name}' for name in (set(intents) - committed))
            run += 1
            intents = {}
            committed = set()
            tests_started = False
        elif kind == 'promotion_intent':
            if tests_started:
                raise ValueError(f'line {index}: promotion after final test')
            name = event.get('name')
            if not isinstance(name, str) or name in intents:
                raise ValueError(f'line {index}: missing/duplicate promotion intent')
            intents[name] = index
        elif kind == 'promotion_committed':
            if tests_started:
                raise ValueError(f'line {index}: commit after final test')
            name = event.get('name')
            if name not in intents or name in committed:
                raise ValueError(f'line {index}: commit without matching intent')
            committed.add(name)
            promotions += 1
        elif kind == 'candidate_trial':
            if tests_started:
                raise ValueError(f'line {index}: dev trial after final test')
            trials += 1
        elif kind == 'train_attempt' and tests_started:
            raise ValueError(f'line {index}: training after final test')
        elif kind == 'final_test':
            tests_started = True
    dangling_all.extend(f'run{run}:{name}' for name in (set(intents) - committed))
    return {'runs': run, 'candidate_trials': trials, 'promotions': promotions,
            'final_test_seen': tests_started, 'dangling_intents': sorted(dangling_all),
            'consistent': not dangling_all}


def main():
    p = argparse.ArgumentParser()
    p.add_argument('ledger', type=Path)
    args = p.parse_args()
    result = audit_events(args.ledger.read_text(encoding='utf8').splitlines())
    print(json.dumps(result, indent=2))
    if not result['consistent']:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
