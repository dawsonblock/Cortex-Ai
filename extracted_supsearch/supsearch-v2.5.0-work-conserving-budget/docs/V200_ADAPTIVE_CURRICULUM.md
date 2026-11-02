# Supsearch v2.0.0 — Adaptive curriculum, budget accounting and qualification

## Objective

An **optional** deterministic, training-feedback-only curriculum policy now
prioritizes later task attempts based on observed per-family progress and
uncertainty. It is not reinforcement-learning neural weight training, and it
is not evidence of transfer or improved intelligence. The historical heuristic
is still the default and must be the control condition.

The score uses smoothed family-average bounded rewards, a UCB-like exploration
bonus, previously unattempted-task preference, unsuccessful-task frontier,
measured search work and retry penalty. A reward is **1** the first time a
training task succeeds, or the fractional search reduction (clamped to [0,1])
for repeated successful tasks. Unsuccessful and regressing attempts receive
**0**, rather than being punished with negative rewards. It has no access to
final-test outcomes. A maximum of two selected tasks per ID-prefix family
keeps one family from consuming a full round.

To evaluate honestly, compare the `heuristic` and `adaptive` policies on
fresh copies of the same original concept library and tasks with fixed solver
limits. Both should run a separate final evaluation performed by an external
evaluator using untouched tasks. The policy choice is precommitted and cannot
be changed within a run.

## Native Rust source changes

- `src/curriculum.rs`: deterministic training-feedback curriculum policy and
  five Rust unit tests.
- `src/learning.rs`: `--curriculum-policy heuristic|adaptive` (default heuristic),
  curriculum_selection ledger events, training-feedback updates, plus a single
  cumulative `--max-built` count across concept-first and raw fallback search.
- `src/journal.rs`: permits internally audited selection events in learning phase;
  it does not cryptographically attest the selection policy.
- `scripts/curriculum_audit_v200.py`: validates one selection per round,
  task allowlist, order of training attempts, bounded family selection, JSON
  duplicate-key rejection, and explicit session closure. It cannot prove that
  the actual model used the claimed algorithm or that reported work is true.
- `tests/test_v200.py`: 12 adversarial/positive Python auditor tests.

## Commands

First qualify the unchanged/native executable:

```bash
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -p 'test_v200.py' -v
```

A minimal local **non-independent** learning smoke run:

```bash
./target/release/supsearch learn bench \
  --train cnat_add --dev cnat_mul \
  --curriculum-policy adaptive --require-native-mined true \
  --rounds 2 --budget 0.05 --max-size 4 \
  --max-built 1000 --fuel 1000 \
  --library /tmp/supsearch-v200/concepts.tsv \
  --ledger /tmp/supsearch-v200/events.jsonl
python3 scripts/curriculum_audit_v200.py \
  --ledger /tmp/supsearch-v200/events.jsonl \
  --train cnat_add
```

`--expected-reuses N` still controls the separate optional v1.9 economic
admission gate; this release does **not** replace it with the curriculum score.
Do not rerun a session into an unfinished or untrusted prior journal.

## Verification requirements

1. Execute native tests and build on Linux and macOS.
2. Verify a full native learning cycle (mined, verified, promoted, reused).
3. Run counterbalanced, fresh-start experiments comparing heuristic and
   adaptive with identical budgets and independent external final tasks.
4. Include **all** search effort: training, candidate trials, dev, final, and
   failed attempts. Record wall time, peak memory and CPU time separately.
5. Repeat across seeds and task families. Preregister thresholds and preserve
   the sealed final set; avoid repeated selection on the same holdout.
6. Reject a release-grade claim if native compile/test, receipt integrity, or
   independent transfer criteria are missing.

This source release contains no independent native transfer measurements.
