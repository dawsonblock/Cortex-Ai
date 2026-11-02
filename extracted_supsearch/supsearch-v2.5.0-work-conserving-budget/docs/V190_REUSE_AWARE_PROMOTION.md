# v1.9.0: Reuse-aware concept admission (experimental)

## What changes

Version 1.8 allowed an abstraction to be admitted for additional solves even if
its development-work savings were zero or negative. That is useful for capability
exploration but is not an efficiency guarantee. Version 1.9 adds an **optional**
`learn --expected-reuses N` policy. `N=0` (default) preserves the historical
capability-oriented admission gate. For `N>0`, a proposal must first pass the
existing solution/regression tests and additionally meet:

```text
paired_dev_savings = sum(before.built - after.built) over tasks solved by BOTH libraries
measured_round_acquisition = train_built + dev_baseline_built + all_candidate_trial_built

paired_dev_savings > 0 AND paired_dev_savings * N >= measured_round_acquisition
```

The best economic forecast is **only a lower bound on required reuse**. The
learning miner, term normalization, verification CPU, memory growth, and other
computational overheads are not accounted for in candidate expansions.
Development tasks were used to select and promote the concept, so this is
**not** independently demonstrated transfer or amortization.

The system evaluates every accepted candidate and arity and then applies the
reuse forecast before selecting the best eligible candidate. This avoids
losing an economically viable alternative arity to a higher-scoring but
costlier alternative.

A new source module `src/reuse_policy.rs` contains the arithmetic and its native
Rust tests. The journal start binds `expected_reuses`, candidate trials now
record paired savings, and promotion intents record forecast inputs.

## Example native command (requires Rust; not run in packaging environment)

```bash
cargo test --locked
cargo build --release --locked
./target/release/supsearch learn bench \
  --train cnat_add --dev cnat_mul \
  --rounds 1 --budget 0.05 --max-size 4 --max-built 1000 --fuel 1000 \
  --require-native-mined true --expected-reuses 25 \
  --library /tmp/supsearch-v190-library.tsv \
  --ledger /tmp/supsearch-v190-ledger.jsonl
python3 scripts/learning_work_audit_v170.py /tmp/supsearch-v190-ledger.jsonl
python3 scripts/reuse_promotion_audit_v190.py /tmp/supsearch-v190-ledger.jsonl
```

Use **new output paths** for each run. Native journal promotion and concept-library
reconciliation is performed separately by existing source/CLI checks. To measure
genuine transfer, freeze and independently custody unseen task families, compare
baseline and learned libraries using the same native evaluator, record all
unsolved work, and do not tune on the final set.

## Verification boundaries

- Rust toolchain was unavailable during ZIP construction. The native tests and
  compilation commands above are **not** recorded as passed.
- Python tests exercise receipt/auditor semantics and static source wiring; they
  cannot establish Rust compilation or actual concept discovery.
- `--expected-reuses` is an **assumption**, not a measurement of future demand.
- Unlocking a previously unsolved problem creates a capability gain but does not
  create paired cost savings. In cost-aware mode such a concept needs additional
  savings on commonly solved development tasks to qualify. Use default mode for
  pure capability exploration.
- Journal evidence is local and self-reported, not attested by independent hardware
  or an externally controlled evaluator.
- A mathematically valid output on finite examples is not a universal proof.
