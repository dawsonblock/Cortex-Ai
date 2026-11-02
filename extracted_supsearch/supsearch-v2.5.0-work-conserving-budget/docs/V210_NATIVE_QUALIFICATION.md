# v2.1.0 qualification procedure

## Scope and limitations

The Python release script and mock fixtures cannot establish Rust correctness. Rust must be compiled and run from this exact source. An internal journal is not an authenticated evidence record. Substantial external holdout results require independently administered tasks and independent custody of artifacts.

## Verify

```sh
python3 scripts/check_manifest.py .
python3 -m unittest discover -s tests -p 'test_v210.py' -v
cargo test --locked --offline
cargo build --release --locked --offline
python3 scripts/native_gate.py --source . --out /tmp/supsearch-v210-gate
```

The gate performs a fresh offline Cargo test and release build, checks the executable's format, executes both native evaluation modes, tests state caps, executes the actual learning command, requires schema-8 start and completion records, and checks journal/library consistency. Examine the emitted `qualification.json` and logs; an unsuccessful or missing report means native qualification did not pass. Do not reuse an existing output directory.

## Further research, not a release claim

1. Execute native learning with `--require-native-mined true` and no imported candidates; verify promotion provenance.
2. Freeze a new set of distinct problem families and submit to evaluator external to the training process.
3. Run the original heuristic and adaptive curriculum with identical search/fuel/time budgets and random seeds. Use repeated runs and report non-solves.
4. Include training, development baseline, candidate trials, mining, runtime and memory overhead in resource accounting. Candidate expansions alone are only a lower bound.
5. Inspect lost solves, slower solved tasks, and task-family overlap. Pre-register success criteria and do not tune on the final test.
6. Do not promote model-policy changes autonomously without operator approval and verification.

## Verification conducted in packaging environment

- Targeted Python suites: 55 tests passed (17 v1.7, 5 v1.8, 15 v1.9, 12 v2.0, 6 v2.1).
- Full legacy suite: timed out, no overall pass claimed.
- Rust toolchain: not installed, so native qualification could not run.
