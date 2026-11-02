# v0.5 Evidence protocol and native reproduction

This package contains the **complete original supsearch sources** plus
successive experimental upgrades. It does not include external model weights
or a downloaded Rust toolchain.

## 1. Reproduce build in a trusted machine (Linux or macOS)

```sh
python3 -m unittest discover -s tests -v
cargo test --locked
cargo build --release --locked
python3 scripts/check_manifest.py .
```

The source/archive integrity manifest is only a content checksum. It is not a
publisher signature. It should not be used as a trust anchor.

## 2. Observe the known bad fixture

```sh
python3 scripts/qualified_pipeline.py audit-splits \
  --source examples/curriculum \
  --train prod_train2,prod_train3 \
  --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5
```

This **must fail**: known equivalent example sets cross train/dev and
dev/test. Do not disable the rejection for any claimed generalization result.
For an instructional demonstration only, append `--fixture-mode`. Its report
is labeled `synthetic_fixture_not_holdout`.

## 3. Run a small native CLI smoke check

```sh
mkdir -p out/manual
./target/release/supsearch evaluate bench \
  --tasks cnat_add --mode raw --out out/manual/raw-smoke.jsonl \
  --budget 0.05 --max-size 4 --fuel 1000
```

The second identical invocation must fail rather than overwrite the result.
It may remain unsolved under that intentionally tiny search budget.

## 4. A real experiment

Supply your own independently designed task corpus. Use unique task IDs and
avoid reusing examples or task-generator families across train/dev/final. A
minimum of 20 final tasks is the default *advisory screen*, not an adequate
power analysis for all task distributions. Use an evaluator in a separate
security domain for genuine holdout custody. `prepare` only enforces local
path separation and file checks.

```sh
python3 scripts/qualified_pipeline.py prepare \
  --source /path/to/independent/tasks \
  --train tr_a,tr_b --dev dv_a,dv_b --test te_a,te_b \
  --disjoint-families --binary ./target/release/supsearch \
  --run out/qualified/experiment-001 --rounds 3 --budget 2
python3 scripts/qualified_pipeline.py train --run out/qualified/experiment-001
python3 scripts/qualified_pipeline.py evaluate --run out/qualified/experiment-001
python3 scripts/qualified_pipeline.py verify --run out/qualified/experiment-001
```

The IDs and path in this illustration are placeholders; they are not included
in the archive. Do not use `--candidates` if making a claim about autonomous
mining: that option explicitly seeds known expressions.

## 5. Evidence interpretation

- `quality_gate.local_screen_passed` is a **descriptive local screening gate**.
  It requires the configured minimum task count, zero final regressions, a
  strict solve-rate improvement, at least one committed promotion, a
  non-seeded candidate run, non-fixture datasets, and a plausible native
  executable header. It is **not an independent test result**.
- `promotion_lineage` ensures that all added concepts match local recorded
  intent and commitment metadata. It does **not** prove that their semantics
  generalize, or that all local evidence was not jointly forged.
- Baseline vs upgraded uses the same `concept` search mode. Raw mode is a
  secondary reference, not the same-algorithm control.
- Final tests remain accessible to other processes with filesystem access.
  A separate evaluator, immutable preregistration and external custody are
  necessary for stronger claims.
- Program-discovery/evaluation cost and number of learning rounds must be
  reported alongside final solve gains. Overfitting can occur through repeated
  use of the development set or repeated runs against known final tests.

## 6. Required before claiming generalization

1. All Rust/Python tests pass from a clean checkout; frozen source hash recorded.
2. Native non-mock, non-seeded program discovery occurs repeatedly.
3. All learning costs (compute/search/time) are accounted for.
4. Comparison includes a matched concept-mode baseline and explicit ablations.
5. Independent final evaluator holds previously unseen task families and
   verifies claims from frozen artifacts under no-reuse and attack tests.
6. External reproduction agrees, including regressions and negative results.
