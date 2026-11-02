# V2.5 — Per-attempt shared wall-clock allowance (soft time limit)

## Problem

The v2.4 `--max-built` candidate-expansion limit was shared between
concept-first and raw enumeration, but **each search received a fresh
`--budget` seconds**. This could allow one training attempt to run both
searches for approximately the full configured duration each.

## Correction

`learn` now defaults to `--shared-time-budget true`. The code creates one
`Instant` at the start of each training task. The raw solver receives only
the remaining wall-clock allowance after concept search and finite-example
reverification. If none remains, raw search does not start. Old behavior can
be requested with `--shared-time-budget false` for explicitly labeled
comparison experiments.

`--max-built` and `--raw-reserve-pct` remain independent candidate-expansion
controls. Reserving expansions **does not** reserve milliseconds; concept
search may still exhaust the time allowance. The bank checks elapsed time
periodically, so this is a **soft** deadline, not a hard resource boundary.
Use an external process timeout and OS isolation for strict termination.

## Evidence

The `start` ledger record includes `shared_time_budget` and
`time_budget_secs`. Each `train_attempt` also includes
`composed_elapsed_secs`, `raw_time_limit_secs`, `raw_elapsed_secs` and
`wall_elapsed_secs` (serialized to nine decimal places). The checker
`scripts/shared_deadline_audit_v250.py` rejects impossible local accounting;
these fields are self-reported, so matching numbers alone do not prove the
native executable ran.

## Reproduce on Rust-enabled machine

```bash
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -p 'test_v250.py' -v
python3 scripts/native_shared_deadline_v250.py \
  --binary ./target/release/supsearch --source . \
  --out /tmp/supsearch-v250-native-deadline
python3 scripts/shared_deadline_audit_v250.py \
  --ledger /tmp/supsearch-v250-native-deadline/native_probe.jsonl
```

`native_shared_deadline_v250.py` requires a real native executable and
preloaded library, not a mock journal. It is still **a bounded fallback
smoke**, not proof of autonomous acquisition or external transfer. Independent
final-test tasks and end-to-end work accounting remain required.
