# Supsearch v0.4.0 qualification and custody runbook

## First principle

A valid experiment must distinguish **concept discovery**, **candidate admission on development data**, and **evaluation against final data never used to tune the system**. A filename split is not a statistical split. No code shipped in this project provides external evaluator custody or stops an OS user from rewriting files under their control.

## Compile the native system

Requires installed stable Rust/Cargo and Python >=3.9. From the repository root:

```bash
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -v
python3 scripts/check_manifest.py .
```

Never interpret the Python tests as evidence that the Rust solver executes successfully. Test at least one native `evaluate` invocation against your newly compiled binary before relying on experimental results.

## Discover leakage before using the included fixture

```bash
python3 scripts/qualified_pipeline.py audit-splits \
  --source examples/curriculum \
  --train prod_train2,prod_train3 \
  --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5
```

The command is expected to **exit 2** because `prod_train3` shares all normalized examples with `prod_dev3`, while `prod_dev4` shares all normalized examples with `prod_final4`. Do not quote that example as holdout validation.

A researcher interested in reproducing the *synthetic demonstration only* may append `--fixture-mode` to `prepare` or `audit-splits`; `state.json` and the report will explicitly record `synthetic_fixture_not_holdout`.

## Use new non-overlapping tasks

Prepare task files that share neither literal input/output example pairs nor near-duplicate problem templates across final-test families. Fix the split plan **before** building the system. Maintain third-party custody for a genuinely independent final evaluation.

```bash
python3 scripts/qualified_pipeline.py prepare \
  --source /ABS/PATH/TO/task-set \
  --train familyA_t1,familyA_t2 \
  --dev familyB_v1,familyB_v2 \
  --test familyC_f1,familyC_f2 \
  --binary ./target/release/supsearch \
  --run out/qualified/experiment-001 \
  --rounds 3 --budget 0.5 --disjoint-families

python3 scripts/qualified_pipeline.py train --run out/qualified/experiment-001
python3 scripts/qualified_pipeline.py evaluate --run out/qualified/experiment-001
python3 scripts/qualified_pipeline.py verify --run out/qualified/experiment-001
```

`--disjoint-families` uses the first underscore-separated token as a **naming-based** family proxy. Prefer an independently documented set of real task-generating mechanisms rather than assuming this heuristic captures semantic families. The final-task files are locally sealed only; any process running under the same OS user can read them. For genuine benchmark qualification, train on one system and arrange for externally held final tasks to be delivered to a separate evaluator after the candidate library is frozen.

## Interpretation of statistics

The report includes concept-baseline versus concept-upgraded results using the **same native concept search algorithm**, plus a separate raw-search reference. It reports:

- Paired solve count, newly solved tasks and regressions.
- Mean paired solve-rate difference and a deterministic, task-level bootstrap 95% interval. This is descriptive and assumes exchangeable tasks.
- Exact two-sided McNemar discordance p-value (only informative under independent, sufficiently numerous matched tasks and a preregistered single comparison).
- Sum of search states for tasks solved by both models and geometric mean upgraded/baseline work ratio on these jointly solved tasks. Both exclude newly unlocked tasks and are subject to survivorship bias.

None of these automatically establishes learning-to-learn. Measure **total discovery and evaluation compute**, separate from final inference compute. Replicate on multiple preselected task families with freshly frozen final tests and report unfavorable outcomes.

## Integrity and failure limits

- A SHA-256 inventory detects accidental corruption if the inventory itself is trusted. Its hashes are not signed.
- Every CLI train/evaluate/verify operation takes a cooperative O_EXCL lock. If the process crashes, interrupted phase state remains consumed; do not delete a leftover lock and rerun without manual audit. Start a clean experiment instead.
- Test examples are not sent to the learner by the normal pipeline. They remain readable on the host filesystem to an intentionally malicious process. To enforce external holdout secrecy, use a physically separate evaluator account/machine or independent service and a precommitted candidate library.
- A changed report is checked against its underlying evaluation files, but all local files remain changeable by a sufficiently privileged user.
- Candidate equivalence is only checked on bounded examples; counterexamples may exist.
- Native evaluator refuses to overwrite an existing result path, reducing accidental final-test replay but not making OS-level replay impossible.

## v0.4 release acceptance gate

Release is **research-qualified only** after native compilation, all native unit tests, original research regression tests, a no-candidate mining experiment, resource-exhaustion and crash tests, and a separate evaluator-owned final suite. If any gate fails, report the defect and do not claim autonomous transfer learning.
