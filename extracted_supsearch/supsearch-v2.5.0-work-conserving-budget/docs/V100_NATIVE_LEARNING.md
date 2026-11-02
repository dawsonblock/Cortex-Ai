# v1.0 native learning qualification

1. In an isolated checkout, run `cargo test --locked` and `cargo build --release --locked`.
2. Run `python3 -m unittest discover -s tests -q` and verify the manifest.
3. Run `python3 scripts/native_gate.py --source . --out /tmp/v100-native-NNN`
   with an unused directory. Preserve stdout, stderr, build logs and binary hash.
4. Gather at least three genuinely distinct task families under evaluator custody;
   freeze files and hashes before training. Keep an unseen evaluator-only split.
5. Run `scripts/qualified_pipeline.py prepare` with no `--candidates` file.
6. Train once. The pipeline requires native-mined mode for v1.0 and rejects
   imported candidates. Reconcile the library and ledger with
   `scripts/candidate_lineage_v100.py` (both initial and learned copies).
7. Evaluate exactly once, then `qualified_pipeline.py verify`. Pass evaluator
   controlled `scripts/external_replay.py` results to `transfer_campaign.py`.
8. Record negative results too. Do not call fixture, operator-generated final
   sets, or replay based on known results an independent holdout.

Adversarial checks: provide a known alpha-equivalent train/test example, then
confirm final recheck rejects it; mutate promotion origin in the trial record;
try to promote a rejected candidate; interrupt after intent before commit;
replace one JSONL object with a duplicate-key object. All should fail closed.

Do not use local provenance labels as cryptographic signatures. Native verifier
is finite-example consistency, not general theorem proving. The true blocker
for the research hypothesis is externally reproduced positive transfer after
including exploration and evaluator cost in the accounting.
