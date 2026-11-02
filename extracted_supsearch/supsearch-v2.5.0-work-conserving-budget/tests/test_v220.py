"""V2.2 adversarial receipt and configuration checks. Python-only: not Rust tests."""
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from concept_admission_audit_v220 import audit
from test_v190 import receipt


def records(mdl=5, positive=2, min_mdl=3, min_families=2, promotion=True):
    e=receipt(horizon=0,savings=12,with_promotion=promotion)
    e[0].update({'dev':2,'min_mdl_gain':min_mdl,
                 'min_positive_families':min_families})
    e[2]['tasks']=2
    e[3].update({'mdl_gain':mdl,'positive_families':positive})
    if promotion:
        e[4].update({'mdl_gain':mdl,'positive_families':positive})
    return e


class ConceptAdmissionTests(unittest.TestCase):
    def check(self, records_):
        with tempfile.TemporaryDirectory() as temp:
            journal=Path(temp)/'test.jsonl'
            journal.write_text(''.join(json.dumps(x,ensure_ascii=False)+'\n' for x in records_),encoding='utf8')
            return audit(journal)

    def test_promoted_concept_passes_both_optional_gates(self):
        report=self.check(records())
        self.assertEqual(len(report['promotions']),1)
        self.assertFalse(report['independent_corpus_recalculation'])
        self.assertFalse(report['native_binary_execution_confirmed'])

    def test_absent_promotion_is_allowed(self):
        self.assertEqual(self.check(records(promotion=False))['promotions'],[])

    def test_below_mdl_threshold_rejected(self):
        with self.assertRaisesRegex(ValueError,'compression gate'):
            self.check(records(mdl=2))

    def test_below_family_threshold_rejected(self):
        with self.assertRaisesRegex(ValueError,'family gate'):
            self.check(records(positive=1))

    def test_disabled_optional_gates_preserve_baseline(self):
        self.assertEqual(len(self.check(records(mdl=-10,positive=0,min_mdl=0,min_families=0))['promotions']),1)

    def test_trial_tampering_detected(self):
        e=records();e[3]['mdl_gain']=1
        with self.assertRaisesRegex(ValueError,'disagrees'):
            self.check(e)

    def test_family_count_tampering_detected(self):
        e=records();e[3]['positive_families']=0
        with self.assertRaisesRegex(ValueError,'disagrees'):
            self.check(e)

    def test_duplicate_trial_rejected(self):
        e=records();e.insert(4,dict(e[3]))
        with self.assertRaises(ValueError):self.check(e)

    def test_absent_v220_start_parameters_fail_closed(self):
        e=records();del e[0]['min_mdl_gain']
        with self.assertRaisesRegex(ValueError,'missing v2.2'):
            self.check(e)

    def test_impossible_positive_families_rejected(self):
        with self.assertRaisesRegex(ValueError,'invalid nonnegative'):
            self.check(records(positive=3))

    def test_family_threshold_cannot_exceed_development_set(self):
        with self.assertRaisesRegex(ValueError,'exceeds'):
            self.check(records(min_families=3))

    def test_rust_pipeline_uses_optional_gates_before_promotion(self):
        code=(ROOT/'src/learning.rs').read_text()
        assert code.index('cfg.min_mdl_gain == 0') < code.index('if let Some(selected) = best {')
        assert code.index('p.positive_families >= cfg.min_positive_families') < code.index('if let Some(selected) = best {')
        self.assertIn('mod mdl;', (ROOT/'src/main.rs').read_text())
        self.assertIn('positive_development_families',(ROOT/'src/learning.rs').read_text())

    def test_native_gate_runs_new_receipt_auditor(self):
        script=(ROOT/'scripts/native_gate.py').read_text()
        self.assertIn('audit_concept_admission(ledger)',script)
        self.assertIn('v220_concept_admission_receipts_reconciled',script)

    def test_cargo_version_matches_lock(self):
        meta=(ROOT/'Cargo.toml').read_text()
        lock=(ROOT/'Cargo.lock').read_text()
        self.assertIn('version = "2.5.0"',meta)
        self.assertIn('version = "2.5.0"',lock)

if __name__=='__main__': unittest.main()
