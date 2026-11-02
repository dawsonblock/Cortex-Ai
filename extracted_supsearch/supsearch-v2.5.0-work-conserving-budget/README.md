# Supsearch v2.5.0 — Work-conserving shared search time

This complete-source experimental upgrade retains the v2.4 engine and adds
an actual shared per-training-task **time allowance** across concept search
and raw fallback. Default-on `--shared-time-budget true` prevents raw search
from receiving an independent fresh `--budget` after a failed concept search.
Existing shared candidate-expansion limits and reserved fallback remain.

- [Mechanism and native qualification](docs/V250_SHARED_DEADLINE.md)
- [Release notes](RELEASE_NOTES.md)
- [Local validation evidence](VALIDATION_V250.json)

**Qualification boundaries:** Source and Python protocol tests do not prove
Rust compilation, external transfer, or AI improvement. Rust compilation and
native campaigns are required in a Rust-enabled environment. The bank's
periodic checks make wall time a *soft* upper bound.

---

# Supsearch v2.4.0 — Nonempty-Library Native Fallback Qualification

Supersedes v2.3.0. **Experimental complete-source release; Rust qualification not
established in this packaging environment.**

The earlier native smoke checked budget receipts but began with an empty
concept library. v2.4 includes a real Rust unit test and a separate native
binary probe using a preloaded, explicitly external concept. They check that
concept-first search actually runs, fails under its reserved one-expansion cap,
and leaves positive candidate-expansion budget to verified raw search.

- [Native probe, limits, and replay commands](docs/V240_NONEMPTY_NATIVE_FALLBACK.md)
- [Validation from this packaging environment](VALIDATION_V240.json)
- [Release notes](RELEASE_NOTES.md)

---

# Supsearch v2.3.0 — Reserved Raw Fallback (Full Source)

Supersedes v2.2.0. **Experimental source release, not native-qualified.**

Adds optional `--raw-reserve-pct 0..95` to `learn`. With `--max-built >= 2`,
it allocates a reserved fraction of candidate expansions to independently
rechecked raw enumeration so a failed concept-first search cannot consume
the entire search allowance. Default 0 preserves the prior allocation.

Includes Rust allocation unit tests, JSONL per-attempt budget receipts, a new
Python fail-closed audit, native-gate wiring, and additional regression tests.

- [Detailed semantics and commands](docs/V230_RESERVED_RAW_FALLBACK.md)
- [Current validation record](VALIDATION_V230.json)
- [Release notes](RELEASE_NOTES.md)

**Important:** No Rust/Cargo toolchain was available. Native learning and
independent transfer gains are **not established** by local Python tests.

---

# Supsearch v2.2.0 — Abstraction Quality & Native Qualification Hooks

A full source upgrade of v2.1, preserving the existing Rust synthesizer, learning
engine, adaptive curriculum, cost-aware promotion, evidence scripts, and tests.

**New (optional; off by default):**

- `--min-mdl-gain N`: require training-corpus AST compression benefit before promotion.
- `--min-positive-families N`: require positive results in at least N named development-task families.
- `scripts/concept_admission_audit_v220.py`: audit frozen admission settings and matching self-reported promotion/trial evidence.
- `scripts/native_gate.py`: now executes the new auditor during genuine native smoke qualification.
- Native Rust unit tests in `src/mdl.rs` and `src/learning.rs` plus new Python adversarial tests.

**Important:** This is an experimental source release. All new admission gates are
heuristics, and are not formal proofs or evidence of independent transfer. The
packaging environment does not contain Cargo/rustc, so native compilation and
performance have not been verified here. See
[`docs/V220_CONCEPT_QUALITY_QUALIFICATION.md`](docs/V220_CONCEPT_QUALITY_QUALIFICATION.md)
and `VALIDATION_V220.json` for exactly what was tested.

---

# Supsearch v2.1.0 — Learning Reliability & Native Gate Repair

This is a complete source upgrade of v2.0.0, **not** a qualified native release.

## What is corrected

1. **Adaptive curriculum reward inflation fixed:** first-ever solves receive a one-time reward; recovering an earlier solve after a regression no longer earns a second first-solve reward. A genuine reduction in candidate expansions is rewarded only when the task succeeded on both consecutive attempts.
2. **Native qualification schema fixed:** `scripts/native_gate.py` now expects the schema-8 learning journal actually written by `src/learning.rs`. The previous v2.0 gate incorrectly expected schema 7, making qualification fail even after a successful native run.
3. **Temporary output hardening:** persistent-library and immutable-evaluation writes use exclusive `create_new(true)` temporary files. A preexisting temporary file or symlink is left intact and causes a fail-closed error instead of being truncated or removed. This is cooperative local integrity, **not** hostile filesystem isolation.
4. **Additional native unit tests** for curriculum recovery and preexisting temporary-file protection; six new Python tests for qualification wiring and guards; updated CI and Cargo metadata.

## Validation boundary

- Tested here: 55 targeted Python regression tests passed across v1.7, v1.8, v1.9, v2.0, v2.1; 6 are new.
- The full legacy Python suite was attempted but **timed out**. Do not interpret targeted passes as full-suite coverage.
- `rustc` and `cargo` were unavailable. Rust compilation, Rust unit tests, native learning, autonomous transfer and commercial/production qualification are **not verified**.
- `--curriculum-policy adaptive` uses a deterministic training-feedback heuristic; no learned cross-domain meta-policy is demonstrated.

## Minimum real qualification (on a machine with Rust installed)

```bash
cargo test --locked --offline
cargo build --release --locked --offline
python3 -m unittest discover -s tests -p 'test_v210.py' -v
python3 scripts/native_gate.py --source . --out /tmp/supsearch-v210-native-gate
```

The native gate must produce a valid `qualification.json` with a native binary digest and completed Rust learning journal. **This is still only native smoke qualification**, not proof of transfer. For transfer, run the existing independent evaluator/campaign tools with held-out tasks maintained by a separate evaluator.

See `docs/V210_NATIVE_QUALIFICATION.md` and `VALIDATION_V210.json`.

---

# Supsearch v2.0.0 — Experimental adaptive curriculum and shared work budget

**Complete source upgrade from v1.9.0.** Added optional deterministic
training-feedback-driven curriculum selection (`--curriculum-policy adaptive`),
kept `heuristic` as the unchanged default, recorded per-round selections,
provided an independent Python ledger-consistency auditor, and constrained
concept-first + raw fallback **training** expansions to one `--max-built` cap
when nonzero. The policy does not use final evaluation data and does not
predict causal generalization. The rest of the source and historical tests are
preserved.

See [`docs/V200_ADAPTIVE_CURRICULUM.md`](docs/V200_ADAPTIVE_CURRICULUM.md)
and [`VALIDATION_V200.json`](VALIDATION_V200.json).

Run native qualification **on a Rust-enabled machine**:

```bash
cargo test --locked && cargo build --release --locked
python3 -m unittest discover -s tests -p 'test_v200.py' -v
```

**Qualification boundary:** The packaging environment has no `cargo` or
`rustc`; native compilation, algorithm correctness, and transfer performance
remain unverified. Passing Python protocol tests is not native qualification.

---

# Supsearch v1.8.0 — Corrected native fallback (experimental)

Supersedes v1.7.0. Repairs a native Rust compilation defect in `learn`:
invalid `Some(composed_solution)` now executes a verified raw fallback instead
of leaving a non-exhaustive match. Invalid raw candidates are filtered, and
composition-plus-fallback expansion counts are retained. Candidate-file
loading also rejects symlinks and excessive reads.

**New native regression tests exist but have not been executed unless the
attached validation record explicitly records a native toolchain run.**

```sh
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -p 'test_v180.py' -v
```

See `docs/V180_CORRECTED_NATIVE_FALLBACK.md` and `VALIDATION_V180.json`.

---

# Supsearch v1.7.0 — Search-work accounting (experimental)

The full original Rust supsearch synthesizer and all preceding experimental releases are preserved. v1.7 fixes a concrete work-accounting defect in `src/learning.rs`: unsuccessful concept-composition searches were not included when raw fallback was required. Native candidate evaluation costs also went unreported.

**What is new:** schema-8 per-attempt and per-round search-work receipts, a strict Python auditor that reconciles them, break-even sensitivity accounting, and protocol adversarial tests. It **does not** prove any abstract concept transfers independently, or that learning pays for itself.

See [`docs/V170_MEASURED_LEARNING.md`](docs/V170_MEASURED_LEARNING.md).

```bash
python3 -m unittest discover -s tests -p 'test_v170.py' -v
python3 scripts/learning_work_audit_v170.py --help
python3 scripts/native_learning_campaign_v170.py --help
```

A native Rust toolchain is required for end-to-end learning experiments:

```bash
cargo test --locked
cargo build --release --locked
```

**Certification status:** The ZIP builder did not have Rust/Cargo, so these commands were not executed. No native learning benchmark or independent held-out transfer was performed for this release.

---

# Supsearch v1.6.0 — Native Learning Campaign (Experimental Source)

This full-source release introduces `scripts/native_learning_campaign_v160.py`, which ties **actual `learn` execution** to a reconciled native-mining promotion journal and a matched baseline/learned `concept`-mode final evaluation. It uses two separate task directories, verifies input hashes before and after execution, checks exact example overlaps and final ID-family reuse, rejects imported promotions, and reports final search work **including unsolved tasks**. Unlike the v1.5 paired runner, the v1.6 orchestrator does not accept an arbitrary preconstructed "learned" library in place of running the learner.

**Qualification boundary:** Rust/Cargo is not available in the package-creation environment. Only Python protocol tests were executed; neither a genuine native learning campaign nor an independent final-transfer result has been run. A script-based mock is strictly labeled `test_double_not_native` and cannot qualify the release. A recognized executable header does not attest its source code.

```bash
python3 -m unittest discover -s tests -p 'test_v160.py' -v
python3 scripts/native_learning_campaign_v160.py --help
# Read docs/V160_NATIVE_LEARNING_CAMPAIGN.md for the native Rust and final replay workflow.
```

See `docs/V160_NATIVE_LEARNING_CAMPAIGN.md`, `RELEASE_NOTES.md`, `VALIDATION_V160.json`, and the full preserved historical implementation below.

---

# Supsearch v1.5.0 — Native Paired Transfer Qualification (Research Source)

The v1.5 release provides a runnable **concept-search versus concept-search** native evaluation driver, plus full-work accounting for the v1.4 synthetic Python learner. It preserves the complete previous source and tests.

```bash
# Python tests and reference experiment (do not qualify native Rust):
python3 -m unittest discover -s tests -p 'test_v150.py' -v
python3 scripts/reference_amortization_v150.py --out /tmp/v150-cost-evidence.json

# On a host with Rust/Cargo (not executed in this packaging environment):
cargo test --locked
cargo build --release --locked
python3 scripts/native_paired_v150.py \
  --binary ./target/release/supsearch --tasks-dir bench --tasks cnat_add \
  --baseline-library examples/v150_empty.tsv \
  --learned-library examples/v150_empty.tsv \
  --out-dir /tmp/supsearch-v150-pair --max-built 100 --budget 0.05 --max-size 4 --fuel 1000
```

The smoke test intentionally uses identical empty concept libraries; it checks the **comparison mechanism**, not learning. To investigate true transfer, supply a baseline snapshot and a separately learned library, then independently audit how that library was produced, freeze tasks before testing, and run on held-out problem families. The runner never authorizes promotion.

See `docs/V150_NATIVE_PAIRED.md`, `RELEASE_NOTES.md`, and `VALIDATION_V150.json`.

---

# Supsearch v1.4.0 — Executable Reference Transfer Experiment

The v1.4 delta adds a **runnable, independently testable (within this package) Python reference implementation of bounded abstraction learning**: bottom-up synthesis on training examples, candidate mining from repeated solved subexpressions, development-only concept promotion, a negative control, and replayable internal synthetic final testing.

This is **not** execution of the Rust engine. It does **not** independently qualify the Rust learner or prove generalization beyond the author-designed fixture. The bundled source retains the complete v1.3 native Rust implementation and all prior Python evaluation/evidence tooling.

```bash
python3 -m unittest discover -s tests -p 'test_v140.py' -v
python3 scripts/reference_learning_v140.py --out /tmp/supsearch-reference-v140.json
python3 scripts/reference_learning_v140.py --audit /tmp/supsearch-reference-v140.json
# Native compilation remains required when Cargo is installed:
cargo test --locked --offline
python3 scripts/native_gate.py --out /tmp/supsearch-v140-native-gate
```

See [v1.4 technical runbook](docs/V140_REFERENCE_TRANSFER.md), [release notes](RELEASE_NOTES.md), and `VALIDATION_V140.json` for what was actually executed.

---

# Supsearch v1.3.0 — Work-Budgeted Abstraction Learning

This full-source experimental release retains all v1.2 functionality and adds a native per-solve state-expansion cap (`--max-built`), cap-bound evaluation metadata, same-algorithm paired receipt checking, and targeted adversarial validation. The state cap is a resource control, **not** evidence that learning became more effective. **Rust compilation, autonomous mining and independent held-out transfer remain unverified in the packaging environment.**

See [v1.3 qualification protocol](docs/V130_STATE_BUDGET_QUALIFICATION.md) and [release notes](RELEASE_NOTES.md).

---

# Supsearch v1.2.0 — Native Evidence Repair

**Release status: source and Python protocol qualification only. Native Rust tests and actual abstraction-transfer performance remain unverified in this environment.**

This package upgrades v1.1.0 without discarding its original synthesis engine, lessons, experiments, or infrastructure.

## v1.2 additions

1. Every historical native promotion in the journal must match its ordered suffix entry in the concept library, not just the last concept. Original pre-journal baseline entries cannot be attested by this check.
2. Schema-v7 learning sessions end with `session_completed`. An interrupted session, even with zero promotions, fails closed at the next startup. Older schema-v6 records are accepted under their original weaker completion semantics.
3. Materializes empty concept libraries so audit tools can distinguish an empty result from a missing result.
4. Refuses symlink/non-regular existing concept libraries on read.
5. Native smoke gate checks the terminal event and runs the independent Python consistency auditor over the native-produced journal and library.
6. Adds Rust-native unit tests and Python adversarial fixtures for history integrity and interrupted-session states.

## Quick verification

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/native_gate.py --preflight
# On an environment with a pinned Rust toolchain and Cargo:
python scripts/native_gate.py --out /tmp/supsearch-v120-native-gate
```

For detailed risk boundaries and the release's exact validation results, read `docs/V120_NATIVE_HISTORY_QUALIFICATION.md` and `VALIDATION_V120.json`.

---

# Supsearch v1.1.0 — Transaction-Safe Native Learning (Research Source)

**Native Rust changes in this release have not been compiled or executed in the packaging environment.**
The upgraded Python protocol suite passes, but those results do not prove the Rust learner runs,
that mining autonomously discovers transferable abstractions, or that any generalization improvement occurred.

The v1.1 delta addresses one concrete native correctness gap: v1.0 accepted ledger history by
searching raw text for promotion event substrings. That could mistakenly treat malicious notes
or malformed content as a committed operation. v1.1 adds `src/journal.rs` with a strict,
bounded, top-level JSONL reader, a last-commit/library reconciliation check, and an
exclusive single-writer `.jsonl.lock`. It fails closed on orphan commits, duplicate JSON keys,
partial records, invalid JSON literals, missing concepts, and unsafe event sequences.

For independent reviewer use, the package includes a separately executable Python
`journal_preflight_v110.py` with adversarial unit tests. Its results establish only consistency of
locally supplied bytes; they cannot prove source authenticity or that native learning occurred.

The earlier v1.0+ source remains present: original Rust program synthesizer, governed concept
mining and admission, internal paired evaluation, cross-split structural checks, externally held
replay and evidence tools, preregistration, and native-gate scripts. The bundled demonstration
curriculum **is known to leak**, and is not evidence of independent transfer.

## Install and validation

On macOS/Linux with an installed Rust 2021 toolchain:

```sh
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --source . --out /tmp/supsearch-v110-native
```

For a locally generated journal and concept library:

```sh
python3 scripts/journal_preflight_v110.py out/learning/decisions.jsonl out/learning/concepts.tsv
python3 scripts/candidate_lineage_v100.py out/learning/decisions.jsonl --require-native-mined
```

`journal_preflight_v110.py` requires the concept library file to exist, even if empty.
Only launch an experiment from fresh, truly disjoint task sets and with new output paths. A
`.jsonl.lock` remaining after a crash means **inspect the run and its ledger** before manually
removing it. The single-writer lock is cooperative and not a defense against an adversarial user
on the same computer.

For the release blockers and evidence boundaries, see `docs/V110_TRANSACTION_QUALIFICATION.md`.

---

# Supsearch v1.0.0 — Candidate Provenance and Solution Recheck

**Complete Rust research source and evaluation toolkit.** Rust compilation, native
learning campaigns, and independent transfer have **not** been executed in the
packaging environment. This release does not demonstrate general intelligence.

New in this upgrade:

1. `learn --require-native-mined true` rejects imported candidate files.
2. Native mining vs imported candidate origin is recorded on every candidate
   trial and promotion intent. The `schema_version: 6` start event marks new
   native provenance-capable ledgers.
3. Candidate solutions are re-applied to each supplied task example and checked
   for equality of beta-normal forms. Hash equality alone cannot admit them.
4. The native `learn` command checks train/final and dev/final structural example
   overlaps **after concept selection**, before computing final evaluation.
5. `scripts/candidate_lineage_v100.py` verifies trial-to-promotion correspondence,
   origin claims, balanced success counts, commit ordering, and library history.
6. The qualified pipeline enables native-only proposals unless explicit external
   candidates were provided, and checks provenance for v1.0 ledgers.

To use on macOS or Linux with Rust 2021 toolchain installed:

```bash
cargo test --locked
cargo build --release --locked
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --source . --out /tmp/supsearch-native-v100
python3 scripts/qualified_pipeline.py --help
python3 scripts/candidate_lineage_v100.py --help
```

Native-only learning example (choose genuinely disjoint task IDs yourself):

```bash
./target/release/supsearch learn ./bench --train TASK_TRAIN --dev TASK_DEV \
  --rounds 2 --require-native-mined true \
  --library ./out/learning/concepts.tsv --ledger ./out/learning/decisions.jsonl
python3 scripts/candidate_lineage_v100.py ./out/learning/decisions.jsonl \
  --require-native-mined
```

Use a fresh run directory and task files. The bundled `examples/curriculum`
fixture is known to leak and must not be represented as an independent holdout.
The Rust verifier reuses the project's NBE engine, so it is a separate execution
path for finite examples, **not** an independent proof kernel. Candidate origin
is self-reported by local source; external evaluation must control and inspect
artifacts and cannot infer truth from a JSON label alone.

See `docs/V100_NATIVE_LEARNING.md` and `RELEASE_NOTES.md`.

---

> **v0.9.0 update:** Parsed lambda-term leakage screening, paired internal test evidence and preregistered family-breadth transfer gates. See [v0.9 qualification](docs/V09_QUALIFICATION.md). Rust compilation and independent transfer results are **not** verified by this source-only release.

# Supsearch v0.8.0 — Preregistered Transfer Qualification

**Full research source. Native Rust compilation and improvements from autonomous abstraction learning are not verified in this authoring environment.** Adds an evaluator-controlled, family-aware learning-transfer campaign gate, source/learning evidence cross-checks, and an isolated Cargo native qualification path.

Start with [v0.8 release notes](RELEASE_NOTES.md) and [the transfer campaign runbook](docs/TRANSFER_CAMPAIGN_V08.md).

```sh
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --preflight
python3 scripts/native_gate.py --source . --out /tmp/supsearch-native-v08
python3 scripts/create_task_map.py --help
python3 scripts/transfer_campaign.py --help
```

Run `native_gate.py` and the separate evaluator replay on a machine with a Rust compiler. Mock protocol fixtures are NOT benchmark results; the default bundled curriculum is known to leak between train/development/final splits.

---

# Supsearch v0.7.0 — Attested Native Qualification

**Complete experimental Rust synthesizer source, not a production-qualified learning system.** This release adds evaluator-held HMAC evidence sealing, real-native qualification commands and adversarial tests. No native Rust results or independent learning improvements are claimed in this package.

See [v0.7 release notes](RELEASE_NOTES.md) and [execution/attestation runbook](docs/ATTESTED_NATIVE_V07.md).

```sh
python3 -m unittest discover -s tests -q
python3 scripts/check_manifest.py .
python3 scripts/native_gate.py --preflight
python3 scripts/native_gate.py --source . --out /tmp/supsearch-gate-001
```

---

# Supsearch v0.6.0 — External Replay Research Release

**Full Rust synthesizer source plus evaluator-side replay tooling. Native Rust compilation and autonomous learning transfer remain unverified.**

New: `scripts/external_replay.py` verifies previously frozen concept libraries against evaluator-supplied tasks, with single-use registry claims, alternating baseline/upgraded evaluation option, and recomputable evidence. The evaluator cannot promote concepts. See [`docs/EXTERNAL_REPLAY_V06.md`](docs/EXTERNAL_REPLAY_V06.md) and [`RELEASE_NOTES.md`](RELEASE_NOTES.md).

```sh
python3 -m unittest discover -s tests -v
cargo test --locked && cargo build --release --locked
python3 scripts/external_replay.py --help
```

---

# Supsearch — v0.5.0 Evidence-Bound Learning Research Release

**Complete source archive, not a compiled or independently validated learning system.**

Version 0.5 adds defensive JSONL parsing, frozen native-evaluation metadata
checks, append-only concept-library/ledger reconciliation, and an explicitly
*advisory* local result gate. Native result writing now uses a no-clobber
hard-link commit to avoid a check-then-rename overwrite race. Source and tests
are included; Cargo was not available in the authoring environment, so native
compilation and real synthesis results are unverified.

See `RELEASE_NOTES.md` and `docs/EVIDENCE_PROTOCOL_V05.md` for commands,
negative tests, caveats, and reproduction procedure.  The bundled curriculum
contains known cross-split overlaps; the default `audit-splits` command
correctly rejects it.

---

# Supsearch — v0.4.0 Auditable Transfer Research Release

**Start here:** `RELEASE_NOTES.md` and `docs/TRANSFER_QUALIFICATION_V04.md`. This archive preserves the original synthesizer and historical demos. Native compilation and learning performance are not verified by the Python orchestration tests. The included v0.3 multiplication fixture has cross-split overlap and **must not be used as independent final-test evidence**.

To screen that fixture without Rust:

```bash
python3 scripts/qualified_pipeline.py audit-splits --source examples/curriculum \
  --train prod_train2,prod_train3 --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5
```

The expected outcome is rejection. Use `--fixture-mode` only to reproduce a synthetic demonstration with an explicit non-holdout label.

---

# ontogenesis

A λ-calculus synthesizer that invents its own vocabulary.

No decoder. No typed DSL. No hand-picked operations. Raw terms, an oracle, a hash table.

The whole trick, one line: **two terms that behave identically on the tests are the same term.** That behavior-keyed hash table collapses millions of syntactically distinct programs into thousands of distinct ones. That's how a machine grows abstractions instead of memorizing them.

~1,700 lines of Rust. Zero dependencies. No neural network, no new language, no special runtime.

## The loop

1. **Search** — enumerate raw λ-terms bottom-up, dedup by normal-form behavior, verify every winner against the oracle. Final candidates are checked against finite task examples, not universally proved correct.
2. **Mine** — from solved solutions, pull open subterms, abstract them into closed combinators, merge the ones that behave alike. Rank by compression gain. A seed earns its place.
3. **Grow** — solve → mine → inject → repeat. The claim is a cost curve `C(L₀) > C(L₁) > …` on held-out tasks.

## The trick, measured

Give the bank raw λ + one operation (`add`). It invents the rest.

```
ladder →  mul = λa.λb.λc.b(a(c))   square   power   parity   (raw λ + add)
```

None of these were given. These are the textbook Church combinators, found, not handed over.
But *discovering* a behavior and *acquiring* it are different acts. Acquisition is a
measured decision: promote a candidate only if, installed as a Prim, it drops the held-out
quotient-search cost (Δ > 0) — never because its subterm recurs often.

```
candidate       held-out quotient          verdict
mul             a×b×c ✗→17                 ACQUIRE   (frontier gain)
square          x³ already 3 (Δ ≤ 0)       REJECT    (mul covers it)
power           x^(n+1) ✗→16               ACQUIRE   (frontier gain)
mined idiom     a×b×c ✗→✗ (Δ ≤ 0)          REJECT    (recurs, buys nothing)
```

So: **c is a concept for a distribution ⟺ installing c makes reasoning on it cheaper.**
square is discovered but not acquired; the recurring mined idiom is not acquired. mul and
power earn their slots because each unlocks a frontier mul-alone cannot reach.

The collapse is real — but it lives in the **search**, not the seed:

| problem | raw search | after it invents `mul` |
|---|---|---|
| `a×b×c` | 17,270 states | **17** |
| `a×b×c×d` | unsolvable | **99** |

A machine has acquired a concept only when reasoning *through* it is cheaper than re-deriving it. That's the thesis, made concrete.

## Honest fine print

No reference ontology exists to grade seeds against. So a "good seed" means *general*, not *true* — every seed's note says so.

A bad seed can slow search down. Winners are rechecked against the provided finite examples; this cannot guarantee correctness outside them.

Acquisition is counterfactual, not syntactic. A candidate becomes a concept only if, installed as a Prim, it reduces held-out quotient-search cost (Δ > 0). "Occurs often" and "is a textbook combinator" do not earn a slot on their own — `ladder` shows square (discovered, but mul already covers its held-out) and a recurring mined idiom both rejected, while mul and power are acquired for the frontier each unlocks.

The walls are honest too:

- Naive seed injection *widens* search (one run: median cost 0.016s → 0.265s). A size-1 atom seed branches against everything.
- The 9-fold product is a wall no product sub-concept breaks. `ablation` proves it's the composition search, not the value representation — compact semantic keys at full eval budget move nothing. Same columns, identical numbers.
- `diag` measures the composition wall exactly, and the verdict is sharper: the pool is already behaviorally deduped and contains **zero dominated** candidates, so semantic pruning is a no-op here (folds 2–11 give byte-identical baseline vs pruned). fold9 fails at cap 64 because it needs a single distinct intermediate at admission #133, and cap 64 saturates at 104 distinct semantics before it — a genuine width/ordering wall, not redundant representatives.

The real lever is more raw solves → bigger recurring idioms. That's the wall — a scale problem, not a mechanism failure.

## Run it

```sh
cargo build --release
./target/release/supsearch mkbench solutions/round0 bench
./target/release/supsearch bootstrap bench --train ... --holdout ... --rounds 3 --budget 20
./target/release/supsearch ladder    # raw discovers mul/square/power; only mul+power earn acquisition (counterfactual Δ>0), square and the mined idiom are rejected
./target/release/supsearch promote   # it picks mul itself, infers its arity, promotes it
./target/release/supsearch ablation  # why the fold-9 wall isn't the value representation
./target/release/supsearch diag      # provenance: winner ancestry, semantic redundancy, cap64 vs cap512
./target/release/supsearch prune     # decisive: semantic pruning @ cap64 — Outcome B (no-op on this family)
```

`cargo test`: 24 pass.

## Layout

```
src/        live track: bank, bootstrap, nbe, term, parse
src/legacy/ frozen 120/120 engine
bench/      synthesized tasks
legacy/     frozen engine outputs + RESULTS
```

## Legacy

Before this, the engine solved all 120 LamBench tasks — with a hand-built vocabulary: a typed DSL over decoded values, ~70 operations, a λ stdlib. That 9→120 jump is the vocabulary's payoff. This project asks whether the loop above turns the 9 into the vocabulary.

## License

MIT.

---

## Upgrade: governed concept learning (`learn`)

The v0.2 upgrade adds a **separate** research workflow that ranks training-task frontiers, mines or imports closed Lambda candidates, evaluates them counterfactually on a disjoint development split, and promotes at most one candidate per round only if it unlocks new tasks or reduces search work without significant regressions. A separate test split is used only after promotion.

This is distinct from the older `bootstrap` demonstration (which can insert mined seeds without individually measuring cost improvements). Use **`learn`**, not `bootstrap`, when you need the strict candidate admission gate.

```bash
cargo test
python3 -m unittest discover -s tests -v
cargo run --release -- learn examples/curriculum \
  --train prod_train2,prod_train3 \
  --dev prod_dev3,prod_dev4 \
  --test prod_final4,prod_final5 \
  --candidates examples/multiplication.candidates \
  --rounds 2 --budget 0.5 --max-size 13 \
  --top-tasks 1 --max-arity 2
```

The candidate file is a supplied, already-known Church multiplication expression; **do not interpret that fixture as autonomous discovery**. See [docs/RUNBOOK.md](docs/RUNBOOK.md) for fully isolated experiments and [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for architecture, threat model and limitations.


---

## v0.3 — Verified-curriculum research workflow

This release adds a **separate native `evaluate` command** and an **offline-tested qualified experiment runner**. It runs learning without ever providing final-task IDs or final-task directories to the native learning subprocess; freezing, training, final evaluation and verification occur in distinct single-use phases.

The package retains the original Rust program synthesizer, v0.2 governed learning, examples and legacy solutions. It is **source code**, not a precompiled Rust application. The qualification runner is not a cryptographically secure or independently managed evaluator, and no native speedup or autonomous intelligence claim is established by its mocked integration tests.

Read [docs/QUALIFICATION.md](docs/QUALIFICATION.md) before conducting experiments. The reproducibility-critical commands are:

```sh
cargo test && cargo build --release
python3 -m unittest discover -s tests -v
python3 scripts/qualified_pipeline.py --help
```
