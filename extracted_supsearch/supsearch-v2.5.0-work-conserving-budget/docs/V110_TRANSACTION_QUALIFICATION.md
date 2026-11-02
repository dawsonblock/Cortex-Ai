# v1.1 Native qualification and reproducibility protocol

## Problem repaired

The prior runtime sought the strings `"event":"promotion_intent"` and
`"event":"promotion_committed"` anywhere within journal lines, not in a validated
JSON event field. That is unsuitable for safe crash recovery. v1.1 checks structural JSON
records, intent/commit pairing, phase ordering and the loaded concept state before training.

## Native qualification (NOT executed here)

1. Clone or extract this ZIP into a fresh directory with installed `cargo` and `rustc`.
2. Run `cargo test --locked` (the new `src/journal.rs` tests must pass).
3. Run `cargo build --release --locked`, capturing toolchain versions and binary SHA-256.
4. Run `python3 scripts/native_gate.py --source . --out /tmp/supsearch-v110-run`, on a fresh path.
5. With evaluator-controlled, split-separated tasks, train using `--require-native-mined true`
   and zero imported candidates. Record the full ledger, generated library and candidate lineage.
6. Use `scripts/journal_preflight_v110.py` and `scripts/candidate_lineage_v100.py` on the outputs.
7. Evaluate separately custodied unseen transfer families using existing external replay and
   pre-registered campaign tools. Report all failures, compute, baseline search states, solved
   tasks, family-level results, and uncertainty. Repeat with fresh task splits.

## Adversarial tests

Try an orphan commit, intent with forged commit text inside an ordinary JSON string, duplicate
`event` keys, corrupt JSON number, truncated line, reordered phases, rewritten concept body,
and a second process acquiring the same lock. Fail-closed errors are required. After simulated
crash, remove lock **only after** reconciling journal and library.

## Trust boundaries

- These guards are not cryptographic signatures or a proof of actual independent execution.
- They are not a substitute for a trusted evaluation machine or immutable experiment storage.
- Existing source checkers can be bypassed by an adversary able to rewrite source + manifest.
- Finite examples are not mathematical correctness proofs.
- Synthetic examples and author-held holdouts are not independent generalization evidence.
- Identical task-level baseline and upgraded timing budgets may still have scheduling variance.

**Release readiness:** Python protocol stage only until native Rust qualification and
independent transfer are reproduced on a clean machine.
