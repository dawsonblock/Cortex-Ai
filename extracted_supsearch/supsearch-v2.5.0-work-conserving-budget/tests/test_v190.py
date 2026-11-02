"""v1.9 native promotion receipt audit: adversarial and positive protocol tests.

Does NOT execute Rust; native unit tests cover integrated source when Cargo exists.
"""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from reuse_promotion_audit_v190 import audit


def receipt(*, horizon=10,savings=12,cost=100,with_promotion=True):
    # train=20 + baseline=30 + trial=50 = 100 candidate expansions
    assert cost == 100
    start={'event':'start','schema_version':8,'train':1,'dev':1,'rounds':1,
           'max_built':1000,'initial_concepts':0,'expected_reuses':horizon}
    events=[start,
            {'event':'train_attempt','round':0,'task':'a','built':20,'composed_built':0,
             'raw_built':20,'solved':True,'kind':'raw'},
            {'event':'dev_baseline_work','round':0,'built':30,'tasks':1},
            {'event':'candidate_trial','round':0,'term':'λa.a','origin':'native_mining',
             'arity':1,'accepted':True,'built':50,'paired_savings':savings}]
    if with_promotion:
        events += [{'event':'promotion_intent','round':0,'name':'concept_0001','term':'λa.a',
                    'origin':'native_mining','arity':1,'paired_savings':savings,
                    'round_measured_acquisition':100,'assumed_reuses':horizon},
                   {'event':'promotion_committed','round':0,'name':'concept_0001','concept_count':1}]
    else:
        events += [{'event':'no_promotion','round':0,'evaluated':1,'corpus':1}]
    events += [{'event':'round_work','round':0,'train_built':20,'dev_baseline_built':30,
               'dev_trial_built':50,'measured_built':100},
              {'event':'session_completed','rounds':1,'concept_count':int(with_promotion)}]
    return events

class ReuseGateTests(unittest.TestCase):
    def run_audit(self, events):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'session.jsonl'
            p.write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in events))
            return audit(p)
    def test_exact_break_even_passes(self):
        result=self.run_audit(receipt(horizon=10,savings=10))
        self.assertEqual(result['promotion_forecasts'][0]['minimum_reuses_lower_bound'],10)
        self.assertFalse(result['full_compute_cost_known'])
    def test_below_break_even_rejected(self):
        with self.assertRaisesRegex(ValueError,'cannot break even'):
            self.run_audit(receipt(horizon=9,savings=10))
    def test_no_savings_rejected(self):
        with self.assertRaisesRegex(ValueError,'no paired savings'):
            self.run_audit(receipt(savings=0))
    def test_negative_savings_rejected(self):
        with self.assertRaisesRegex(ValueError,'no paired savings'):
            self.run_audit(receipt(savings=-30))
    def test_disabled_horizon_preserves_exploratory_promotion(self):
        result=self.run_audit(receipt(horizon=0,savings=-5))
        self.assertIsNone(result['promotion_forecasts'][0]['minimum_reuses_lower_bound'])
    def test_no_promotion_valid(self):
        result=self.run_audit(receipt(horizon=10,with_promotion=False))
        self.assertEqual(result['promotion_forecasts'],[])
    def test_cost_forgery_rejected(self):
        events=receipt();events[4]['round_measured_acquisition']=60
        with self.assertRaisesRegex(ValueError,'does not reconcile'):
            self.run_audit(events)
    def test_horizon_changed_rejected(self):
        events=receipt();events[4]['assumed_reuses']=999
        with self.assertRaisesRegex(ValueError,'changed frozen horizon'):
            self.run_audit(events)
    def test_trial_savings_changed_rejected(self):
        events=receipt();events[3]['paired_savings']=200
        with self.assertRaisesRegex(ValueError,'mismatch trial'):
            self.run_audit(events)
    def test_orphan_intent_rejected(self):
        events=receipt();events[4]['term']='λx.λy.x'
        with self.assertRaisesRegex(ValueError,'not linked'):
            self.run_audit(events)
    def test_ineligible_trial_rejected(self):
        events=receipt();events[3]['accepted']=False
        with self.assertRaisesRegex(ValueError,'not linked'):
            self.run_audit(events)
    def test_duplicate_trial_rejected(self):
        events=receipt();events.insert(4,copy.deepcopy(events[3]))
        # Work accounting also catches doubled work; either way rejection is correct.
        with self.assertRaises(ValueError): self.run_audit(events)
    def test_duplicate_json_key_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.jsonl';lines=[json.dumps(e) for e in receipt()]
            lines[0]=lines[0].replace('"train": 1','"train": 1, "train": 1')
            p.write_text('\n'.join(lines)+'\n')
            with self.assertRaisesRegex(ValueError,'duplicate'):
                audit(p)
    def test_rejects_truncated_receipt(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'a.jsonl';p.write_text(json.dumps(receipt()[0]))
            with self.assertRaisesRegex(ValueError,'truncated'):
                audit(p)
    def test_native_code_wires_gate_before_promotion(self):
        s=(ROOT/'src/learning.rs').read_text()
        assert s.index('let mut best = allowed.next();') < s.index('if let Some(selected) = best {')
        self.assertIn('cfg.expected_reuses',s)
        self.assertIn('pub(crate) struct Forecast',(ROOT/'src/reuse_policy.rs').read_text())
        self.assertIn('paired_savings',(ROOT/'src/learning.rs').read_text())

if __name__=='__main__': unittest.main()
