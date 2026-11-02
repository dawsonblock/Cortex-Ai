# Supsearch v2.5.0 — Work-conserving search time

- Corrected a second budget dimension: per-task wall-clock allowance is now
  shared between concept-first enumeration and verified raw fallback.
- Exposed `--shared-time-budget true|false`, default `true` (use `false` for
  explicitly labeled legacy comparisons).
- Prevented raw fallback when the allotted time is already exhausted.
- Added train-attempt phase timings, self-reported time-budget audit,
  adversarial protocol tests, native nonempty-library probe and CI wiring.
- Retained prior source, regressions, shared candidate-expansion cap, MDL,
  curriculum, reuse-aware promotion, and evaluation tools.
- Qualification remains open until Rust/Cargo builds and native tests run.

---

# Supsearch v2.4.0 — Verified Fallback Qualification (Source Release)

This source release preserves the complete v2.3 synthesizer, concept-miner,
learning controller, MDL/compression gate, reuse economics, native campaigns,
audit tools, fixtures, and tests.

## New

- A Rust unit test executes **concept-first search and raw fallback** with an
  actual preloaded concept and a strict 20-expansion shared cap.
- A native executable probe uses its own **nonempty** initial library and
  separate training/development tasks, captures real native ledger evidence,
  and refuses to pass unless both search paths perform positive work.
- Native qualification now invokes this probe and requires its verdict.
- An independent receipt checker rejects missing concepts, nonexistent
  fallback work, forged caps, lost library entries, malformed JSONL, and
  substituted script executables.
- Added adversarial Python tests and wired the native probe into CI.
- Aligned package and lockfile versions to 2.4.0.

## Qualification limits

Package/regression testing is recorded in `VALIDATION_V240.json`. No Rust
compiler is installed here; no Rust compilation, native runtime qualification,
autonomous learning improvement, or independent transfer result is claimed.
The prior release's Python-only checks are not relabeled as native evidence.

See `docs/V240_NONEMPTY_NATIVE_FALLBACK.md` for exact replay commands.
