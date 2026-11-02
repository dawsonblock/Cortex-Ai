# v2.4.0 — Nonempty-library native fallback qualification

**Source-complete experimental release; NOT native-qualified until a real Rust binary passes on a separate machine.**

## Change

v2.3's `native_gate.py` exercised `--raw-reserve-pct 25`, but its learning
session began with **zero concepts**. The engine intentionally skips concept
search in that case, so the check could pass without ever entering the
reservation path. The allocation was only verified with Rust arithmetic tests
and Python-supplied ledger fixtures.

v2.4 adds two separate checks:

1. `src/learning.rs::v240_nonempty_fallback_tests`: a native Rust unit test
   loading a fixed pre-existing multiplication combinator and tuple-reversal
   task. It gives the concept search **1 of 20** candidate expansions and
   requires actual positive bounded work in both concept-first and raw search.
2. `scripts/native_reserved_fallback_v240.py`: a **real native CLI** campaign
   using `examples/v240_preloaded_library.tsv`. The smoke is a separate run,
   not the empty-library case. Its fail-closed checker requires
   `start.initial_concepts == 1`, `composed_limit == 1`,
   `0 < composed_built <= 1`, `kind == "raw"`, `raw_built > 0`, a reserved
   raw budget of at least 19, and retention of the preloaded concept.
   Failed native execution is not turned into a synthetic pass.

Both are deliberately **smoke tests**. No native promotion is required; zero
promotions is not a failure of reserved fallback. The seeded combinator is an
**externally supplied fixture**, not a self-discovered abstraction. Neither
check demonstrates improved native learning, generalization, or net cost gains.

## Run on a machine with Rust

```bash
cargo test --locked --offline
cargo build --release --locked --offline
python3 scripts/native_reserved_fallback_v240.py \
    --binary ./target/release/supsearch --source . \
    --out /tmp/supsearch-v240-reserved-native
python3 scripts/native_gate.py \
    --source . --out /tmp/supsearch-v240-full-gate
```

Use **new output paths** each time. Qualification artifacts include the
native command/logs, JSONL journal, final library, and
`probe_qualification.json` with the executable SHA-256. The full native gate
must pass the added nonempty-library check before it issues a success report.

## Known limitations

- Rust compilation could not be run in the packaging environment; no native
  claims are asserted in the packaged validation file.
- `--max-built` counts candidate expansions, not CPU cycles or elapsed time.
  Concept and raw solver time budgets remain per-solver, not one strict shared
  wall-clock deadline.
- The finite-example recheck is not a formal proof.
- The probe's single preloaded concept is intentionally unrelated to the
  training task; this tests the **failure/fallback** path, not effective reuse.
- A passing internal CLI smoke is not an independent external transfer study.
