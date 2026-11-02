# v1.6.0 — End-to-end native mining and paired final evaluation

## Objective and claim boundary

`native_learning_campaign_v160.py` orchestrates a **real call to the provided executable's `learn` command**, audits the resulting transaction journal and concept library, then calls the same executable's `evaluate` command on withheld final tasks twice, with the same search algorithm and resource limits. It rejects imports by passing `--require-native-mined true`, and checks the promotion journal for `native_mining` origins. The binary must have a recognized native executable header except when an explicitly enabled **unqualified Python test double** is used.

It is not a proof of implementation identity, autonomous learning efficacy, independent evaluator custody, formal correctness, or broad transfer. Locally observed improvements are only internal results. Binary format is not proof that the executable was compiled from the submitted Rust source.

## Reproduction on an independently provisioned Rust machine

```bash
cargo test --locked
cargo build --release --locked
# Smoke data are from this repository, NOT independent or meaningful generalization.
mkdir -p /tmp/supsearch-v160-heldout
cp bench/ctre_rev.tsk /tmp/supsearch-v160-heldout/ctre_rev.tsk
python3 scripts/native_learning_campaign_v160.py \
  --binary ./target/release/supsearch \
  --learn-tasks ./bench --train cnat_add --dev cnat_mul \
  --final-tasks /tmp/supsearch-v160-heldout --final ctre_rev \
  --baseline-library examples/v150_empty.tsv \
  --out-dir /tmp/supsearch-v160-campaign \
  --rounds 1 --budget 0.05 --max-size 4 --max-built 1000 --fuel 1000
```

The output path must **not exist** when started. Never reuse a previous output directory. On partial failure, quarantine it; do not relabel incomplete artifacts as passing. To make a meaningful research claim, substitute separate externally controlled final tasks from unrelated computational task families, reproduce from pinned source/toolchain and report negative controls and multiple seeds.

## What the campaign enforces

1. A frozen baseline library and native executable identified by SHA-256 before and after learning and evaluation.
2. Disjoint train/dev/final IDs; train/development tasks and final tasks must live in **separate real directories**; final-task example bytes are not passed to `learn`.
3. Exact example-overlap detection using `task_custody`; binder-prefixed benchmark examples are recognized. Task-family IDs in the final split must not reuse training/development prefixes. These are necessary but insufficient leakage checks; semantic equivalents may remain.
4. Finite search time, fuel, program-size, state-expansion and round limits.
5. A fresh learned library created from a frozen initial library and a complete, strict JSONL promotion journal. Every accepted promotion must originate from `native_mining`. Imported candidates are forbidden by the native command.
6. Matched `concept` solver mode in baseline and upgraded final evaluation; the outputs are separately parsed and internally reconciled.
7. Reports **all** final search-state counts, including unsuccessful tasks, plus a **lower bound** for training expansions. Development baseline and candidate screening expenses, plus miner overhead, are **not fully available** in the existing Rust journal and cannot be accurately added to lifecycle cost.
8. Native and script-test-double runs are always distinguished in the report. A passing test double never establishes learning.

## Adversarial limitations

This is cooperative local evaluation, not a hostile-process sandbox. Native `learn` inherits ambient filesystem permissions and could read the final-task folder in principle, although the harness never supplies that path. For a true blinded holdout, run the learner in a separately isolated environment that cannot access final tasks, then permit a separately controlled evaluation process to replay the frozen final set. A malicious or compromised binary can falsify its own provenance records. Rebuild from source under independent custody and compare reproducible measurements.

A SHA-256 digest is an integrity checksum, not an authenticity attestation. A fixed final corpus reused for repeated model selection is no longer a valid final holdout. Do not treat internal curriculum-generated problems as external generalization evidence.

## Exit criteria

- Rust source compiles with `cargo test --locked` and optimized binary builds.
- Native `learn` attempts and optional promotions are present in an independently inspected journal.
- A nonempty promoted concept library can be reconciled with actual natively mined candidate lineage (otherwise report *no acquisition*).
- Baseline and upgraded comparisons on truly held-out tasks support a meaningful task-family-level performance improvement, with all successful and failed search work reported.
- Replication by a separate evaluator with fresh tasks and controlled computation reproduces the result. This condition is **not satisfied by this package's synthetic fixtures**.
