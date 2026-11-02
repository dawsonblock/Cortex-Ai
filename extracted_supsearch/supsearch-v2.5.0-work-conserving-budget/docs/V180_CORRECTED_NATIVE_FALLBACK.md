# v1.8.0: corrected native learning fallback

## Root-cause defect

In v1.7, native `learn` used a non-exhaustive Rust match on an optional
composed solution. `Some(program)` with `solution_matches_examples(..) == false`
had no arm. The Rust compiler should reject the match with E0004. As a
result all older Python-only validation claims **cannot** qualify the native
learning engine.

## Implemented changes

1. Replaced the non-exhaustive match with `verified_or_raw_fallback`.
2. Finite-example checking accepts only verified composed solutions.
3. Missing or invalid composed results fall back to raw search.
4. Invalid raw solutions are filtered before they enter the mining corpus.
5. A raw fallback's `stats.built` remains counted alongside composed-search
   expansion counts in the native accounting receipt.
6. Added four Rust regression tests for all result paths and one Unix-only
   candidate-symlink rejection test.
7. Changed external candidate-file ingestion to refuse symlinks and to cap
   the actual bytes read, mirroring the existing task-file protection.

## Qualification

### Executed in packaging environment

- ZIP structural integrity and complete SHA-256 manifest recomputation.
- Python unit tests including v1.8 static source-wiring checks.

### Requires native Rust toolchain (not claimed passed here)

```sh
cargo test --locked
cargo build --release --locked
```

The original v1.7 native learning campaign, including matching baseline and
learned replay, remains available:

```sh
python3 scripts/native_learning_campaign_v170.py --help
```

A passing `cargo test` establishes local compilation and unit behavior, **not**
independently demonstrated concept acquisition, unbiased transfer, or general
intelligence. Those require genuine native multi-family learning campaigns.
