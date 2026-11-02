# Supsearch Learning Controller v0.2 — architecture and boundaries

## What has been implemented

- An additive native Rust `learn` subcommand (no new Cargo dependencies).
- Task split validation that rejects missing, malformed, overlapping, or unsafe IDs.
- A task-frontier priority heuristic with per-family sampling and retry costs.
- Training-only raw Lambda synthesis and recurring-program abstraction mining.
- A closed-expression candidate import format (no eval, scripts, commands or untrusted plugins).
- Counterfactual concept-composition search on a separate development split.
- Native strict admission: no solved-to-unsolved regression, no severe search-state regressions, and either newly solved tasks or meaningful cumulative search savings.
- Composition-arity inference by measuring arities 1 to 5, never by assuming the candidate's syntactic lambda arity.
- Promotion of at most one best candidate per learning round.
- Library persistence and per-run append-only JSONL decision history.
- Final-test evaluation only after promotion is over; no final-test selection inside the controller.
- Structural normal-form verification before concept_solve declares a solution, not hash equality alone.

## Data flow

1. Parse disjoint train/dev/test IDs from existing `.tsk` files.
2. Rank train problems by unsolved frontier, search-state cost and prior attempt count.
3. Run raw Lambda bank on selected training tasks and collect solutions.
4. Mine recurring abstractions; combine with explicitly supplied candidate terms.
5. Evaluate each candidate and inferred composition arity against the current concept library using the dev tasks.
6. Reject regressions; select the highest-value qualified candidate.
7. Record intent, atomically persist the promoted library, record commit.
8. Repeat; use final-test problems only after all selection ends.

## Threat model and known limits

This is experimental research infrastructure, not a secure arbitrary-code sandbox.

- Imported candidates are parsed as pure lambda terms; evaluation is bounded by fuel/search time, but resource exhaustion and memory usage may still occur. Run with OS-level quotas and isolate untrusted inputs.
- Task labels are local experiment definitions. They are NOT independent benchmarks; task creators could encode answer leakage through task design.
- The final test is sealed during a *single run only*. The system cannot stop an operator from repeatedly running and tuning against the same tests.
- The development set is explicitly reused for selection, so it can be overfit; final-test tasks must remain distinct and preferably be authored by another evaluator.
- Search-state counts are one measure of compute, not tokens, joules, training cost, total wall time, or general intelligence.
- `std::collections::hash_map::DefaultHasher` is not a cryptographic audit hash. The JSONL ledger is an audit log only, without signer-backed authenticity or tamper resistance.
- Concept-body semantics are tested on finite task examples. No proof of universal equivalence is claimed.
- The existing concept composition pool cap and search wall remain; no claim of solving fold-nine has been made.
- Promotion intent and library commit are individually persisted, but not jointly transactional. Recovery should check dangling intent events after crashes.
- Runtime depends on the Rust compiler/toolchain and cannot be fully qualified by static source checks alone.
- Previous `bootstrap` remains available as a legacy research path and **does not** use the new strict promotion gate. For gated acquisition, use `learn`.

## Experiment nomenclature

- `local_smoke`: source and CLI operational tests.
- `internal_dev`: repeatedly used for selection; never describe as holdout evidence.
- `local_final_test`: no selection in same run, but still not independently evaluated.
- `external_holdout`: only a third-party frozen suite qualifies, with operator separation and traceable evaluator custody.

## Promotion metric

The controller uses measured `built` counts from concept composition, conditional on a solved task. It first forbids solved-to-unsolved changes or any single solved task that exceeds its allowed regression tolerance by more than two extra states. Of remaining candidates it prioritizes the number of newly solved tasks and then aggregate work saved. This is a heuristic admission rule, not a proof of global benefit.
