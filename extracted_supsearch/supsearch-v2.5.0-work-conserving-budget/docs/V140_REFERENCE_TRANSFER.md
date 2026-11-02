# v1.4: Executable reference learning and admission gate

This release contains **two separate systems**:

1. **The original Supsearch Rust program synthesizer**, incorporating the v1.3 work-budget and v1.2 journal/learning components. Its build and tests still require Cargo. No native Rust execution has been performed in this release environment.
2. **A deliberately small, dependency-free Python reference learner** (`scripts/reference_learning_v140.py`). This is an independently runnable *implementation of the algorithmic idea*, **not** a binding, port, adapter, or qualification test of the native Rust learner.

## Example

```bash
python3 scripts/reference_learning_v140.py --out /tmp/reference-v140.json
python3 scripts/reference_learning_v140.py --audit /tmp/reference-v140.json
python3 -m unittest discover -s tests -p 'test_v140.py' -v
```

Use fresh paths: reports cannot overwrite existing artifacts. Audit verifies the report digest and reruns the entire reference experiment with the declared parameters. Hashes do **not** prove independent authority; an adversary controlling both code and files can generate new hashes.

## Learning algorithm

- Enumerate tiny well-typed arithmetic expression trees over integer variables and addition. Deduplicate candidates by observed value vectors, with an explicit `max_size` and per-solve `max_built` cap.
- Solve two *training* input-output tasks from scratch with `+` and variables only.
- Mine a unary compositional abstraction from a repeated solved subtree, canonicalizing bound-variable position. In this fixture, `double(a) = a+a` is automatically discovered rather than provided as an algorithmic primitive. It only becomes a candidate after training searches have succeeded.
- Validate a candidate's definition under a finite sanity domain. Run the **same** synthesis algorithm with and without the added concept library against development examples. Reject regressions; promote only when developer-frozen acceptance criteria pass.
- Open synthetic final-test tasks only after the promotion decision. Solve under identical size/work caps. Also try an intentionally useless identity concept as a negative control.

## Actual evidence and limits

With max expression size 9 and up to 30,000 enumerated candidate states per task, this bundled fixture normally reports:

- Training: 2/2 solved without prior abstractions.
- Mined template: `(+ v0 v0)` (equivalent to `2*x`), sourced from two solved training programs.
- Development: 2/2 solved in both modes, with a small measured reduction in search effort.
- Synthetic final: baseline 0/2 solved within expression-size cap; learned 2/2 solved.
- Negative control: identity concept **rejected**.

These are **internal demonstrations**: the tasks are known to the fixture author, the arithmetic grammar is deliberately restricted, and both final tasks are in one related weighted-sum family. Structural differences and disjoint individual examples do not guarantee independent test-set custody or evidence of general intelligence. Runtime, memory, and search-state overhead of learning must be measured at the full-campaign level for a serious speedup claim. No neural model, LLM weights, or autonomous general-purpose reasoning is trained.

## Next release blockers

1. Compile the **native Rust** sources with pinned Cargo and run `cargo test --locked --offline`, `cargo build --release --locked --offline` and `scripts/native_gate.py`.
2. On **native** code, verify that the learner itself mines and promotes at least one abstraction and that native paired evaluation improves previously unseen tasks.
3. Freeze unseen tasks and evaluators under independent custody, and use the existing transfer campaign and external replay tools with multiple task families.
4. Track end-to-end cost, negative transfer, and repeated-round stability; avoid selecting against the final evaluation set.
