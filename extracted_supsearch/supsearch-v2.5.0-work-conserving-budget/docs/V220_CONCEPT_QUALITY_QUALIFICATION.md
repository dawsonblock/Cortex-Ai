# Supsearch v2.2: training compression and development-family admission checks

## Goal and scope

This release adds two optional *secondary* admission criteria to the v2.1 Rust learning pipeline. Both are disabled by default. Neither is a proof of correctness, neural search-guidance training, equality saturation, independent transfer, or net real-world compute savings.

### 1. `--min-mdl-gain N` (default 0; disabled)

The `src/mdl.rs` module estimates the change in abstract syntax tree (AST) description length when a closed candidate appears as an exact subexpression of programs in the current **training** solution corpus. The calculation replaces each non-overlapping structurally identical occurrence by a one-node primitive and subtracts the full candidate definition size plus one bookkeeping node. Only `net_gain >= N` passes when enabled.

Examples: a repeated 4-node abstraction referenced 3 times saves `(4 - 1)*3 - (4 + 1) = 4` AST nodes by this proxy. A concept with no exact matches has negative gain. The proxy is deliberately simple: it does not include arithmetic representation cost, CPU time, interpreter cost, normalization cost, or semantic equivalence beyond exact syntax. It may underestimate useful higher-order abstractions that require beta normalization or renaming before matching. The verifier remains responsible for candidate behavior.

### 2. `--min-positive-families N` (default 0; disabled)

The pipeline groups *development* task IDs by the text before the first underscore. A family counts as positive if a candidate unlocks at least one task in that family or reduces the total candidate expansions across tasks jointly solved by the original and upgraded libraries within that family. The existing global regression checks still run.

This is a **development-set diversity heuristic**, not a measure of independent cross-domain transfer. Family names are user-supplied labels, not ontological similarity classes. To prevent trivial gaming, task-set ownership and family definitions must be controlled outside the learning process in any formal experiment.

### 3. Audit receipts

The existing schema-8 learning events now include the optional threshold values in `start`, and the measurements `mdl_gain` and `positive_families` in `candidate_trial` and `promotion_intent`. The v2.2 `concept_admission_audit_v220.py` composes the existing acquisition-work and reuse-forecast auditors, then checks that a promotion matches its trial and the thresholds frozen at session start. The auditor cannot recalculate the original training corpus from journal records alone.

## Running a local test

```bash
cargo test --locked --offline
cargo build --release --locked --offline
python3 -m unittest discover -s tests -p 'test_v220.py' -v
python3 scripts/native_gate.py --source . --out /tmp/supsearch-v220-native-gate
```

The native gate creates an isolated Cargo target, executes the real binary, audits native evaluation and native learning receipts, and checks the new concept-admission receipt. Passing this gate means **native smoke qualification**, not successful cross-family learning.

Optional experiment:

```bash
./target/release/supsearch learn bench \
  --train cnat_add,cnat_mul \
  --dev clst_hed,ntup_hed \
  --rounds 2 --budget 0.2 --max-size 5 --max-built 1500 \
  --curriculum-policy adaptive \
  --min-mdl-gain 1 --min-positive-families 2 \
  --library /tmp/supsearch-v220-concepts.tsv \
  --ledger /tmp/supsearch-v220-decisions.jsonl
python3 scripts/concept_admission_audit_v220.py /tmp/supsearch-v220-decisions.jsonl
```

This is an intentionally **strict illustrative command** and can produce zero promotions; it is not a promised learning demonstration. Ensure `/tmp` paths do not already contain prior runs. `--max-built` caps each solver call, but not the entire campaign, and wall time/resource costs are not fully accounted for.

## Qualification checklist

1. Run Cargo unit tests and release build in a pinned, isolated environment; preserve logs, executable SHA-256 and compiler version.
2. Run `scripts/native_gate.py` and require its exit code to be zero, with `v220_concept_admission_receipts_reconciled=true`.
3. Run native learn with the two gates enabled and disabled against preregistered training/dev tasks; compare both arms to the unmodified v2.1 engine under equal budgets.
4. Separately evaluate on unseen examples selected by another evaluator; record all candidate expansions, wall time, miner CPU costs, errors and lost solutions.
5. Do not claim transfer or amortization based on repeated development-set evaluations or self-reported journal consistency.

## External dependencies

The Rust crate remains dependency-free. Python testing uses the standard library. The optional neural policy, e-graphs, Stitch-like abstraction compression, and SMT/CEGIS integrations are NOT included in this release. Adding them before the native learning baseline is reproduced would make causal attribution harder, not easier.
