#!/usr/bin/env python3
"""Create explicitly labeled synthetic Church-product tasks.

These are demonstrations, NOT externally curated or independent holdouts.
No random train/test leakage; split IDs do not overlap.
"""
from pathlib import Path
import argparse


def church(n: int) -> str:
    if n < 0 or n > 4096:
        raise ValueError('Church numeral outside demonstration limits')
    expr = 'x'
    for _ in range(n):
        expr = f'f({expr})'
    return f'λf.λx.{expr}'


def task(arity: int, start: int) -> str:
    if not 2 <= arity <= 5:
        raise ValueError('arity must be 2..5')
    lines = [f'synthetic product of {arity} Church numerals; not an independent benchmark', '---']
    for j in range(5):
        values = [1 + (j + k + start) % 3 for k in range(arity)]
        product = 1
        for v in values:
            product *= v
        lines.extend([f'@main({", ".join(church(v) for v in values)})', f'= {church(product)}'])
    return '\n'.join(lines) + '\n'


def write_all(destination: Path) -> list[Path]:
    destination.mkdir(parents=True, exist_ok=True)
    definitions = [('prod_train2', 2, 0), ('prod_train3', 3, 1),
                   ('prod_dev3', 3, 2), ('prod_dev4', 4, 1),
                   ('prod_final4', 4, 2), ('prod_final5', 5, 0)]
    paths = []
    for name, arity, start in definitions:
        path = destination / (name + '.tsk')
        path.write_text(task(arity, start), encoding='utf8')
        paths.append(path)
    return paths


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', default='examples/curriculum')
    args = parser.parse_args()
    for filename in write_all(Path(args.out)):
        print(filename)
