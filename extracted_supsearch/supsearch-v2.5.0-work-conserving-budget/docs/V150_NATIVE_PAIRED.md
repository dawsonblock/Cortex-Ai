# v1.5 native paired evaluation: protocol and evidence boundary

## Why this version
The Rust engine has two algorithms, `bank::solve` (raw) and `bank::concept_solve`. Comparing those directly does not isolate the utility of learning a new concept. Instead run **`concept_solve` in both arms**, with only the library snapshot changed. The same budget, `--max-built`, fuel, task IDs, order, and native executable must be used.

## Run
On a Rust-equipped machine use the commands in the v1.5 README. The baseline library must be an actual frozen pre-learning snapshot, and the learned library the reconciled post-learning snapshot, not two generated substitute files. For smoke tests only, both can be the empty fixture.

The harness checks input file hashes before and after running the evaluator and stores both native JSONL outputs, an aggregate `report.json`, the executable digest and source-library digests under a fresh output directory. If the process crashes, the partial directory is quarantined: do not relabel it as complete. Output paths must not overlap input trees. Each JSONL record is schema-checked. New solutions and regressions are tracked individually, and paired search work is measured **only for jointly solved tasks**; never treat the absence of a baseline solution as free cost. The Python reference amortization script separately tracks **total** attempts (including failed solves).

## Limits
- Input digest != authenticated provenance; a controlled evaluator with independent custody is needed.
- A binary file header != verified source build; reproduce from pinned commits and toolchains.
- This harness does not make a candidate-library provenance claim or independently check a native learning journal. Use existing source-replay/gate tooling for that.
- One synthetic task or task family cannot establish transfer learning. Do not overinterpret paired scores.
- No native Cargo compilation was executed during package creation.

## Qualification sequence
1. `cargo test --locked`; build on macOS/Linux and reproduce SHA-256 of binary from source.
2. Run native learning without candidate imports, under a fixed state cap, on training and development problems only.
3. Reconcile the native ledger and learned concept library.
4. Freeze independent previously unseen tasks and compare concept-before and concept-after using this harness.
5. Report task and family-level accuracy, regression frequency, combined search cost, plus exploration/training cost and repeated campaigns.
6. Only if all checks pass, seek separately custodial external replication.
