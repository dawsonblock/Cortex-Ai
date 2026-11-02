"""v0.6 evaluator tests use a MOCK native interface, never real synthesis."""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from qualified_pipeline import main as local
from external_replay import main as external, verify_result
from test_qualified_pipeline import MOCK


def task(term: str) -> str:
    return f'mock task, not a mathematical oracle\n---\n@main({term})\n= λx.x\n'


class ExternalReplayTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.t=self.base/'training'
        self.t.mkdir()
        self.external=self.base/'private-held-out'
        self.external.mkdir()
        for k,v in {'arith_a':'λx.x','graph_b':'λf.f','data_c':'λy.y','list_d':'λz.z'}.items():
            (self.t/f'{k}.tsk').write_text(task(v),encoding='utf8')
        for k,v in {'final_a':'λm.m','final_b':'λn.n'}.items():
            (self.external/f'{k}.tsk').write_text(task(v),encoding='utf8')
        self.binary=self.base/'fake_native'
        self.binary.write_text(MOCK)
        self.binary.chmod(self.binary.stat().st_mode | stat.S_IXUSR)
        self.run=self.base/'training-run'
        self.registry=self.base/'registry'
        self.out=self.base/'external-result'
        self.prepare()

    def prepare(self):
        args=['prepare','--source',str(self.t),'--train','arith_a,graph_b',
              '--dev','data_c,list_d','--test','final_unused','--binary',str(self.binary),
              '--run',str(self.run)]
        # Local pipeline requires a final task name but it will not be used by the
        # separate evaluator. The local test is deliberately not opened on replay.
        (self.t/'final_unused.tsk').write_text(task('λq.q'),encoding='utf8')
        self.assertEqual(local(args),0)
        self.assertEqual(local(['train','--run',str(self.run)]),0)

    def replay(self,*args):
        return external(['evaluate','--run',str(self.run),'--source',str(self.external),
                         '--registry',str(self.registry),'--out',str(self.out),
                         '--tasks','final_a,final_b',*args])

    def test_local_mock_batch_and_verify(self):
        self.assertEqual(self.replay(),0)
        self.assertEqual(external(['verify','--out',str(self.out)]),0)
        r=json.loads((self.out/'report.json').read_text())
        self.assertEqual(r['status'],'evaluator_side_replay_not_automatically_independent')
        self.assertFalse(r['claimed_independent_validation'])
        self.assertEqual(r['concept_pair']['newly_solved'],['final_a','final_b'])
        self.assertEqual(len(list(self.registry.glob('*.consumed'))),1)
        self.assertEqual(self.replay(),2)

    def test_counterbalanced_mock_replay(self):
        self.assertEqual(self.replay('--counterbalanced'),0)
        self.assertEqual(external(['verify','--out',str(self.out)]),0)
        self.assertEqual(len(list((self.out/'results').glob('*.jsonl'))),6)
        self.assertTrue(json.loads((self.out/'report.json').read_text())['counterbalanced'])

    def test_cross_split_leakage_rejected(self):
        (self.external/'final_a.tsk').write_bytes((self.t/'arith_a.tsk').read_bytes())
        self.assertEqual(self.replay(),2)
        self.assertFalse(self.registry.exists())
        self.assertFalse(self.out.exists())

    def test_private_task_tamper_detected(self):
        self.assertEqual(self.replay(),0)
        (self.out/'private_tasks'/'final_a.tsk').write_text('modified')
        with self.assertRaisesRegex(ValueError,'test task modified'):
            verify_result(self.out)

    def test_report_forgery_detected_even_if_receipt_digest_updated(self):
        self.assertEqual(self.replay(),0)
        p=self.out/'report.json'
        r=json.loads(p.read_text()); r['concept_pair']['baseline_solved']=999
        p.write_text(json.dumps(r))
        from qualified_pipeline import digest
        receipt=self.out/'receipt.json'
        q=json.loads(receipt.read_text());q['report_sha256']=digest(p)
        receipt.write_text(json.dumps(q))
        with self.assertRaisesRegex(ValueError,'metrics inconsistent'):
            verify_result(self.out)

    def test_trained_library_tamper_detected(self):
        with (self.run/'inputs'/'working.tsv').open('a') as f:f.write('# tamper\n')
        self.assertEqual(self.replay(),2)
        self.assertFalse(self.out.exists())

    def test_rejects_registry_inside_training_tree(self):
        self.registry=self.run/'registry'
        self.assertEqual(self.replay(),2)
        self.assertFalse(self.registry.exists())

    def test_rejects_reused_task_family(self):
        (self.external/'arith_final.tsk').write_text(task('λv.v'))
        self.assertEqual(external(['evaluate','--run',str(self.run),'--source',str(self.external),
                    '--registry',str(self.registry),'--out',str(self.out),'--tasks','arith_final']),2)
        self.assertFalse(self.out.exists())

    def test_rejects_oversized_external_task(self):
        (self.external/'final_a.tsk').write_text('x'*(2*1024*1024+1))
        self.assertEqual(self.replay(),2)
        self.assertFalse(self.registry.exists())

    def test_rejects_symlink_external_task(self):
        (self.external/'final_a.tsk').unlink()
        (self.external/'final_a.tsk').symlink_to(self.t/'arith_a.tsk')
        self.assertEqual(self.replay(),2)
        self.assertFalse(self.registry.exists())

    def test_rejects_duplicate_test_ids(self):
        self.assertEqual(external(['evaluate','--run',str(self.run),'--source',str(self.external),
                    '--registry',str(self.registry),'--out',str(self.out),'--tasks','final_a,final_a']),2)

if __name__=='__main__':unittest.main()
