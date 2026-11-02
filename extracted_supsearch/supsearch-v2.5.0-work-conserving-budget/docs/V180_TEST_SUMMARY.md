# v1.8 qualification summary

- Historical full Python unittest suite: **223 passed**, **198.116 seconds**.
- New v1.8 static protocol/source-wiring tests: **5 passed** (included above).
- New Rust unit tests: **5 added**, not executed.
- Native Rust compilation: **not executed**; no Rust toolchain in this packaging environment.
- Native learning campaign and independent transfer: **not executed**.
- Packaging manifest hashes source bytes and excludes itself. No signature attestation is claimed.

Run the following locally to qualify native code:

```sh
cargo test --locked
cargo build --release --locked
python3 scripts/native_learning_campaign_v170.py --help
```

Even successful compilation would not establish demonstrated learning or independent generalization.
