"""Adversarial checks for the v2.0 event-consistency auditor (no Rust execution)."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from curriculum_audit_v200 import audit

def sample():
    return [
        {'event':'start','schema_version':8,'train':3,'initial_concepts':0,'curriculum_policy':'adaptive'},
        {'event':'curriculum_selection','round':0,'policy':'adaptive','tasks':'add_1,mul_1'},
        {'event':'train_attempt','round':0,'task':'add_1','built':100},
        {'event':'train_attempt','round':0,'task':'mul_1','built':50},
        {'event':'round_work','round':0,'train_built':150},
        {'event':'session_completed','rounds':1,'concept_count':0},
    ]
class CurriculumAuditTests(unittest.TestCase):
    def check(self,rows,raw=None):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'j.jsonl'
            p.write_text(raw if raw is not None else ''.join(json.dumps(r)+'\n' for r in rows))
            return audit(p,{'add_1','mul_1','other_1'})
    def test_positive(self):
        a=self.check(sample())
        self.assertEqual(a['sessions'][0]['attempts'],2)
        self.assertEqual(a['qualified_as'],'internal_ledger_consistency_only')
    def test_duplicate_event_rejected(self):
        r=sample(); r.insert(2,r[1]);
        with self.assertRaisesRegex(ValueError,'duplicate'):self.check(r)
    def test_unknown_task_rejected(self):
        r=sample();r[1]['tasks']='secret_1'
        with self.assertRaisesRegex(ValueError,'unknown'):self.check(r)
    def test_wrong_attempt_order_rejected(self):
        r=sample();r[2]['task']='mul_1'
        with self.assertRaisesRegex(ValueError,'order'):self.check(r)
    def test_missing_attempt_rejected(self):
        r=sample();r.pop(3)
        with self.assertRaisesRegex(ValueError,'missing'):self.check(r)
    def test_incomplete_rejected(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):self.check(sample()[:-1])
    def test_mismatched_policy_rejected(self):
        r=sample();r[1]['policy']='heuristic'
        with self.assertRaisesRegex(ValueError,'policy'):self.check(r)
    def test_duplicate_json_keys_rejected(self):
        r=sample();raw='{"event":"start","event":"start"}\n'+''.join(json.dumps(x)+'\n' for x in r[1:])
        with self.assertRaisesRegex(ValueError,'duplicate JSON'):self.check(r,raw)
    def test_missing_newline_rejected(self):
        with self.assertRaisesRegex(ValueError,'newline'):self.check(sample(),'{}')
    def test_family_limit_rejected(self):
        r=sample(); r[1]['tasks']='add_1,add_1,add_1'
        with self.assertRaisesRegex(ValueError,'duplicate'):self.check(r)
    def test_training_outside_session_rejected(self):
        r=sample();r.append({'event':'train_attempt','round':0,'task':'add_1','built':2})
        with self.assertRaisesRegex(ValueError,'outside'):self.check(r)
    def test_task_count_rejected(self):
        r=sample();r[0]['train']=4
        with self.assertRaisesRegex(ValueError,'count'):self.check(r)
if __name__=='__main__':unittest.main()
