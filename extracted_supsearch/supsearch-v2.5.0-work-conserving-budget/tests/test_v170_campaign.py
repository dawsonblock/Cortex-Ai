"""End-to-end protocol smoke with an explicit script test double, never native qualification."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_v160 import FAKE,task

ROOT=Path(__file__).resolve().parents[1]

def double_source():
    s=FAKE.replace('__MODE__',"'normal'")
    s=s.replace("{'event':'start','schema_version':7,'initial_concepts':0}",
                "{'event':'start','schema_version':8,'rounds':1,'train':1,'dev':1,'max_built':1000,'initial_concepts':0}")
    s=s.replace("{'event':'train_attempt','task':'train_x','solved':True,'built':23}",
                "{'event':'train_attempt','round':0,'task':'train_x','solved':True,'built':23,'composed_built':0,'raw_built':23},\n          {'event':'dev_baseline_work','round':0,'built':18,'tasks':1}")
    s=s.replace("'arity':1,'accepted':True}", "'arity':1,'accepted':True,'built':6,'round':0}")
    s=s.replace("    rows += [{'event':'session_completed'",
                "    rows += [{'event':'round_work','round':0,'train_built':23,'dev_baseline_built':18,'dev_trial_built':6,'measured_built':47}]\n    rows += [{'event':'session_completed'")
    s=s.replace("'concept_count':0 if MODE=='nopromote' else 1}",
                "'concept_count':0 if MODE=='nopromote' else 1,'rounds':1}")
    return s

class CampaignV170(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.p=Path(temp.name)
        for directory in ('learning','final'):(self.p/directory).mkdir()
        task(self.p/'learning/train_x.tsk','λa.a')
        task(self.p/'learning/dev_x.tsk','λa.λb.a')
        task(self.p/'final/final_x.tsk','λa.λb.b')
        task(self.p/'final/final_y.tsk','λa.λb.λc.a')
        (self.p/'base.tsv').write_text('# empty\n')
        self.binary=self.p/'double.py';self.binary.write_text(double_source());self.binary.chmod(0o700)
    def run_double(self):
        return subprocess.run([sys.executable,str(ROOT/'scripts/native_learning_campaign_v170.py'),
            '--binary',str(self.binary),'--learn-tasks',str(self.p/'learning'),
            '--final-tasks',str(self.p/'final'),'--baseline-library',str(self.p/'base.tsv'),
            '--out-dir',str(self.p/'out'),'--train','train_x','--dev','dev_x',
            '--final','final_x,final_y','--max-built','1000','--max-size','5',
            '--rounds','1','--allow-script-test-double'],text=True,capture_output=True,timeout=15)
    def test_end_to_end_remains_mock_not_native(self):
        result=self.run_double();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads((self.p/'out/report-v170.json').read_text())
        self.assertEqual(report['measured_search_work']['accounted_search_expansions_lower_bound'],47)
        self.assertEqual(report['qualification_scope'],'test_double_not_native')
        self.assertFalse(report['native_source_execution_verified'])
        self.assertFalse(report['fully_amortized'])
        self.assertEqual(report['amortization']['saved_search_expansions_per_final_batch'],26)
    def test_rejects_undercounted_candidate_trial(self):
        self.binary.write_text(double_source().replace("'measured_built':47", "'measured_built':46"))
        result=self.run_double();self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.p/'out/report-v170.json').exists())
        self.assertIn('disagrees',result.stderr)

if __name__=='__main__':unittest.main()
