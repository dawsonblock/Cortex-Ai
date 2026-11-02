# v1.3: bounded-work experiment protocol

## Why this version

Prior versions primarily used wall-clock time to stop native synthesis. Two
runs on different machines could explore different numbers of candidates even
when both were configured with the same `--budget` timeout. Comparisons of
`built` counts therefore needed an additional, explicit resource constraint.

v1.3 adds `--max-built N` to native `learn` and `evaluate`. A value of `0`
(default) preserves the earlier unbounded-by-state behavior. A positive value
in the range 1–100,000,000 caps candidate expansions in the raw bank and in
the concept-composition solver (including its ablation and diagnostic paths).
The existing wall-clock budget is retained as a separate protective limit.

The limit applies **per solver invocation**, not to an entire learning session.
Native learning may run multiple solver invocations per task and candidate.
The cap constrains candidate *counts*, not allocations, normalization steps,
wall-clock duration or energy cost. Equal caps are not proof of equal hardware
execution, equal complexity per candidate, or identical scheduling.

## Reproducible native checks (Rust toolchain required)

```bash
cargo test --locked --offline
cargo build --release --locked --offline
python3 scripts/native_gate.py --source . --out /tmp/supsearch-v130-native-gate
```

Choose a fresh gate output directory. The native gate will run the full Rust
unit suite, build a binary in an isolated target directory and check state
caps of one expansion in both raw and concept modes, followed by a bounded
learning smoke run and journal reconciliation.

## Native evaluation example

Make baseline and upgraded concept-library files available as separate files.
Keep the same tasks, solver mode, timeout, maximum term size, fuel and state
cap for each arm. These are illustrative commands, NOT benchmark results.

```bash
./target/release/supsearch evaluate bench \
  --tasks cnat_add,cnat_mul --mode concept --library /tmp/base.tsv \
  --out /tmp/baseline-v130.jsonl --budget 5 --max-size 8 --fuel 1000 --max-built 5000
./target/release/supsearch evaluate bench \
  --tasks cnat_add,cnat_mul --mode concept --library /tmp/learned.tsv \
  --out /tmp/learned-v130.jsonl --budget 5 --max-size 8 --fuel 1000 --max-built 5000
python3 scripts/state_budget_audit_v130.py \
  --baseline /tmp/baseline-v130.jsonl --learned /tmp/learned-v130.jsonl \
  --tasks cnat_add,cnat_mul --budget 5 --max-size 8 --fuel 1000 \
  --max-built 5000 --out /tmp/paired-v130.json
```

Only use tasks supplied and safeguarded by a separate evaluator for an
independent transfer claim. This example uses familiar benchmark tasks and is
**not** a valid independent transfer experiment. It is a local functional test.

The paired audit refuses mode mismatch, cap/settings mismatch, duplicate or
missing tasks, results that exceed the declared state cap and non-increasing
concept-library sizes. It also describes newly solved, lost and commonly solved
cases. A gain does not automatically qualify promotion or prove transfer.

## Compatibility and data migration

- `--max-built` defaults to zero: old commands remain valid.
- Native `evaluation_meta` and learning `start` records include `max_built`.
- The v0.x–v1.2 qualification pipeline treats records without that field as
  uncapped legacy results and rejects **nonzero** caps unless they were
  explicitly frozen in the evaluator's configuration.
- No previously frozen candidate promotion criteria are retroactively changed.
- Existing persisted concept libraries remain in the same TSV format.

## Evidence scope

Python protocol tests can verify parser checks and the internal consistency of
synthetic fixtures. They cannot compile Rust, authenticate an untrusted binary,
prove general-purpose intelligence or measure actual autonomous transfer. The
local journaling and local digest inventories are modifiable by a sufficiently
privileged operator. Separate custodian-controlled experiments remain necessary.
