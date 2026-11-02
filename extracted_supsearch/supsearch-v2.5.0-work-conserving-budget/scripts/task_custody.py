#!/usr/bin/env python3
"""Conservative split leakage detection for supsearch .tsk examples.

Checks are necessary, NOT sufficient, to establish task independence:
syntactic canonicalization cannot establish semantic equivalence for lambda terms.
The header is intentionally excluded; input/output example pairs are retained.
"""
from __future__ import annotations
from collections import defaultdict
import hashlib
import re
from pathlib import Path
from typing import Mapping


def canonical_examples(path: Path) -> tuple[str, ...]:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 2 * 1024 * 1024:
        raise ValueError(f'{path}: unsafe or oversized task (2 MiB limit)')
    text = path.read_text(encoding='utf8')
    if len(text.encode('utf8')) > 2 * 1024 * 1024:
        raise ValueError(f'{path}: task grew beyond 2 MiB')
    sections = text.split('\n---\n')
    if len(sections) != 2:
        raise ValueError(f'{path}: invalid task header delimiter')
    body = sections[1]
    lines = [re.sub(r'\s+', '', s) for s in body.splitlines() if s.strip()]
    examples = []
    for line in lines:
        if line.startswith('@main(') or re.fullmatch(r'(?:λ[A-Za-z_][A-Za-z_0-9]*\.)+@main\(.*\)', line):
            examples.append([line])
        elif line.startswith('=') and examples and len(examples[-1]) == 1:
            examples[-1].append(line)
        else:
            raise ValueError(f'{path}: malformed example sequence')
    if not examples or any(len(e) != 2 for e in examples):
        raise ValueError(f'{path}: no complete examples')
    return tuple(sorted(set(f'{e[0]}=>{e[1]}' for e in examples)))


def scan_splits(files: Mapping[str, Path], assignment: Mapping[str, str]) -> dict:
    """Returns descriptive signals; caller determines policy and custody labels."""
    examples = {tid: set(canonical_examples(path)) for tid, path in files.items()}
    leaks = []
    families = defaultdict(set)
    for tid, split in assignment.items():
        families[tid.split('_')[0]].add(split)
    for i, tid in enumerate(sorted(files)):
        for other in sorted(files)[i+1:]:
            if assignment[tid] == assignment[other]:
                continue
            intersection = examples[tid] & examples[other]
            if intersection:
                leaks.append({'left': tid, 'left_split': assignment[tid],
                              'right': other, 'right_split': assignment[other],
                              'shared_example_count': len(intersection),
                              'left_fraction': len(intersection)/len(examples[tid]),
                              'right_fraction': len(intersection)/len(examples[other]),
                              'identical_example_sets': examples[tid] == examples[other]})
    return {'cross_split_example_overlaps': leaks,
            'cross_split_id_families': sorted(k for k, v in families.items() if len(v)>1),
            'task_example_count': {k:len(v) for k,v in sorted(examples.items())},
            'task_examples_sha256': {
                k:hashlib.sha256('\n'.join(sorted(v)).encode()).hexdigest()
                for k,v in sorted(examples.items())}}


def assess_custody(scan: dict, *, fixture_mode: bool, require_family_disjoint: bool) -> str:
    overlap = scan['cross_split_example_overlaps']
    shared_families = scan['cross_split_id_families']
    if overlap and not fixture_mode:
        names = ', '.join(f"{e['left']}:{e['right']}" for e in overlap[:6])
        raise ValueError('cross-split example leakage (use --fixture-mode only for labeled demonstrations): '+names)
    if require_family_disjoint and shared_families and not fixture_mode:
        raise ValueError('cross-split task-family overlap: '+','.join(shared_families))
    if fixture_mode:
        return 'synthetic_fixture_not_holdout'
    if shared_families:
        return 'local_related_prefix_holdout_not_independent'
    return 'local_no_detected_prefix_overlap_not_independent'
