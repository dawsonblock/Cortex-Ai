"""Tests for same-algorithm paired Rust evaluation interface; mock cannot qualify Rust."""
from __future__ import annotations
import json
import sys
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import native_paired_v150 as n
import reference_amortization_v150 as a

FAKE='''#!/usr/bin/env python3
import json,sys,pathlib
x=sys.argv
assert x[1]=='evaluate' and x[x.index('--mode')+1]=='concept'
name=pathlib.Path(x[x.index('--library')+1]).name
out=pathlib.Path(x[x.index('--out')+1])
ids=x[x.index('--tasks')+1].split(',')
meta={'event':'evaluation_meta','schema_version':5,'mode':'concept','concept_count':int(name.startswith('learned')),'task_count':len(ids),'budget':float(x[x.index('--budget')+1]),'max_size':int(x[x.index('--max-size')+1]),'fuel':int(x[x.index('--fuel')+1]),'max_built':int(x[x.index('--max-built')+1])}
rows=[]
for i,id in enumerate(ids):
  solved=(i==0 or name.startswith('learned'))
  rows.append({'event':'evaluation','task':id,'mode':'concept','solved':solved,'built':10 if name.startswith('learned') else 20,'kept':4,'aborted':False,'elapsed_secs':0.01})
with out.open('x') as f:
 for item in [meta,*rows]: f.write(json.dumps(item)+'\\n')
'''

class PairedEvaluationV150(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.tasks=self.root/'tasks';self.tasks.mkdir()
        for name in ('a','b'):(self.tasks/(name+'.tsk')).write_text('fixture')
        self.base=self.root/'empty.tsv';self.base.write_text('# empty concept library\n')
        self.learned=self.root/'learned.tsv';self.learned.write_text('c0\t1\tλa.a\n')
        self.fake=self.root/'fake.py';self.fake.write_text(FAKE);self.fake.chmod(0o700)
        self.out=self.root/'out'
    def args(self):
        return ['--binary',str(self.fake),'--tasks-dir',str(self.tasks),
                '--tasks','a,b','--baseline-library',str(self.base),
                '--learned-library',str(self.learned),'--out-dir',str(self.out),
                '--max-built','100','--allow-script-test-double']
    def test_test_double_not_mislabeled_as_native(self):
        p=subprocess.run([sys.executable,str(ROOT/'scripts/native_paired_v150.py'),*self.args()],capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        report=json.loads((self.out/'report.json').read_text())
        self.assertEqual(report['qualification_scope'],'test_double_not_native')
        self.assertFalse(report['native_binary_format_detected'])
        self.assertFalse(report['independent_holdout'])
        self.assertEqual(report['solver_algorithm_both_arms'],'concept_solve')
        self.assertEqual(report['metrics']['newly_solved'],['b'])
        self.assertTrue(report['metrics']['local_screen_passed'])
    def test_fail_closed_script_without_opt_in(self):
        bad=self.args()[:-1]
        p=subprocess.run([sys.executable,str(ROOT/'scripts/native_paired_v150.py'),*bad],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn('not a native executable',p.stderr)
        self.assertFalse(self.out.exists())
    def test_reject_duplicate_ids_and_task_output_overlap(self):
        args=self.args();args[args.index('--tasks')+1]='a,a'
        p=subprocess.run([sys.executable,str(ROOT/'scripts/native_paired_v150.py'),*args],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        args=self.args();args[args.index('--out-dir')+1]=str(self.tasks/'reports')
        p=subprocess.run([sys.executable,str(ROOT/'scripts/native_paired_v150.py'),*args],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
    def test_refuse_symlinked_library(self):
        linked=self.root/"linked.tsv"
        linked.symlink_to(self.base)
        args=self.args();args[args.index("--baseline-library")+1]=str(linked)
        p=subprocess.run([sys.executable,str(ROOT/"scripts/native_paired_v150.py"),*args],capture_output=True,text=True,timeout=10)
        self.assertNotEqual(p.returncode,0)
        self.assertIn("symlinked",p.stderr)

    def test_double_run_no_overwrite(self):
        cmd=[sys.executable,str(ROOT/'scripts/native_paired_v150.py'),*self.args()]
        self.assertEqual(subprocess.run(cmd,capture_output=True,timeout=10).returncode,0)
        report=(self.out/'report.json').read_bytes()
        self.assertNotEqual(subprocess.run(cmd,capture_output=True,timeout=10).returncode,0)
        self.assertEqual((self.out/'report.json').read_bytes(),report)
    def test_strict_result_parser(self):
        config={'budget':1.0,'max_size':13,'fuel':20000,'max_built':100}
        path=self.root/'results.jsonl'
        header={'event':'evaluation_meta','schema_version':5,'mode':'concept','concept_count':0,'task_count':1,**config}
        row={'event':'evaluation','task':'a','mode':'concept','solved':True,'built':3,'kept':1,'aborted':False,'elapsed_secs':.01}
        path.write_text(json.dumps(header)+'\n'+json.dumps(row)+'\n')
        self.assertEqual(n.parse_jsonl(path,task_ids=['a'],config=config,arm='baseline')['rows']['a'],row)
        path.write_text(json.dumps(header)+'\n'+json.dumps({**row,'built':101})+'\n')
        with self.assertRaisesRegex(ValueError,'invalid work count'):
            n.parse_jsonl(path,task_ids=['a'],config=config,arm='baseline')
        path.write_text(json.dumps(header)+'\n'+json.dumps(row)[:-1]+',"built":2}\n')
        with self.assertRaisesRegex(ValueError,'duplicate'):
            n.parse_jsonl(path,task_ids=['a'],config=config,arm='baseline')
    def test_learned_regressions_fail_screen(self):
        base={'rows':{'a':{'solved':True,'built':5},'b':{'solved':True,'built':5}}}
        worse={'rows':{'a':{'solved':False,'built':20},'b':{'solved':True,'built':30}}}
        self.assertFalse(n.compare(base,worse,.15,.05)['local_screen_passed'])
    def test_reference_full_work_accounting(self):
        r=a.evaluate_cost()
        self.assertTrue(r['final_new_solved']>0)
        self.assertEqual(r['final_total_work_baseline'],366)
        self.assertEqual(r['final_total_work_learned'],450)
        self.assertLess(r['final_all_task_work_delta'],0)
        self.assertFalse(r['native_rust_executed'])
        self.assertFalse(r['independent_holdout'])

if __name__=='__main__':unittest.main()
