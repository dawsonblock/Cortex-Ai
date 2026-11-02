#!/usr/bin/env python3
"""Explicit paired metrics for fixed holdout tasks; no independent-evidence claim.

Exact McNemar test conditions on discordant pairs. Does not correct for task-family
clustering, model selection, multiple comparisons or the reuse of a holdout.
"""
from __future__ import annotations
from math import comb, exp, log
from random import Random


def exact_mcnemar(new: int, lost: int) -> float:
    if not all(type(x) is int and x >= 0 for x in (new, lost)):
        raise ValueError('discordant counts must be nonnegative integers')
    n = new + lost
    if not n:
        return 1.0
    lower = min(new, lost)
    # Computing binomial tail using integer arithmetic avoids underflow for modest n.
    numerator = sum(comb(n, k) for k in range(lower+1))
    return min(1.0, (2*numerator) / (2**n))


def paired_bootstrap_success_ci(baseline: dict, improved: dict, *, reps: int = 2000, seed: int = 1405) -> list[float] | None:
    task_ids = sorted(set(baseline) & set(improved))
    if not task_ids:
        return None
    differences = [int(improved[t]['solved']) - int(baseline[t]['solved']) for t in task_ids]
    rng = Random(seed)
    n = len(differences)
    samples = sorted(sum(differences[rng.randrange(n)] for _ in range(n))/n for _ in range(reps))
    return [samples[int(0.025*(reps-1))], samples[int(0.975*(reps-1))]]


def paired_work_geometric_ratio(baseline: dict, improved: dict) -> float | None:
    jointly_solved = [t for t in baseline.keys() & improved.keys()
                      if baseline[t]['solved'] and improved[t]['solved']]
    if not jointly_solved:
        return None
    return exp(sum(log(max(1, improved[t]['built'])/max(1, baseline[t]['built']))
                   for t in jointly_solved)/len(jointly_solved))
