"""Synthetic negative tests only; no real Rust execution or learning claims."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from candidate_lineage_v100 import inspect, verify_file


def session(origin='native_mining'):
    first={'event':'start','initial_concepts':1,'train':4,'dev':4,'test':2}
    trial={'event':'candidate_trial','round':0,'term':'λa.a','arity':1,'origin':origin,
           'accepted':True,'new_solved':1,'lost_solved':0,'severe_regressions':0,'improvement':0.3}
    intent={'event':'promotion_intent','round':0,'name':'concept_0002','term':'λa.a','arity':1,
            'origin':origin,'new_solved':1,'lost_solved':0,'severe_regressions':0,'improvement':0.3,
            'baseline_solved':2,'candidate_solved':3}
    commit={'event':'promotion_committed','name':'concept_0002','concept_count':2}
    final={'event':'final_test_paired','base_solved':0,'learned_solved':1,
           'initial_concepts':1,'learned_concepts':2,'internal_test_only':True}
    result={'event':'final_test','task':'sample_final','solved':True,'built':4,'concepts':2}
    return [first,trial,intent,commit,final,result]


class LineageV100(unittest.TestCase):
    def test_positive_local_lineage(self):
        result=inspect(session(),require_native_mined=True,require_final=True)
        self.assertTrue(result['consistent_local_record'])
        self.assertEqual(result['promotions'],1)
        self.assertFalse(result['independent_validation'])
    def test_imported_candidate_rejected_by_mined_only(self):
        with self.assertRaisesRegex(ValueError,'imported'):
            inspect(session('imported_candidate'),require_native_mined=True)
        self.assertFalse(inspect(session('imported_candidate'))['native_mined_promotions_only'])
    def test_missing_trial_rejected(self):
        with self.assertRaisesRegex(ValueError,'matching accepted'):
            inspect([session()[0],*session()[2:]])
    def test_rejected_trial_cannot_promote(self):
        s=session(); s[1]['accepted']=False
        with self.assertRaisesRegex(ValueError,'accepted trial'):
            inspect(s)
    def test_trial_origin_substitution_rejected(self):
        s=session(); s[1]['origin']='imported_candidate'
        with self.assertRaisesRegex(ValueError,'matching accepted'):
            inspect(s)
    def test_trial_regression_disagreement_rejected(self):
        s=session(); s[2]['lost_solved']=1
        with self.assertRaisesRegex(ValueError,'metrics disagree'):
            inspect(s)
    def test_unsafe_extra_promotion_rejected(self):
        s=session(); s.insert(4,s[2].copy())
        with self.assertRaisesRegex(ValueError,'accepted trial|late|nested|invalid'):
            inspect(s)
    def test_crash_between_intent_and_commit_rejected(self):
        with self.assertRaisesRegex(ValueError,'unreconciled'):
            inspect(session()[:3])
    def test_final_before_training_end_rejected(self):
        s=session(); s.append(s[1].copy())
        with self.assertRaisesRegex(ValueError,'trial out of order'):
            inspect(s)
    def test_requires_final_when_requested(self):
        with self.assertRaisesRegex(ValueError,'final test missing'):
            inspect(session()[:4],require_final=True)
    def test_concept_count_mismatch_rejected(self):
        s=session(); s[3]['concept_count']=20
        with self.assertRaisesRegex(ValueError,'concept_count'):
            inspect(s)
    def test_duplicate_json_keys_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger=Path(temp)/'ledger.jsonl'
            ledger.write_text('{"event":"start","initial_concepts":0,"initial_concepts":100}\n')
            with self.assertRaisesRegex(ValueError,'duplicate'):
                verify_file(ledger)
    def test_malformed_json_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            ledger=Path(temp)/'ledger.jsonl'
            ledger.write_text('{broken json}\n')
            with self.assertRaises((ValueError,json.JSONDecodeError)):
                verify_file(ledger)
    def test_original_rust_modifications_present(self):
        root=Path(__file__).resolve().parents[1]
        native=(root/'src/learning.rs').read_text()
        evaluator=(root/'src/evaluation.rs').read_text()
        self.assertIn('reject_cross_split_examples(&train, &test)?;',native)
        self.assertIn('reject_cross_split_examples(&dev, &test)?;',native)
        self.assertIn('solution_matches_examples',native)
        self.assertIn('solution_matches_examples(task, solution, c.fuel)',evaluator)
        self.assertIn('--require-native-mined',native)

if __name__ == '__main__': unittest.main()
