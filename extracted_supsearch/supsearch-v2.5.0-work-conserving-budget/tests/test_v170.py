"""Tests are Python protocol checks with synthetic event data, not native Rust."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from learning_work_audit_v170 import audit,amortization


def fixture():
    return [
      {'event':'start','schema_version':8,'rounds':1,'dev':2,'train':1,'max_built':1000,'initial_concepts':0},
      {'event':'train_attempt','round':0,'task':'train_x','built':32,'composed_built':12,'raw_built':20},
      {'event':'dev_baseline_work','round':0,'tasks':2,'built':100},
      {'event':'candidate_trial','round':0,'term':'λa.a','origin':'native_mining','arity':1,'built':150},
      {'event':'round_work','round':0,'train_built':32,'dev_baseline_built':100,'dev_trial_built':150,'measured_built':282},
      {'event':'session_completed','concept_count':0,'rounds':1}]

class AuditV170(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.path=Path(temp.name)/'test.jsonl'
    def audit(self, rows):
        self.path.write_text(''.join(json.dumps(row,ensure_ascii=False)+'\n' for row in rows))
        return audit(self.path)
    def test_reconciled_work(self):
        r=self.audit(fixture())
        self.assertEqual(r['accounted_search_expansions_lower_bound'],282)
        self.assertEqual(r['training_built'],32)
        self.assertEqual(r['dev_candidate_trial_built'],150)
        self.assertFalse(r['complete_expansion_cost'])
    def test_rejects_missing_fallback_search_cost(self):
        rows=fixture();rows[1]['built']=20
        with self.assertRaisesRegex(ValueError,'fallback'):self.audit(rows)
    def test_rejects_inflated_work_summary(self):
        rows=fixture();rows[4]['measured_built']=1
        with self.assertRaisesRegex(ValueError,'disagrees'):self.audit(rows)
    def test_rejects_missing_candidate_cost(self):
        rows=fixture();del rows[3]['built']
        with self.assertRaises(ValueError):self.audit(rows)
    def test_rejects_duplicate_round_summary(self):
        rows=fixture();rows.insert(-1,rows[4].copy())
        with self.assertRaises(ValueError):self.audit(rows)
    def test_rejects_missing_summary(self):
        rows=fixture();rows.pop(4)
        with self.assertRaises(ValueError):self.audit(rows)
    def test_rejects_wrong_development_count(self):
        rows=fixture();rows[2]['tasks']=1
        with self.assertRaisesRegex(ValueError,'count'):self.audit(rows)
    def test_rejects_missing_session_close(self):
        with self.assertRaisesRegex(ValueError,'unfinished'):self.audit(fixture()[:-1])
    def test_rejects_non_schema_8(self):
        rows=fixture();rows[0]['schema_version']=7
        with self.assertRaisesRegex(ValueError,'schema-8'):self.audit(rows)
    def test_rejects_duplicate_json_keys(self):
        rows=fixture();self.path.write_text('{"event":"start","event":"start"}\n')
        with self.assertRaisesRegex(ValueError,'duplicate'):audit(self.path)
    def test_rejects_truncated_jsonl(self):
        self.path.write_bytes(b'{"event":"start"}')
        with self.assertRaisesRegex(ValueError,'truncated'):audit(self.path)
    def test_rejects_oversized_train_expansion(self):
        rows=fixture();rows[1].update({'built':2100,'composed_built':1100,'raw_built':1000})
        with self.assertRaises(ValueError):self.audit(rows)
    def test_savings_upper_bound_and_payback(self):
        r=amortization(self.audit(fixture()),500,400,repetitions=2)
        self.assertEqual(r['minimum_repeats_to_recoup_measured_learning_lower_bound'],3)
        self.assertEqual(r['net_search_expansion_savings_upper_bound'],-82)
        self.assertFalse(r['fully_amortized'])
    def test_no_benefit_has_no_break_even(self):
        r=amortization(self.audit(fixture()),100,200)
        self.assertIsNone(r['minimum_repeats_to_recoup_measured_learning_lower_bound'])
        self.assertFalse(r['net_positive_under_current_assumptions_possible'])
    def test_overoptimistic_flag_never_set(self):
        r=amortization(self.audit(fixture()),1000,10,repetitions=100)
        self.assertFalse(r['fully_amortized'])
        self.assertTrue(r['net_positive_under_current_assumptions_possible'])
    def test_rejects_post_terminal_events(self):
        rows=fixture();rows.append({'event':'round_work','round':0})
        with self.assertRaisesRegex(ValueError,'after completed'):self.audit(rows)
    def test_multi_round_consistency(self):
        rows=fixture();rows[0]['rounds']=2;rows.pop()
        rows.extend([{'event':'train_attempt','round':1,'task':'train_x','built':5,'composed_built':0,'raw_built':5},
                     {'event':'dev_baseline_work','round':1,'tasks':2,'built':1},
                     {'event':'round_work','round':1,'train_built':5,'dev_baseline_built':1,'dev_trial_built':0,'measured_built':6},
                     {'event':'session_completed','concept_count':0,'rounds':2}])
        self.assertEqual(self.audit(rows)['accounted_search_expansions_lower_bound'],288)

if __name__=='__main__':unittest.main()
