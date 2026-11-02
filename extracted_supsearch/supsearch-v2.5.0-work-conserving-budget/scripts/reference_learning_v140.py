#!/usr/bin/env python3
"""Executable, dependency-free reference abstraction learner for Supsearch v1.4.

This is a separate Python reference experiment, NOT the native Rust engine.
It learns unary definitional abbreviations from synthesis solutions and checks
whether those abbreviations improve same-algorithm held-out program search.
All example tasks and the task design are bundled; the test is NOT independent.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class Expr:
    op: str
    args: tuple['Expr', ...] = ()
    var: int = -1

    def format(self) -> str:
        if self.op == 'var':
            return f'v{self.var}'
        if self.op == 'add':
            return f'(+ {self.args[0].format()} {self.args[1].format()})'
        if self.op == 'learned':
            return f'(C0 {self.args[0].format()})'
        raise ValueError('unsupported operator')

    def size(self) -> int:
        return 1 + sum(child.size() for child in self.args)


def var(n: int) -> Expr:
    return Expr('var', var=n)


def add(left: Expr, right: Expr) -> Expr:
    if left.format() > right.format():
        left, right = right, left
    return Expr('add', (left, right))


def evaluate(expr: Expr, inputs: tuple[int, ...], learned: Expr | None = None) -> int:
    if expr.op == 'var':
        return inputs[expr.var]
    if expr.op == 'add':
        return evaluate(expr.args[0], inputs, learned) + evaluate(expr.args[1], inputs, learned)
    if expr.op == 'learned' and learned is not None:
        # All candidate concepts are unary templates over the single v0 binder.
        value = evaluate(expr.args[0], inputs, learned)
        return evaluate(learned, (value,), None)
    raise ValueError('invalid expression or unbound concept')


@dataclass(frozen=True)
class Task:
    id: str
    family: str
    arity: int
    examples: tuple[tuple[tuple[int, ...], int], ...]

    @classmethod
    def make(cls, id: str, family: str, arity: int,
             function: Callable[..., int], inputs: tuple[tuple[int, ...], ...]) -> 'Task':
        if not inputs or any(len(x) != arity for x in inputs):
            raise ValueError('invalid task examples')
        return cls(id, family, arity, tuple((x, function(*x)) for x in inputs))


def example_leakage(splits: dict[str, tuple[Task, ...]]) -> None:
    """Reject exact arity/input/output duplicates between any two splits."""
    seen: dict[tuple[int, tuple[int, ...], int], str] = {}
    for split, tasks in splits.items():
        for task in tasks:
            for arguments, output in task.examples:
                key = (task.arity, arguments, output)
                if key in seen and seen[key] != split:
                    raise ValueError(f'cross-split exact example reuse: {seen[key]} and {split}')
                seen[key] = split


@dataclass(frozen=True)
class Solve:
    solved: bool
    built: int
    retained: int
    expression: Expr | None


def synthesize(task: Task, *, concept: Expr | None, max_size: int,
               max_built: int) -> Solve:
    """Bottom-up enumerator with per-task observational deduplication.

    Same enumeration order and work cap are used in baseline and upgrade.
    `built` counts generated candidates, including semantically redundant ones.
    """
    if max_size < 1 or max_built < 1:
        raise ValueError('positive search bounds are required')
    expected = tuple(y for _, y in task.examples)
    # A candidate may be retained once per distinct observed behavior, even
    # when represented with a structurally different expression.
    seen: set[tuple[int, ...]] = set()
    levels: dict[int, list[Expr]] = {}
    built = 0
    for size in range(1, max_size + 1):
        candidates: list[Expr] = []
        if size == 1:
            candidates = [var(i) for i in range(task.arity)]
        else:
            if concept is not None:
                candidates.extend(Expr('learned', (e,)) for e in levels.get(size - 1, ()))
            for left_size in range(1, size - 1):
                right_size = size - 1 - left_size
                for left in levels.get(left_size, ()):
                    for right in levels.get(right_size, ()):
                        if left.format() <= right.format():
                            candidates.append(add(left, right))
        retained: list[Expr] = []
        for expr in candidates:
            built += 1
            if built > max_built:
                return Solve(False, max_built, len(seen), None)
            signature = tuple(evaluate(expr, values, concept) for values, _ in task.examples)
            if signature in seen:
                continue
            seen.add(signature)
            retained.append(expr)
            if signature == expected:
                return Solve(True, built, len(seen), expr)
        levels[size] = retained
    return Solve(False, built, len(seen), None)


def normalize_unary_template(expr: Expr) -> Expr | None:
    """Convert `add(vK,vK)` into `add(v0,v0)` for a reusable unary concept.

    Only accepts templates with precisely one variable, occurring twice.
    It does not accept arbitrary syntax or invent a multiplication primitive.
    """
    if expr.op != 'add' or len(expr.args) != 2:
        return None
    left, right = expr.args
    if left.op != 'var' or right.op != 'var' or left.var != right.var:
        return None
    return add(var(0), var(0))


def mine_from_training(tasks: tuple[Task, ...], solved: dict[str, Solve]) -> tuple[Expr | None, dict]:
    occurrences: dict[str, set[str]] = {}
    templates: dict[str, Expr] = {}
    for task in tasks:
        expression = solved[task.id].expression
        if expression is None:
            continue
        stack = [expression]
        while stack:
            node = stack.pop()
            template = normalize_unary_template(node)
            if template is not None:
                key = template.format()
                templates[key] = template
                occurrences.setdefault(key, set()).add(task.id)
            stack.extend(node.args)
    eligible = [(len(ids), key) for key, ids in occurrences.items() if len(ids) >= 2]
    eligible.sort(key=lambda x: (-x[0], x[1]))
    if not eligible:
        return None, {'method': 'repeated_solved_subexpression', 'candidate_count': 0}
    _, key = eligible[0]
    return templates[key], {'method': 'repeated_solved_subexpression',
                           'candidate_count': len(eligible),
                           'chosen_source_tasks': sorted(occurrences[key]),
                           'definition': key}


def checks_template_definition(concept: Expr) -> bool:
    # This is a finite sanity check; definition expansion is what gives the
    # concept its semantics. It is not a proof of task correctness.
    return all(evaluate(concept, (x,)) == x + x for x in range(-12, 13))


def quantify(before: dict[str, Solve], after: dict[str, Solve]) -> dict:
    new = sorted(k for k in before if not before[k].solved and after[k].solved)
    lost = sorted(k for k in before if before[k].solved and not after[k].solved)
    shared = sorted(k for k in before if before[k].solved and after[k].solved)
    b = sum(before[k].built for k in shared)
    a = sum(after[k].built for k in shared)
    gain = (b - a) / b if b else 0.0
    slow = [k for k in shared if after[k].built > before[k].built * 1.2 + 2]
    return {'before_solved': sum(x.solved for x in before.values()),
            'after_solved': sum(x.solved for x in after.values()),
            'new_solved': new, 'lost_solved': lost,
            'severe_search_regressions': slow,
            'paired_shared_search_work_before': b,
            'paired_shared_search_work_after': a,
            'paired_shared_work_reduction': round(gain, 6)}


def fixture() -> dict[str, tuple[Task, ...]]:
    # The target functions in these synthetic fixtures are deliberately known
    # to the test author. The synthesize() solver only sees input/output pairs.
    train_x = tuple((x,) for x in (-9, -6, -3, -1, 1, 3, 7, 10))
    train_xy = tuple((a, b) for a, b in zip(range(1, 9), range(11, 19)))
    dev_xy = tuple((a, b) for a, b in ((-13, 4), (10, 3), (6, -7), (-4, -5), (1, 13), (8, 1)))
    final_xyz = tuple((a, b, c) for a, b, c in ((-8, 4, -2), (11, -3, 2),
        (7, 12, 1), (-6, -7, -3), (13, 2, -9), (2, -11, 10)))
    return {
        'training': (
            Task.make('train_double_x', 'double', 1, lambda x: 2*x, train_x),
            Task.make('train_double_y', 'double', 2, lambda x, y: 2*y, train_xy),
        ),
        'development': (
            Task.make('dev_left_offset', 'offset', 2, lambda x, y: 4*x+y, dev_xy),
            Task.make('dev_right_offset', 'offset', 2, lambda x, y: x+4*y, dev_xy),
        ),
        'final': (
            Task.make('final_three_sum', 'weighted_sum', 3, lambda x, y, z: 4*x+y+z, final_xyz),
            Task.make('final_three_sum_rotated', 'weighted_sum', 3, lambda x, y, z: x+4*y+z, final_xyz),
        ),
    }


def serialize(s: Solve) -> dict:
    return {'solved': s.solved, 'built': s.built, 'retained': s.retained,
            'solution': s.expression.format() if s.expression else None}


def canonical(value: dict) -> bytes:
    return (json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)+'\n').encode('utf-8')


def experiment(*, max_size: int = 9, max_built: int = 30000,
               require_gain: float = 0.05) -> dict:
    if not 3 <= max_size <= 10 or not 20 <= max_built <= 100000 or not 0 <= require_gain <= 1:
        raise ValueError('invalid experiment limits')
    splits = fixture()
    example_leakage(splits)
    training = {t.id: synthesize(t, concept=None, max_size=max_size, max_built=max_built)
                for t in splits['training']}
    discovered, discovery = mine_from_training(splits['training'], training)
    valid = discovered is not None and checks_template_definition(discovered)
    dev_before = {t.id: synthesize(t, concept=None, max_size=max_size, max_built=max_built)
                  for t in splits['development']}
    dev_after = {t.id: synthesize(t, concept=discovered if valid else None,
                  max_size=max_size, max_built=max_built) for t in splits['development']}
    dev_metrics = quantify(dev_before, dev_after)
    # Deliberately unhelpful concept: identity(a)=a. This demonstrates that
    # adding an arbitrary new search operator is NOT accepted by default.
    null_concept = var(0)
    null_after = {t.id: synthesize(t, concept=null_concept, max_size=max_size,
                  max_built=max_built) for t in splits['development']}
    null_metrics = quantify(dev_before, null_after)
    null_accepted = bool(not null_metrics['lost_solved'] and
                         not null_metrics['severe_search_regressions'] and
                         (len(null_metrics['new_solved']) > 0 or
                          null_metrics['paired_shared_work_reduction'] >= require_gain))
    accepted = bool(valid and not dev_metrics['lost_solved'] and
                    not dev_metrics['severe_search_regressions'] and
                    (len(dev_metrics['new_solved']) > 0 or
                     dev_metrics['paired_shared_work_reduction'] >= require_gain))
    accepted_concept = discovered if accepted else None
    # Final split remains unused until acceptance decisions are frozen.
    final_before = {t.id: synthesize(t, concept=None, max_size=max_size, max_built=max_built)
                    for t in splits['final']}
    final_after = {t.id: synthesize(t, concept=accepted_concept,
                   max_size=max_size, max_built=max_built) for t in splits['final']}
    final_metrics = quantify(final_before, final_after)
    record = {'schema_version': 1, 'experiment': 'supsearch-python-reference-v140',
              'qualification_scope': 'bundled synthetic reference experiment ONLY',
              'native_rust_executed': False, 'independent_external_holdout': False,
              'outcome_is_general_intelligence_evidence': False,
              'max_size': max_size, 'max_built_per_solve': max_built,
              'min_dev_work_reduction': require_gain,
              'discovery': {**discovery, 'training_all_solved': all(x.solved for x in training.values()),
                            'template_definition_checked': valid},
              'negative_control': {'definition': null_concept.format(), 'metrics': null_metrics, 'accepted': null_accepted},
              'promotion': {'accepted': accepted,
                            'concept': discovered.format() if accepted and discovered else None},
              'training': {key: serialize(value) for key, value in sorted(training.items())},
              'development': {'before': {k: serialize(v) for k,v in sorted(dev_before.items())},
                              'after': {k: serialize(v) for k,v in sorted(dev_after.items())},
                              'metrics': dev_metrics},
              'final': {'before': {k: serialize(v) for k,v in sorted(final_before.items())},
                        'after': {k: serialize(v) for k,v in sorted(final_after.items())},
                        'metrics': final_metrics}}
    return record


def seal(record: dict) -> dict:
    return {'result': record, 'sha256': hashlib.sha256(canonical(record)).hexdigest()}


def verify_envelope(envelope: dict) -> bool:
    if not isinstance(envelope, dict) or set(envelope) != {'result', 'sha256'}:
        return False
    if not isinstance(envelope['result'], dict) or not isinstance(envelope['sha256'], str):
        return False
    return hashlib.sha256(canonical(envelope['result'])).hexdigest() == envelope['sha256']


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, help='fresh output report JSON (never overwrite)')
    parser.add_argument('--audit', type=Path, help='check saved hash and replay reference experiment')
    parser.add_argument('--max-size', type=int, default=9)
    parser.add_argument('--max-built', type=int, default=30000)
    parser.add_argument('--min-gain', type=float, default=0.05)
    ns = parser.parse_args(argv)
    if ns.audit is not None:
        if ns.out is not None:
            parser.error('--audit and --out are mutually exclusive')
        def no_duplicate_object_keys(pairs):
            d = {}
            for key, value in pairs:
                if key in d:
                    raise ValueError(f'duplicate JSON key: {key}')
                d[key] = value
            return d
        try:
            obj = json.loads(ns.audit.read_text(encoding='utf-8'),
                             object_pairs_hook=no_duplicate_object_keys,
                             parse_constant=lambda s: (_ for _ in ()).throw(ValueError(f'nonfinite JSON: {s}')))
        except (OSError, ValueError) as exc:
            parser.error(f'malformed audit file: {exc}')
        if not verify_envelope(obj):
            parser.error('report digest mismatch or malformed envelope')
        record = obj['result']
        replay = experiment(max_size=record['max_size'], max_built=record['max_built_per_solve'],
                            require_gain=record['min_dev_work_reduction'])
        if replay != record:
            parser.error('report does not match fresh deterministic replay')
        print('REPLAY VERIFIED (bundled synthetic reference; not native Rust or external holdout)')
        return 0
    report = experiment(max_size=ns.max_size, max_built=ns.max_built, require_gain=ns.min_gain)
    envelope = seal(report)
    data = json.dumps(envelope, indent=2, sort_keys=True)+'\n'
    if ns.out:
        # x flag ensures every real experiment is written to a fresh evidence path.
        with ns.out.open('x', encoding='utf-8') as f:
            f.write(data)
    else:
        print(data)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
