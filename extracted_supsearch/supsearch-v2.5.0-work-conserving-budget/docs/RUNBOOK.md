# Running the upgraded system

## Requirements

Rust/Cargo stable (Rust 1.82 or later recommended), Python 3.9+ only for fixture generation and offline package checks. Cargo.toml remains zero-dependency.

## Build and test

```bash
cargo test
cargo build --release
python3 -m unittest discover -s tests -v
```

## Demonstration with supplied candidate

```bash
python3 scripts/generate_curriculum.py
cargo run --release -- learn examples/curriculum \
  --train prod_train2,prod_train3 \
  --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5 \
  --candidates examples/multiplication.candidates \
  --rounds 2 --budget 0.5 --max-size 13 \
  --top-tasks 1 --max-candidates 4 --max-arity 2 \
  --library out/learning/concepts.tsv \
  --ledger out/learning/decisions.jsonl
```

This demonstration passes an already known multiplication candidate; it does **not** demonstrate autonomous discovery of multiplication. Promotion should only happen if the candidate actually clears the development gate in that runtime. No result is predeclared.

## Candidate import and continuation

Place one fully closed lambda expression per line into a UTF-8 file. Lines starting with `//` or `#` are comments. Pass with `--candidates FILE`.

Rerunning with the same `--library` loads existing concepts. For a clean evaluation use new run-specific library and ledger paths. Do not combine results across runs while reusing the supposed sealed test set.

## Baseline comparison and reporting

Run an unchanged baseline with the same task budget, fuel, pool-cap and compiler version. Track per-task solved flag and `built` candidate compositions, plus CPU time and RSS measured externally. Where no concepts are supplied, the concept-composition algorithm may return zero built and unsolved. This is not equivalent to an independent raw-lambda search baseline; distinguish these search methods in reports.

Do not report `local_final_test` as `external_holdout`.

## Failure recovery

Inspect the ledger for `promotion_intent` entries without matching `promotion_committed` entries. Compare named concepts and bodies against the TSV library. A crash or write failure needs operator reconciliation rather than assuming exactly-once promotion. Record whether the library has been updated before retrying.

## Audit a run and check package source hashes

```bash
python3 scripts/audit_run.py out/learning/decisions.jsonl
python3 scripts/check_manifest.py .
```

The audit script understands multiple appended runs and flags dangling intents or
selection after the final-test phase within a run. It cannot independently
prove that the ledger has not been modified.
