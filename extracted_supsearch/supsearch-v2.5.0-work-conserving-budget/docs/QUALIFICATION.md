> **Superseded for v0.4.0:** Consult `TRANSFER_QUALIFICATION_V04.md`. The v0.3 example below is known to leak equivalent input/output examples across splits, so the new normal `prepare` command rejects it unless `--fixture-mode` is supplied.

# Supsearch v0.3 local qualification protocol

This release **does not** prove autonomous general learning, independently measured speedups, or a secure sandbox. It provides a source-level Rust evaluation command and a tested, standard-library Python experiment-control runner. A real Rust build and real benchmarks remain necessary.

## Environment

- Stable Rust/Cargo toolchain (not included in the ZIP); no external Cargo dependencies.
- Python 3.9+ for the local research harness.
- Treat imported lambda expressions as resource-expensive inputs. Use OS process isolation if they are untrusted.

## Build and validation

```sh
cargo test
cargo build --release
python3 -m unittest discover -s tests -v
python3 scripts/check_manifest.py .
```

## One qualified experiment

Run these commands **from the extracted repository root**. The six Church multiplication tasks are synthetic, partly overlapping in their mathematical relationships, and not independent evidence. The candidate fixture is a known multiplication term, not a model-created discovery.

```sh
python3 scripts/qualified_pipeline.py prepare \
  --source examples/curriculum \
  --train prod_train2,prod_train3 \
  --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5 \
  --binary ./target/release/supsearch \
  --candidates examples/multiplication.candidates \
  --run out/qualified/demo-001 --rounds 2 --budget 0.5

python3 scripts/qualified_pipeline.py train --run out/qualified/demo-001
python3 scripts/qualified_pipeline.py evaluate --run out/qualified/demo-001
python3 scripts/qualified_pipeline.py verify --run out/qualified/demo-001
```

Remove `--candidates` to investigate spontaneous mining. Do not claim the known-candidate demonstration as autonomous discovery.

## Data custody

`prepare` reads and SHA-256-fingerprints task files and copies them into different directories:

- `learning_tasks/` contains training and development tasks, and is the only directory given to the native `learn` CLI.
- `sealed_test/` contains final-test tasks, and is used **only after training completes** by the native `evaluate` CLI.
- `inputs/initial.tsv` contains the starting library, `inputs/working.tsv` contains the learned library; the initial file is fingerprinted.
- `results/decisions.jsonl` contains Rust learning decisions.
- `results/concept_baseline.jsonl`, `concept_upgraded.jsonl`, and `raw_reference.jsonl` are native evaluation records.
- `state.json` records phase and input digests; `results/report.json` compares the matched concept-mode evaluations.

For final tests, the Python runner first uses O_EXCL to write `FINAL_EVALUATION_CONSUMED` and changes phase to `evaluation_consumed`. Any interrupted final evaluation requires a **new** run ID and preferably a fresh final task suite; there is no unattended retry. The same is true for training after a crash.

This controls the standard CLI path. Since the user owns the OS filesystem, no process isolation prevents a malicious modified learner from reading `sealed_test/`. Strong evaluator custody requires a separate OS account, machine, or third-party evaluator.

## Baselines: interpret correctly

Native `evaluate` supports two algorithms:

```sh
./target/release/supsearch evaluate examples/curriculum \
  --tasks prod_final4,prod_final5 --mode concept \
  --library out/qualified/demo-001/inputs/working.tsv \
  --out out/manual-final.jsonl --budget 0.5 --max-size 13 --fuel 20000
```

`concept_baseline` and `concept_upgraded` use the same concept-composition algorithm, same task list and same resource settings; only the concept library differs. This is the **paired concept-acquisition comparison**. If baseline concepts are empty, concept-mode performance may be zero by design; the raw solver is a separate useful reference. **Do not treat `raw_reference` versus `concept_upgraded` as a controlled sole-effect-of-learning measurement.**

The comparison report provides newly solved and lost tasks, and search-state reductions *only for jointly solved tasks*. It deliberately does not treat unsolved tasks as if they had zero computational cost. `built` is a proxy for search work, not a direct token/energy/time measure.

## Failure, leakage, and tamper boundaries

- Exact duplicate file bytes across task IDs are rejected at preparation. Equivalent semantics with different bytes are NOT detected.
- The qualified runner never passes final-test IDs or directories to the learning subprocess.
- Frozen source, candidate, initial library and executable hashes are checked before important transitions. These hashes are unsigned and mutable by whoever controls `state.json`.
- The previous Rust ledger remains an unsigned JSONL record. The Python auditor checks expected event order but cannot establish authenticity.
- If a native promotion crashes between intent and commit, the Rust learn CLI now refuses to continue when it detects a pending intent. There is no transactional rollback: an operator must reconcile the TSV and ledger before starting a new run.
- The Rust evaluator writes results atomically. Separate evaluation of raw versus concept modes is not assumed identical in search strategy or runtime behavior.
- A user can restart with another run ID and adapt to observed final-test results. Independent external custody must enforce no-reuse policies across runs.

## Objective release qualification

1. Compile and execute native Rust tests on a trusted, pinned Rust toolchain.
2. Reproduce v0.2 and v0.3 concept discovery with matching search budgets.
3. Compare untampered native concept-baseline and concept-upgraded results, including per-task solve rates, work and elapsed time.
4. Run negative tests for pathological lambda terms, memory growth, intentional process termination during promotion, hash tampering, malicious IDs and changed candidate inputs.
5. Repeat on a genuinely external, frozen task distribution with independent custody.
6. Only then assess learning-to-learn performance or claim generalization.
