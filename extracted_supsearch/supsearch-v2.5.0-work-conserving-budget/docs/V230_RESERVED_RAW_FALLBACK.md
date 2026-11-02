# v2.3.0 — Reserved raw-search fallback (experimental)

## Why this exists

The native `learn` command previously ran concept-first search against the
entire `--max-built` allowance, then fell back to raw search with only the
remaining expansions. When the concept-based search exhausted the cap,
**raw fallback received zero expansions**, even if the learned library was
harmful for that task. This change adds an *optional* reserved share.

## Behavior

`--raw-reserve-pct N` accepts an integer from **0 through 95**. The default
of **0 preserves v2.2 behavior**. Nonzero values require `--max-built >= 2`
(the 0 value in the Rust bank means *unbounded*, so an unlimited search cannot
be combined with a reserve). When a concept library is available:

- Concept search receives at most `total - ceil(total*N/100)` expansions,
  with both concept and raw shares bounded to at least one expansion.
- If composition produces a candidate that passes every finite training
  example, the raw path is skipped. Reserved expansions are unused.
- Otherwise raw enumeration receives the entire remaining shared budget,
  including unused concept allowance. Across both searches the total measured
  candidate expansions may not exceed `--max-built`.
- When the concept library is initially empty, raw search retains the full
  total budget. The setting has no effect on concept-neutral tasks.

Example:

```bash
cargo test --locked --offline
cargo build --release --locked --offline
./target/release/supsearch learn bench \
  --train cnat_add --dev cnat_mul \
  --rounds 1 --max-size 4 --budget 0.05 \
  --max-built 1000 --raw-reserve-pct 25 \
  --library /tmp/supsearch-v230-concepts.tsv \
  --ledger /tmp/supsearch-v230-journal.jsonl
python3 scripts/search_budget_audit_v230.py \
  --ledger /tmp/supsearch-v230-journal.jsonl
```

Use fresh output paths because the journal is append-only and protects against
unsafe replay/recovery.

## Measurement and scope

- `composed_limit` and `raw_limit` are recorded on each native `train_attempt`.
- `raw_reserve_pct` is included in the schema-8 `start` record. Schema 8 is
  retained because older event semantics are unchanged and new keys are additive.
- `scripts/search_budget_audit_v230.py` checks cap arithmetic, field consistency,
  terminal completion, duplicate JSON keys, and forged/overbudget results.
- `scripts/native_gate.py` now exercises `--raw-reserve-pct 25` and runs the
  budget auditor after its native learning smoke run.
- Included Rust unit tests exercise small, large, overflow and legacy budgets.

This is an **algorithmic safeguard**, not evidence that learning becomes faster
or more general. Reserving raw budget can also reduce concept-first success
when the useful concept needs more expansions. The setting applies to native
`learn` training attempts, not the independent `evaluate` subcommand.

No Rust compiler was available in the release environment. Rust tests and the
native gate must be executed before calling this release native-qualified.
