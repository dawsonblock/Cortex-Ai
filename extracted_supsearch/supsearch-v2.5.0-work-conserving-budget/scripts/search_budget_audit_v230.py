#!/usr/bin/env python3
"""Fail-closed local audit of the optional v2.3 concept/raw search portfolio.

Verifies arithmetic and declared search allocation from a schema-8 native
journal. This is self-reported evidence, NOT proof the native solver ran.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from evidence_integrity import strict_jsonl


def integer(value, name, upper=100_000_000):
    if type(value) is not int or not 0 <= value <= upper:
        raise ValueError('invalid nonnegative integer: ' + name)
    return value


def composed_cap(total, percentage):
    if total == 0 or percentage == 0:
        return total
    reserve = max(1, min(total - 1, (total * percentage + 99) // 100))
    return total - reserve


def audit(journal: Path) -> dict:
    if not journal.is_file() or journal.is_symlink():
        raise ValueError('missing or symlinked journal')
    # strict_jsonl handles duplicate keys and size bounds; guard newline separately.
    if not journal.read_bytes().endswith(b'\n'):
        raise ValueError('incomplete JSONL newline')
    rows = strict_jsonl(journal, max_bytes=8 * 1024 * 1024)
    if len(rows) < 3 or type(rows[0]) is not dict or rows[0].get('event') != 'start':
        raise ValueError('no native session start')
    if rows[-1].get('event') != 'session_completed':
        raise ValueError('no completed learning session')
    start = rows[0]
    if start.get('schema_version') != 8:
        raise ValueError('unsupported native journal schema')
    total = integer(start.get('max_built'), 'max_built')
    pct = integer(start.get('raw_reserve_pct'), 'raw_reserve_pct', 95)
    if pct and total < 2:
        raise ValueError('reserve requires bounded budget >=2')
    count = 0
    for row in rows[1:-1]:
        if type(row) is not dict:
            raise ValueError('malformed native journal record')
        if row.get('event') != 'train_attempt':
            continue
        count += 1
        cb = integer(row.get('composed_built'), 'composed_built')
        rb = integer(row.get('raw_built'), 'raw_built')
        built = integer(row.get('built'), 'built')
        cap = integer(row.get('composed_limit'), 'composed_limit')
        raw_limit = integer(row.get('raw_limit'), 'raw_limit')
        kind = row.get('kind')
        if kind not in ('composed', 'raw'):
            raise ValueError('invalid solver path')
        if built != cb + rb:
            raise ValueError('missing or forged expansion accounting')
        if kind == 'composed' and rb:
            raise ValueError('composed accepted but raw work charged')
        if total:
            if cap not in (0, composed_cap(total, pct)):
                raise ValueError('composed cap differs from configured reserve')
            if cb > cap or raw_limit != total - cb or rb > raw_limit or built > total:
                raise ValueError('shared search budget exceeded or inconsistent')
        elif cap or raw_limit:
            raise ValueError('unbounded sentinel must remain zero')
        elif kind == 'raw' and cb == 0 and cap != 0:
            raise ValueError('unbounded no-concept path inconsistent')
    if not count:
        raise ValueError('no native train attempts to audit')
    return {
        'schema':'supsearch-search-budget-v230',
        'train_attempts_checked':count,
        'configured_max_built':total,
        'configured_raw_reserve_pct':pct,
        'self_reported_allocation_consistent':True,
        'native_executed_independently':False,
        'validated_scope':'journal receipt arithmetic only',
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger', type=Path, required=True)
    ns = p.parse_args()
    try:
        print(json.dumps(audit(ns.ledger), sort_keys=True, indent=2))
    except (OSError, ValueError, UnicodeError) as e:
        p.exit(2, f'budget audit failed: {e}\n')


if __name__ == '__main__':
    main()
