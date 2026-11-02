# Supsearch v0.8 — Preregistered transfer campaigns

**Scope:** A researcher-oriented, conservative assessment of externally replayed concept-learning results. It is **not** an engine that autonomously learns new concepts, a replacement for source review, nor proof of independent scientific validation.

## Changes from v0.7

- New `scripts/create_task_map.py` builds task identities from the evaluator's curated `task_id -> family` assignments, actual private `.tsk` bytes, and hashes. It rejects unsafe names, duplicate file content and syntactically reused example pairs.
- New `scripts/transfer_campaign.py freeze` produces a fixed, checkable preregistration file containing task-family map, private task SHA-256, and scoring thresholds. It refuses overwriting existing protocol files. Its digest alone cannot establish the protocol was frozen *before* tests: custody/timestamps must be established externally.
- `transfer_campaign.py assess` re-verifies the external replay artifacts; requires all preregistered tasks be present exactly once; rejects mock scripts, synthetic evaluations, repeated trials, changed digests, changed learning lineage and reused test examples; and evaluates paired solved-rate improvements with **family-cluster percentile bootstrap** plus exact McNemar test. Note McNemar does not itself adjust for family clustering.
- A passing **local** campaign now also requires the native qualification receipt from `native_gate.py` matching the replay binary's SHA-256, native-mined (not candidate-seeded) concepts, at least one promotion, counterbalanced native evaluation, minimum task and family counts and no unacceptable regressions. This receipt remains unauthenticated unless a trusted evaluator externally authenticates it.
- `native_gate.py` uses `CARGO_TARGET_DIR=<isolated output>/target`, `--locked --offline`, no incremental build. The prior CI path was guaranteed to violate the gate's source/output separation rule; v0.8 places gate output under `${RUNNER_TEMP}` instead.

## First: actual native Rust qualification (mandatory)

This repository has **no Cargo dependencies**. On Ubuntu or macOS with Rust installed:

```sh
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --preflight
python3 scripts/native_gate.py --source . --out /tmp/supsearch-native-gate-v08
```

A successful execution writes `/tmp/supsearch-native-gate-v08/qualification.json` and the Rust binary under the isolated `target/release` directory. The source must live outside the qualification output. Compile/tests/native command execution remain unverified until the above is run; the scripts alone provide no native evidence.

## Next: prepare a custodian-held test campaign

Design a task set **not generated from, used to tune, or inspected by the learner**. Write a private `families.json` such as:

```json
{
  "novel_arithmetic_01": "arithmetic_transfer",
  "novel_graph_01": "graph_transfer",
  "novel_list_01": "list_transfer"
}
```

This is only a format example, *not* a sufficient independent campaign. The default pass rule requires at least 20 tasks and at least 3 separately defined families. Curate family labels manually based on underlying semantics, not filename prefixes. Before calling native final evaluation:

```sh
python3 scripts/create_task_map.py \
  --source /evaluator/private_tasks \
  --families /evaluator/families.json \
  --out /evaluator/task_map.json

python3 scripts/transfer_campaign.py freeze \
  --task-map /evaluator/task_map.json \
  --out /evaluator/preregistered_transfer.json
```

For each task, `task_map.json` records `family` and a lowercase 64-hex `sha256` of the actual `.tsk` bytes. The freeze command stores fixed thresholds. Keep `preregistered_transfer.json` outside the training operator's write access, and timestamp/authenticate it through the evaluator's own infrastructure. Its embedded digest only protects against inadvertent edits, not adversarial re-freezing.

Run the v0.6 `external_replay.py evaluate` from a separate evaluator identity/VM, with `--counterbalanced`, disjoint tasks and unique output folders. Run `external_replay.py verify` on each output. Optionally use `attested_replay.py` with an evaluator-private HMAC key. Each external replay must contain task examples actually used in that evaluation. **Mock Python binaries and synthetic fixtures are disallowed.**

## Finally: verify against the preregistration

```sh
python3 scripts/transfer_campaign.py assess \
  --protocol /evaluator/preregistered_transfer.json \
  --native-qualification /tmp/supsearch-native-gate-v08/qualification.json \
  --replay /evaluator/replay_a \
  --replay /evaluator/replay_b \
  --out /evaluator/transfer_assessment.json
```

Optional: add `--attestation-key /evaluator/private-hmac-key.bin` after properly sealing **every** replay. This reads a symmetric secret; never share it with the learner, publish it, or include it in a source ZIP.

Task maps may cover several *disjoint* replay batches; all replays must use the same compiled binary and the same frozen before/after concept libraries and ledger. Missing tasks or repeated task IDs/trial keys cause hard rejection. Evaluation records are recomputed from original per-task JSONL files and hashes by the existing v0.6 verifier.

## Gates and limits

Defaults for a passing **local** qualification: >=20 test tasks, >=3 curated families, >=3 newly solved, zero losses, >=5 percentage points absolute improvement, exact McNemar two-sided p <=0.05, family-bootstrap lower confidence bound >0, native-mined concepts, at least one committed promotion, counterbalanced order, and a matching native build-gate digest.

Family-cluster bootstrap treats *families* as the independent resampling units, not individual tasks. Large improvements across too few families fail. The confidence interval is percentile-based and can miscalibrate for a small number of families. Reusing the same hidden tasks across successive architecture revisions also invalidates prospective evaluation; the local registry is not a substitute for external governance.

Passing local rules does **not** prove general intelligence, mathematical correctness, transfer to unrelated real-world domains, code provenance, external custody or independence of the experiment. The output always reports `independently_validated: false`. HMAC provides symmetric file-integrity assurance only under independent key custody.

## Known limitations

- Native Rust compilation/testing and actual transfer results were not performed in the package-authoring environment; no Rust/Cargo toolchain was installed.
- Existing `external_replay` task-family screen is based on filename prefixes, supplemented here with evaluator-defined test family metadata; neither implies semantic independence.
- Syntactic example-overlap screening misses alpha-equivalent and logically equivalent expressions.
- A native binary header and unauthenticated native-gate receipt do not prove a program was compiled from these sources; use controlled builds, trusted provenance, sandboxing and signed attestations.
- The existing source's internal dev-task decision rule and finite-task correctness checks are not a formal proof engine. In particular, existing examples must not be used as genuine independent holdouts.
