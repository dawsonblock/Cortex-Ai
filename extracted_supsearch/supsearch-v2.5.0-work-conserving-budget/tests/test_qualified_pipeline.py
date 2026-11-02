"""Offline qualification-runner tests; not native Rust integration benchmarks."""
import importlib.util
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from qualified_pipeline import main, parse_eval, paired_summary

MOCK = '''#!/usr/bin/env python3
import json, pathlib, sys
args = sys.argv[1:]
def get(flag):return args[args.index(flag)+1]
if args[0] == 'learn':
    assert not any(p.name.startswith('final_') for p in pathlib.Path(args[1]).glob('*.tsk'))
    pathlib.Path(get('--library')).write_text('# learned concept\\nconcept_0001\\t2\\tλa.λb.a(b)\\n')
    events=[{'event':'start'},{'event':'candidate_trial'},
            {'event':'promotion_intent','name':'concept_0001','arity':2,'term':'λa.λb.a(b)'},
            {'event':'promotion_committed','name':'concept_0001','concept_count':1}]
    pathlib.Path(get('--ledger')).write_text(''.join(json.dumps(x)+'\\n' for x in events))
elif args[0] == 'evaluate':
    mode=get('--mode'); library=pathlib.Path(get('--library')).read_text()
    gained = 'concept_0001' in library and mode=='concept'
    t=get('--tasks').split(',')
    lines=[{'event':'evaluation_meta','mode':mode,'task_count':len(t),'concept_count':(1 if 'concept_0001' in library and mode=='concept' else 0),'budget':float(get('--budget')),'max_size':int(get('--max-size')),'fuel':int(get('--fuel'))}]
    for task in t:
        lines.append({'event':'evaluation','mode':mode,'task':task,'solved':gained,
                      'built':5 if gained else 100,'elapsed_secs':0.01})
    pathlib.Path(get('--out')).write_text(''.join(json.dumps(x)+'\\n' for x in lines))
else:raise SystemExit(1)
'''


class QualifiedTests(unittest.TestCase):
    def setUp(self):
        self.t = tempfile.TemporaryDirectory()
        self.addCleanup(self.t.cleanup)
        self.d = Path(self.t.name)
        self.tasks = self.d / 'tasks'
        self.tasks.mkdir()
        for i, name in enumerate(['train_a','train_b','dev_a','final_a','final_b']):
            body = 'f(' * (i + 1) + 'x' + ')' * (i + 1)
            (self.tasks / (name + '.tsk')).write_text(f'example {name}\n---\n@main(λf.λx.{body})\n= λx.x\n')
        self.bin = self.d / 'fake-supsearch'
        self.bin.write_text(MOCK)
        self.bin.chmod(self.bin.stat().st_mode | stat.S_IXUSR)
        self.run = self.d / 'r1'

    def prepare(self, run=None):
        return main(['prepare','--source',str(self.tasks),'--train','train_a,train_b',
                     '--dev','dev_a','--test','final_a,final_b',
                     '--binary',str(self.bin),'--run',str(run or self.run)])

    def test_prepare_separates_sealed_tasks_and_tracks_hashes(self):
        self.assertEqual(self.prepare(),0)
        self.assertEqual(sorted(x.stem for x in (self.run/'learning_tasks').glob('*.tsk')),
                         ['dev_a','train_a','train_b'])
        self.assertEqual(sorted(x.stem for x in (self.run/'sealed_test').glob('*.tsk')),
                         ['final_a','final_b'])
        self.assertEqual(json.loads((self.run/'state.json').read_text())['phase'],'frozen')
        self.assertEqual(self.prepare(),2)

    def test_rejects_cross_split_duplicate_by_content(self):
        (self.tasks/'final_a.tsk').write_bytes((self.tasks/'train_a.tsk').read_bytes())
        self.assertEqual(self.prepare(),2)
        self.assertFalse(self.run.exists())

    def test_rejects_split_overlap(self):
        rc=main(['prepare','--source',str(self.tasks),'--train','train_a',
                 '--dev','train_a','--test','final_a','--binary',str(self.bin),
                 '--run',str(self.run)])
        self.assertEqual(rc,2)

    def test_complete_local_mock_workflow_with_single_use_final(self):
        self.assertEqual(self.prepare(),0)
        self.assertEqual(main(['train','--run',str(self.run)]),0)
        self.assertEqual(main(['verify','--run',str(self.run)]),0)
        self.assertEqual(main(['train','--run',str(self.run)]),2)
        self.assertEqual(main(['evaluate','--run',str(self.run)]),0)
        self.assertEqual(main(['evaluate','--run',str(self.run)]),2)
        self.assertEqual(main(['verify','--run',str(self.run)]),0)
        report=json.loads((self.run/'results'/'report.json').read_text())
        self.assertEqual(len(report['concept_pair']['newly_solved']),2)
        self.assertEqual(len(report['concept_pair']['regressions']),0)
        self.assertEqual(report['status'],'local_final_test_not_independent')

    def test_tampering_with_final_task_is_rejected(self):
        self.assertEqual(self.prepare(),0)
        self.assertEqual(main(['train','--run',str(self.run)]),0)
        (self.run/'sealed_test'/'final_a.tsk').write_text('changed')
        self.assertEqual(main(['evaluate','--run',str(self.run)]),2)

    def test_recomputed_report_blocks_metric_forgery_even_with_updated_digest(self):
        from qualified_pipeline import digest
        self.assertEqual(self.prepare(),0)
        self.assertEqual(main(['train','--run',str(self.run)]),0)
        self.assertEqual(main(['evaluate','--run',str(self.run)]),0)
        report_path=self.run/'results'/'report.json'
        report=json.loads(report_path.read_text())
        report['concept_pair']['baseline_solved']=999
        report_path.write_text(json.dumps(report))
        state_path=self.run/'state.json'
        state=json.loads(state_path.read_text())
        state['report_sha256']=digest(report_path)
        state_path.write_text(json.dumps(state))
        self.assertEqual(main(['verify','--run',str(self.run)]),2)

    def test_modified_binary_blocks_train(self):
        self.assertEqual(self.prepare(),0)
        self.bin.write_text(self.bin.read_text()+'\n# changed\n')
        self.assertEqual(main(['train','--run',str(self.run)]),2)

    def test_invalid_results_rejected(self):
        p=self.d/'bad.jsonl'
        p.write_text(json.dumps({'event':'evaluation_meta','mode':'concept','task_count':1,'concept_count':0})+'\n'+
                     json.dumps({'event':'evaluation','mode':'concept','task':'x',
                                 'solved':'yes','built':5,'elapsed_secs':0})+'\n')
        with self.assertRaisesRegex(ValueError,'invalid metric'):
            parse_eval(p,['x'],'concept')

    def test_reports_regressions_and_paired_cost(self):
        before={'a':{'solved':True,'built':100},'b':{'solved':False,'built':8}}
        after={'a':{'solved':True,'built':50},'b':{'solved':True,'built':30}}
        got=paired_summary(before,after)
        self.assertEqual(got['newly_solved'],['b'])
        self.assertEqual(got['paired_built_improvement_fraction'],0.5)


if __name__=='__main__':unittest.main()
