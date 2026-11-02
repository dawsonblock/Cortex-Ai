# v1.7: Measured learning-cost receipts

This release targets the first measurable cost defect in v1.6. `learn` previously charged *only the final raw solve* when concept composition failed, and did not journal any development-candidate trial cost. An apparent useful abstraction could therefore lose computational efficiency after its discovery cost was included.

## What is implemented

Native Rust instrumentation (requires separate Rust qualification):

- `train_attempt`: `built`, `composed_built`, `raw_built`. A failed concept composition followed by raw fallback charges both search attempts. Invalid composed solutions also trigger a raw fallback.
- `dev_baseline_work`: the sum of native candidate-expansion counts for every development task before testing candidates.
- `candidate_trial`: recorded `built` for that candidate/arity on every development task, including tasks not solved.
- `round_work`: one event per round summing all training, baseline-development and trial-development expansions.
- Journal schema version 8 records the expected number of learning rounds. Previous schema-6/7 journals continue to be accepted by existing history validators. The new cost auditor **requires schema 8**.

The bounded auditor rejects: duplicate keys, truncated receipts, out-of-order events, missing attempts, inconsistent work totals, fake fallback sums, wrong development counts, missing/duplicate round summaries, incorrect resource-bound counts, and incomplete sessions. It does *not* accept a record merely because the outer summary looks plausible.

The per-`round` and cumulative totals are **lower bounds** on total learning cost, because candidate mining, evaluator wall-clock, normalization, and other computations are not metered in candidate expansions. The lower bound also assumes all self-reported native records are truthful; local JSON records are not hardware attestation.

## Reproduce protocol tests (Python)

```sh
python3 -m unittest discover -s tests -p 'test_v170.py' -v
python3 scripts/learning_work_audit_v170.py --help
```

## Native source qualification (unperformed in packaged environment)

```sh
cargo test --locked
cargo build --release --locked
# Use independently supplied, disjoint task directories (v1.6 runbook)
python3 scripts/native_learning_campaign_v170.py \
  --binary ./target/release/supsearch \
  --learn-tasks /path/to/training-and-dev \
  --final-tasks /path/to/external-final \
  --train TRAIN_TASK_IDS --dev DEV_TASK_IDS --final FINAL_TASK_IDS \
  --baseline-library ./examples/v150_empty.tsv \
  --out-dir /tmp/supsearch-v170-new-run \
  --rounds 2 --max-built 30000
```

The v1.7 runner delegates task custody, journal preflight, native origin checks, and final matched evaluation to the v1.6 runner before it performs the mandatory work-receipt audit. It writes `report-v170.json` only if the journal reconciles.

A final-task gain does **not** establish profitability in search cost. The report gives an *upper bound* on net savings and the *lower bound* on repeats needed to recoup even the measured development/learning search expansions, not an observed net profit or demonstrated amortization. Measured counts are candidate expansions, not money, GPU usage, or time.

## Qualification blockers

1. Compile and execute Rust source on a pinned independent toolchain.
2. Repeat native discovery runs and verify at least one concept is natively mined and transferred.
3. Audit whether a held-out task-family workload recoups learning costs, including external evaluation and mining overhead.
4. Independently control the final task holdout, test source-to-binary provenance, and run on a second host.

The Python reference learner's synthetic tasks and the included mock-native tests cannot satisfy these steps.
