"""v2.3 portfolio accounting tests: reference arithmetic and tamper rejection.

These are Python tests, not native Rust qualification.
"""
from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from search_budget_audit_v230 import audit, composed_cap


def fixture(*, reserve=25, total=100, composed=75, raw=25, cap=75,
            raw_limit=25, kind='raw', complete=True):
    return [
        dict(event='start', schema_version=8, max_built=total,
             raw_reserve_pct=reserve, rounds=1),
        dict(event='train_attempt', round=0, task='x', kind=kind,
             solved=False, built=composed+raw, composed_built=composed,
             raw_built=raw, composed_limit=cap, raw_limit=raw_limit),
        dict(event='session_completed', rounds=1) if complete else
        dict(event='round_work', round=0),
    ]


class PortfolioAuditTests(unittest.TestCase):
    def check(self, rows, expected_error=None):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'native.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in rows), encoding='utf8')
            if expected_error:
                with self.assertRaisesRegex(ValueError, expected_error):
                    audit(path)
            else:
                return audit(path)

    def test_valid_reservation_and_remaining_budget(self):
        x=self.check(fixture())
        self.assertEqual(x['train_attempts_checked'],1)
        self.assertFalse(x['native_executed_independently'])

    def test_no_concepts_retains_full_raw_budget(self):
        self.check(fixture(composed=0, raw=100, cap=0, raw_limit=100))

    def test_legacy_mode_unchanged(self):
        self.check(fixture(reserve=0,composed=100,raw=0,cap=100,raw_limit=0,kind='composed'))

    def test_reserved_budget_enforces_floor(self):
        self.assertEqual(composed_cap(2,95),1)
        self.assertEqual(composed_cap(7,25),5)
        self.assertEqual(composed_cap(100,25),75)

    def test_wrong_composed_cap_fails(self):
        self.check(fixture(cap=80), 'composed cap')

    def test_replay_forgery_exceeding_shared_work_fails(self):
        self.check(fixture(raw=26), 'expansion accounting|budget')

    def test_wrong_remaining_raw_limit_fails(self):
        self.check(fixture(raw_limit=24), 'shared search budget')

    def test_invalid_configuration_fails(self):
        self.check(fixture(reserve=96), 'invalid nonnegative')
        self.check(fixture(total=0), 'reserve requires')

    def test_composed_path_cannot_claim_raw_search(self):
        self.check(fixture(kind='composed'), 'composed accepted')

    def test_incomplete_session_fails(self):
        self.check(fixture(complete=False), 'completed')

    def test_duplicate_json_keys_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'records.jsonl'
            start='{"event":"start","schema_version":8,"max_built":100,"raw_reserve_pct":25}'
            train='{"event":"train_attempt","built":0,"built":1}'
            path.write_text(start+'\n'+train+'\n'+json.dumps({'event':'session_completed'})+'\n')
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'): audit(path)

    def test_missing_terminal_newline_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'records.jsonl'
            path.write_text(''.join(json.dumps(x)+'\n' for x in fixture()).rstrip('\n'))
            with self.assertRaisesRegex(ValueError,'newline'): audit(path)

    def test_source_includes_reserve_option_and_native_math(self):
        learning=(ROOT/'src/learning.rs').read_text()
        self.assertIn('--raw-reserve-pct', learning)
        self.assertIn('crate::search_budget::composed_limit', learning)
        self.assertIn('crate::search_budget::fallback_limit', learning)
        self.assertIn('mod search_budget;', (ROOT/'src/main.rs').read_text())

    def test_cargo_and_lock_package_versions_align(self):
        for path in (ROOT/'Cargo.toml',ROOT/'Cargo.lock'):
            self.assertIn('version = "2.5.0"',path.read_text())

    def test_smoke_gate_runs_v230_audit(self):
        gate=(ROOT/'scripts/native_gate.py').read_text()
        self.assertIn('audit_search_budget(ledger)',gate)
        self.assertIn('v230_search_budget_receipts_reconciled',gate)


if __name__ == '__main__':
    unittest.main()
