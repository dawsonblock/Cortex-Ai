#!/usr/bin/env python3
"""Defensive local evidence checks for supsearch v0.5.

An unsigned, user-writable record cannot prove external custody, truth of an
LLM proposal, or equivalence of lambda expressions. These checks detect
common accidental or opportunistic inconsistencies within that record.
"""
from __future__ import annotations
from pathlib import Path
import json
import math
import re

MAX_JSONL_BYTES = 16 * 1024 * 1024
MAX_LIBRARY_BYTES = 2 * 1024 * 1024
VALID_NAME = re.compile(r'^[A-Za-z0-9_-]{1,96}$')


def _object_no_duplicates(pairs):
    out = {}
    for k, v in pairs:
        if k in out:
            raise ValueError(f'duplicate JSON key: {k}')
        out[k] = v
    return out


def _reject_constant(value):
    raise ValueError(f'non-finite JSON literal: {value}')


def strict_json_loads(data: str):
    return json.loads(data, object_pairs_hook=_object_no_duplicates,
                      parse_constant=_reject_constant)


def strict_jsonl(path: Path, *, max_bytes: int = MAX_JSONL_BYTES):
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'invalid evidence file: {path}')
    if path.stat().st_size > max_bytes:
        raise ValueError(f'evidence file exceeds {max_bytes} bytes: {path}')
    lines = path.read_text(encoding='utf8').splitlines()
    if any(not x.strip() for x in lines):
        raise ValueError(f'blank JSONL row: {path}')
    return [strict_json_loads(line) for line in lines]


def library_entries(path: Path):
    """Parse the persisted wire format; not a proof that terms are well-typed."""
    if path.is_symlink() or not path.is_file():
        raise ValueError(f'invalid library file: {path}')
    if path.stat().st_size > MAX_LIBRARY_BYTES:
        raise ValueError('library size limit exceeded')
    entries = []
    names, bodies = set(), set()
    for n, line in enumerate(path.read_text(encoding='utf8').splitlines(), 1):
        if not line or line.startswith('#'):
            continue
        columns = line.split('\t', 2)
        if len(columns) != 3:
            raise ValueError(f'{path}:{n}: malformed concept')
        name, arity, body = columns
        if not VALID_NAME.fullmatch(name) or not arity.isdecimal() or not 1 <= int(arity) <= 5:
            raise ValueError(f'{path}:{n}: malformed concept header')
        if not body or len(body) > 16384 or name in names or body in bodies:
            raise ValueError(f'{path}:{n}: duplicate or oversized concept')
        names.add(name)
        bodies.add(body)
        entries.append({'name': name, 'arity': int(arity), 'term': body})
        if len(entries) > 256:
            raise ValueError('more than 256 concepts')
    return entries


def reconcile_library(ledger: Path, initial: Path, learned: Path):
    """Require an append-only concept library matching the entire local intent log."""
    start = library_entries(initial)
    end = library_entries(learned)
    if end[:len(start)] != start:
        raise ValueError('trained library modified original concepts')
    new = end[len(start):]
    events = strict_jsonl(ledger)
    intents = {}
    commits = []
    started = 0
    for index, event in enumerate(events, 1):
        if not isinstance(event, dict) or not isinstance(event.get('event'), str):
            raise ValueError(f'ledger event {index}: invalid object')
        kind = event['event']
        if kind == 'start':
            started += 1
        if kind == 'promotion_intent':
            name = event.get('name')
            term = event.get('term')
            arity = event.get('arity')
            if not isinstance(name, str) or not isinstance(term, str) or type(arity) is not int:
                raise ValueError(f'ledger event {index}: invalid promotion intent')
            if name in intents:
                raise ValueError(f'ledger event {index}: duplicated intent')
            intents[name] = {'name': name, 'term': term, 'arity': arity}
        if kind == 'promotion_committed':
            name = event.get('name')
            if name not in intents or name in commits:
                raise ValueError(f'ledger event {index}: commit with no unique intent')
            if type(event.get('concept_count')) is not int or event['concept_count'] != len(start) + len(commits) + 1:
                raise ValueError(f'ledger event {index}: incorrect concept_count')
            commits.append(name)
    if started != 1 or len(intents) != len(commits) or len(new) != len(commits):
        raise ValueError('ledger/library promotion count mismatch')
    for i, name in enumerate(commits):
        if new[i] != intents[name]:
            raise ValueError(f'promoted concept {name}: ledger/library mismatch')
    return {'initial_concepts': len(start), 'promotions': len(commits),
            'final_concepts': len(end), 'append_only_reconciled': True}


def result_gate(pair: dict, *, task_count: int, custody_label: str,
                has_candidates: bool, promotions: int, min_tasks: int = 20):
    """Conservative advisory gate, never an external-validation certificate."""
    reasons = []
    if task_count < min_tasks:
        reasons.append('insufficient_final_tasks')
    if pair['regressions']:
        reasons.append('regressions_on_final_tasks')
    if pair['upgraded_solved'] <= pair['baseline_solved']:
        reasons.append('no_solve_rate_improvement')
    if not promotions:
        reasons.append('no_promoted_concepts')
    if has_candidates:
        reasons.append('externally_seeded_candidates')
    if custody_label == 'synthetic_fixture_not_holdout':
        reasons.append('synthetic_fixture_mode')
    if custody_label == 'local_related_prefix_holdout_not_independent':
        reasons.append('shared_task_prefix_families')
    return {'local_screen_passed': not reasons,
            'independent_validation': False,
            'claim': 'local_screen_only_never_independent_evidence',
            'minimum_final_tasks': min_tasks,
            'reasons': reasons}
