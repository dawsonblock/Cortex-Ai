# v0.9 — Native overlap screening and transfer-family breadth

## Implemented, not yet reproduced natively

- The Rust learner now screens **parsed training/development examples** using de Bruijn lambda-term representations. It rejects shared structurally equal tests even when binders are renamed, headers differ or task IDs differ. This is stronger than byte-level duplicate detection but not proof of beta/eta or semantic separation. The sealed final evaluation data remains unopened until the learning phase ends.
- Internal final testing now compares the **original** and **post-learning** concept libraries using the same concept-mode solver, emitting `final_test_paired`. An internal comparison is NOT an independent final holdout.
- Native evaluator rejects output paths inside the task tree including nonexistent descendants and existing symlink aliases. Read-only source checks cannot substitute for OS isolation from malicious processes.
- New campaign schema `supsearch-transfer-campaign-v2` adds **preregistered** `min_positive_families` and `min_family_size` gates, family effects, and leave-one-family-out descriptive estimates. Unlike a 20-task gain concentrated in one family, the default requires net-positive outcomes in at least two distinct declared families. Results continue to require the previously implemented tests.
- v1 preregistrations are still accepted and verified **with their exact original content hashes**. New v2 thresholds are not backfilled into existing v1 frozen designs.

## Honest current verification boundary

This package was authored in a runtime with Python 3 but without `cargo` or `rustc`. Python protocol/unit tests can be executed; **Rust compilation and actual learning outcomes remain unverified**. No user data were used to construct an external holdout. Author-authored synthetic examples are not scientific evidence of transferable learning.

## Native command on Mac/Linux with Rust

```bash
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --preflight
python3 scripts/native_gate.py --source . --out /tmp/supsearch-native-v09
```

Ensure that `/tmp/supsearch-native-v09` does not already exist. The qualification tool runs offline `cargo test --locked`, an isolated release build, concept-mode baseline and raw-mode reference on a small task, and a native learning smoke test. If compilation fails, repair the code and rerun the entire qualification. A smoke passing with zero admitted concepts does **not** prove learning.

## Prospective transfer campaign

1. An evaluator curates at least 20 hidden tasks across >=3 semantic families, >=2 tasks in each family, independent of the training set and operator. Those task-family labels are human hypotheses, not formal proofs of disjointness.
2. The evaluator generates a private task map and freezes v2 preregistration before exposure. Authenticate timestamps and hashes under independent custody.
3. Run genuine `supsearch learn` from training-only inputs and freeze the before/after libraries and decision ledger.
4. Run `external_replay.py` using the same exact binary on evaluator-held unseen tasks in counterbalanced mode. Authenticate replay artifacts with an evaluator-private key if available. Do not use synthetic/mocked replays.
5. Run `transfer_campaign.py assess`. The default v2 family breadth test is mandatory for newly frozen v2 protocols.
6. Conduct independent reproduction on another machine before claiming independent validation.

## Known remaining problems

- Native Rust tests not executed by the package authoring session; toolchain absent.
- Finite-example verification only; no formal proof of inferred concepts.
- Syntactic/parsed-structure duplicate detection misses beta/eta-equivalent test expressions.
- Family labels and preregistration custody are assertions until externally verified.
- Test dataset generation and genuinely independent learning-to-learn outcomes remain unproven.
- HMAC evidence sealing is only secure under independent key custody and has no PKI identity guarantees.
