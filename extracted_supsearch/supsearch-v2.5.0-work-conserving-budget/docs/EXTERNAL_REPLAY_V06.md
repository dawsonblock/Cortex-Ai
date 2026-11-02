# v0.6 evaluator-side replay protocol

This is a **source-level research release**, not a claim that autonomous
abstraction discovery succeeds. Its primary new tool is
`scripts/external_replay.py`. Use it on a **separate evaluator-owned machine or
account** where the learner cannot read test tasks or modify the evaluator's
registry. If all files remain on one user-writable computer, the evidence is
only a local replay. A file hash is *not* a trusted signature.

## Build / preconditions

```sh
python3 -m unittest discover -s tests -v
cargo test --locked
cargo build --release --locked
python3 scripts/check_manifest.py .
```

The Rust toolchain was unavailable in the packaging environment, so those
Cargo commands are requirements for a new installation, not completed results.
A nonnative mock executable is used in Python protocol tests, which establishes
orchestration behavior only.

## 1. Train and freeze WITHOUT evaluator-held task access

Create a local training/development run with the v0.5
`scripts/qualified_pipeline.py prepare` and `train` procedures. `prepare`
requires a local test split for legacy protocol compatibility, but the new
external evaluator **never opens that local final split**. Do not provide
external private tasks to `prepare`, the learner, or the candidate generator.

When possible, provide a task-family manifest managed by the evaluator, use
disjoint families, and avoid author-seeded candidates. Internally generated
candidate search is bounded and has not yet demonstrated transfer efficiency.

## 2. Evaluator privately replays frozen baseline and working concept libraries

Transfer the frozen, trained run, approved executable, and the trusted
preregistration to the evaluator. Keep evaluator-owned final tasks outside the
training run, and hold an access-controlled single-use registry separately.

```sh
python3 scripts/external_replay.py evaluate \
  --run /received/trained-run \
  --source /private/new-tasks \
  --tasks final_01,final_02 \
  --registry /evaluator-registry/claims \
  --out /evaluator-results/trial-001 \
  --budget 1 --max-size 13 --fuel 20000 \
  --counterbalanced
```

All four parent directories must exist. The registry and output directories
must not be inside the training run or source folder. A consumed marker is
written under the registry *before* native evaluation and is not cleared after
failure. Replays with the identical libraries, binary, task content, and
parameters are rejected within the **same trusted registry**.

Default evaluation performs baseline, upgraded, then raw-reference batches;
`--counterbalanced` alternates baseline/upgraded task order and runs the raw
reference third. The latter costs `3 × task_count` native process invocations
and can reduce simple ordering bias. Both modes compare concept-mode against
concept-mode; raw search is a separate reference, not a fair algorithm-matched
control. Outcomes should be evaluated against pre-registered thresholds,
including total search costs and any unsolved tasks.

No auto-promotion is performed. The evaluator cannot directly mutate the
learner's concept library.

## 3. Re-verify a replay without rerunning the private task set

```sh
python3 scripts/external_replay.py verify --out /evaluator-results/trial-001
```

This checks stored file digests, evaluation metadata, task coverage, library
counts, and recomputes paired metrics from saved native result rows. It does
not authenticate the underlying Rust executable. A party with write access to
**all** report and receipt files can replace them, so retain the receipt and
source approval hashes with the independent evaluator outside the learner's
storage domain.

## 4. Negative controls and limitations

- Cross-split identical examples, partial example reuse, and shared ID-prefix
  task families are rejected by default (unless explicitly marked as related
  or a synthetic fixture). Prefix screening is not semantic independence.
- A test is a finite set of input/output assertions, not a universal proof of
  lambda-term correctness.
- `--fixture-mode` is intentionally ineligible for a credible holdout claim.
- The package does not isolate native code from its host. Run only reviewed
  executables, preferably in a restricted VM or unprivileged container.
- The check does not detect leakage through prior model exposure, synthetic
  task-generator reuse, adversarial task renaming, multiple comparison runs
  against new keys, or coordinated modification of the report and receipt.
- No blind independent evaluation, signed provenance, native Rust compilation,
  or real synthesis gains have been reproduced in the packaging environment.
- The new external evaluator labels every result
  `evaluator_side_replay_not_automatically_independent` with
  `claimed_independent_validation=false`. Stronger claims require actual
  independent custody and reproduction.
