# Supsearch v0.7.0 — Attested Replay & Native Qualification

**Status: source and Python-protocol verified. Native Rust compilation and autonomous concept-learning transfer are NOT verified in the packaging environment.**

## What is new

1. `scripts/attested_replay.py`: an independent evaluator can seal an existing valid external replay with HMAC-SHA256. The key is a 32-byte random secret stored OUTSIDE the replay and source tree. The attestation covers every regular replay artifact (including logs), file count, byte sizes, file digests, the trial key and the evaluator key identifier. Changes/additions/deletions and mismatched keys fail verification. A consumed replay cannot be silently resealed. A local secret under the learner's control does not establish independent custody. **Never put key material into a source archive or log.**
2. `scripts/native_gate.py`: builds and tests with Cargo, checks native executable format, runs real `evaluate` in concept-empty and raw-reference modes, and runs a bounded `learn` invocation. Produces a qualification report only when all checks pass; a failure produces `FAILURE.txt` and no positive result. These smoke tests show operability, not improvement.
3. The native evaluator now rejects more than 200 task IDs per invocation.
4. Negative tests covering HMAC substitution, file tampering, directory additions, unsafe key permissions, symlinks and fail-closed missing-Cargo behavior.

## Commands

```sh
# Source/protocol checks (uses Python stdlib only)
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .

# Must be executed on a machine with Rust/Cargo.
python3 scripts/native_gate.py --preflight
python3 scripts/native_gate.py --source . --out /tmp/supsearch-native-qual-001

# After a replay was generated and independently verified:
# create the HMAC key in an evaluator-owned, private directory, outside the replay.
python3 scripts/attested_replay.py init-key --key /private-evaluator/secret-key.bin
python3 scripts/attested_replay.py seal --out /evaluator-results/trial-001 --key /private-evaluator/secret-key.bin
python3 scripts/attested_replay.py verify --out /evaluator-results/trial-001 --key /private-evaluator/secret-key.bin
```

`init-key` creates exactly 32 cryptographically random bytes with file mode `0600`, and refuses overwriting an existing secret. This is symmetric authentication, not a public-key signature or trusted attestation. Everyone with the secret can forge the seal. Verifiers need access to that secret, or must trust the evaluator to verify it.

## Acceptance criteria for transfer-learning research

Run `native_gate.py` on the actual target platform first. Design a pre-registered experiment using isolated training, development, and independently stewarded test families, with no hidden candidate hand-seeding. Use the same `concept_solve` search algorithm for both baseline and upgraded concept-library arms. Evaluate unseen tasks once, recompute paired work and success statistics, account for family clustering and repeated experiments, and seal the evaluator report with a key the learner cannot access. No synthetic or mock test qualifies as independent holdout evidence.

**Remaining blockers:** Cargo compile/test has not run here; no real native learning improvement or transfer has been shown; HMAC cannot secure compromised evaluator administration; task-family split names do not prove semantic novelty; finite example checks are not universal proofs. Existing v0.3 curriculum has known leakage. All prior limitations remain unless specifically replaced above.
