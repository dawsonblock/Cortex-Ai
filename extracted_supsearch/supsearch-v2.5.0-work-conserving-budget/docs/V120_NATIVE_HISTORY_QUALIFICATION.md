# Supsearch v1.2.0 qualification

## Change rationale

Prior native history verification checked the most recent committed concept only.
Earlier journal-committed concept bodies or their order could be changed in the library
without detection, provided the final concept was intact. In addition, a crash after
writing `start` but before promotion could be mistaken for a clean run.

## New invariant

For first journal session with initial library size `B`, and an ordered sequence of
all committed promotions `P`, require the actual loaded library to have length `B + |P|`
and require that its suffix starting at index `B` equal `P` exactly by name, arity,
and normalized source term. Session `start` counts must agree across restarts.

The original prefix of size `B` remains an **unattested input**. It can be authenticated
only by an independently sealed baseline or external custody, not by this local journal.

## Session completion

Native `learn` now writes schema 7 `start`, finishes the rounds, optionally records a
paired internal test, and writes `session_completed` with the current concept count.
A schema-7 journal without the terminal event must be investigated and must not be
resumed automatically. Removing the terminal event does not count as recovery.
Historical schema-6 journals retain previous compatibility.

## Commands

```bash
python -m unittest discover -s tests -p 'test_*.py'
python scripts/native_gate.py --preflight
# Requires Cargo and an external clean output directory:
python scripts/native_gate.py --out /tmp/supsearch-v120-native-unique
```

## Scientific boundary

Promotion consistency is not a proof that the solver discovered useful abstractions,
that task families are independent, or that improvement is statistically reproducible.
Use the existing preregistered external replay tools for those questions, with native
build and evidence custody independently verified.
