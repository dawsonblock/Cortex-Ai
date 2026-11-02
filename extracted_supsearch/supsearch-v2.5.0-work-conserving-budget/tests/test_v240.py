"""V2.4 ledger-level adversarial cases; NOT an executed native Rust qualification."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from native_reserved_fallback_v240 import (validate_native_probe, run_native_probe,
                                            SEED_NAME, TOTAL, RESERVE)


def records(*, initial=1, reserve=95, kind='raw', cb=1, rb=19, cap=1, raw_limit=19):
    return [
        dict(event='start', schema_version=8, rounds=1,
             initial_concepts=initial, max_built=TOTAL, raw_reserve_pct=reserve),
        dict(event='train_attempt', round=0, task='probe_train', kind=kind,
             built=cb+rb, composed_built=cb, raw_built=rb,
             composed_limit=cap, raw_limit=raw_limit, solved=False),
        dict(event='session_completed', rounds=1, concept_count=initial),
    ]


class NonemptyNativeProbeReceiptTests(unittest.TestCase):
    def verify(self, rows, expected_error=None):
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)
            ledger=directory/'ledger.jsonl'
            library=directory/'library.tsv'
            ledger.write_text(''.join(json.dumps(x)+'\n' for x in rows),encoding='utf8')
            library.write_text(f'{SEED_NAME}\t2\tλa.λb.λc.b(a(c))\n', encoding='utf8')
            if expected_error:
                with self.assertRaisesRegex(ValueError, expected_error):
                    validate_native_probe(ledger,library)
            else:
                return validate_native_probe(ledger,library)

    def test_honest_nonempty_fallback_receipt(self):
        result=self.verify(records())
        self.assertTrue(result['concept_search_executed'])
        self.assertTrue(result['raw_fallback_executed'])
        self.assertEqual(result['shared_built'],TOTAL)

    def test_reject_empty_library_journal(self):
        self.verify(records(initial=0),'preloaded concept')

    def test_reject_no_concept_search(self):
        self.verify(records(cb=0, rb=19, cap=1, raw_limit=20),'positive bounded work')

    def test_reject_no_raw_fallback(self):
        self.verify(records(cb=1, rb=0),'positive bounded work')

    def test_reject_composed_success(self):
        self.verify(records(kind='composed',rb=0),'raw fallback')

    def test_reject_budget_configuration_change(self):
        self.verify(records(reserve=25),'composed cap|frozen budget')

    def test_reject_incorrect_cap(self):
        self.verify(records(cb=1,rb=19,cap=2,raw_limit=19),'composed cap|intended raw budget')

    def test_reject_forced_overbudget_result(self):
        self.verify(records(cb=1,rb=20,cap=1,raw_limit=19),'shared search budget')

    def test_reject_duplicate_json_key(self):
        with tempfile.TemporaryDirectory() as td:
            directory=Path(td)
            ledger=directory/'ledger.jsonl'
            library=directory/'library.tsv'
            s=json.dumps(records()[0]); e=json.dumps(records()[-1])
            ledger.write_text(s+'\n'+ '{"event":"train_attempt","built":4,"built":20}' +'\n'+e+'\n')
            library.write_text(f'{SEED_NAME}\t2\tλa.λb.λc.b(a(c))\n')
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                validate_native_probe(ledger,library)

    def test_reject_non_native_executable_before_invoking(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td); fake=root/'fake.sh'; fake.write_text('#!/bin/sh\nexit 0\n')
            with self.assertRaisesRegex(ValueError,'native Rust executable required'):
                run_native_probe(fake, ROOT, root/'out')

    def test_native_gate_wires_and_checks_real_probe(self):
        gate=(ROOT/'scripts/native_gate.py').read_text()
        self.assertIn('run_native_probe(exe, source, output/', gate)
        self.assertIn('v240_nonempty_library_fallback_native_qualified',gate)
        self.assertIn('native_compiled_smoke_passed',gate)

    def test_fixture_preloads_closed_lambda_combinator(self):
        fixture=(ROOT/'examples/v240_preloaded_library.tsv').read_text()
        self.assertIn(SEED_NAME+'\t2\tλa.λb.λc.b(a(c))',fixture)
        self.assertIn('2.5.0',(ROOT/'Cargo.toml').read_text())
        self.assertIn('2.5.0',(ROOT/'Cargo.lock').read_text())


if __name__ == '__main__':
    unittest.main()
