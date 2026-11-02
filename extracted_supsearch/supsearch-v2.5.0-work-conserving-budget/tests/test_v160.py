"""Protocol tests for v1.6. All executable fixtures are Python doubles, NOT Rust."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import native_learning_campaign_v160 as campaign
from task_custody import canonical_examples

FAKE='''#!/usr/bin/env python3
import json,pathlib,sys
MODE=__MODE__
a=sys.argv
if a[1]=='learn':
    tdir=pathlib.Path(a[2])
    lib=pathlib.Path(a[a.index('--library')+1])
    ledger=pathlib.Path(a[a.index('--ledger')+1])
    if MODE=='fail': sys.exit(4)
    if MODE=='tamper': (tdir/'train_x.tsk').write_text('malicious change')
    if MODE != 'nopromote':
        lib.write_text('# empty\\nconcept_0001\\t1\\tλa.a\\n')
    rows=[{'event':'start','schema_version':7,'initial_concepts':0},
          {'event':'train_attempt','task':'train_x','solved':True,'built':23}]
    if MODE != 'nopromote':
        rows += [{'event':'candidate_trial','round':0,'term':'λa.a','origin':'native_mining','arity':1,'accepted':True},
                 {'event':'promotion_intent','name':'concept_0001','term':'λa.a','arity':1,'origin':'imported_candidate' if MODE=='imported' else 'native_mining'},
                 {'event':'promotion_committed','name':'concept_0001','concept_count':1}]
    rows += [{'event':'session_completed','concept_count':0 if MODE=='nopromote' else 1}]
    if MODE=='malformed':rows[1]={'event':'promotion_committed','name':'bad','concept_count':1}
    ledger.write_text(''.join(json.dumps(r)+'\\n' for r in rows))
    sys.exit(0)
if a[1]=='evaluate':
    out=pathlib.Path(a[a.index('--out')+1])
    final=a[a.index('--tasks')+1].split(',')
    learned='learn' in str(a[a.index('--library')+1])
    meta={'event':'evaluation_meta','schema_version':5,'mode':'concept','concept_count':int(learned and MODE!='nopromote'),
        'task_count':len(final),'budget':float(a[a.index('--budget')+1]),'max_size':int(a[a.index('--max-size')+1]),
        'fuel':int(a[a.index('--fuel')+1]),'max_built':int(a[a.index('--max-built')+1])}
    rows=[{'event':'evaluation','task':name,'mode':'concept','solved':learned or i==0,
           'built':5 if learned else 18,'kept':3,'aborted':False,'elapsed_secs':0.001}
           for i,name in enumerate(final)]
    out.write_text(''.join(json.dumps(r)+'\\n' for r in [meta,*rows]))
    sys.exit(0)
sys.exit(2)
'''

def task(path: Path, input_expr: str):
    path.write_text('synthetic task\n---\n@main('+input_expr+')\n= '+input_expr+'\n', encoding='utf8')

class NativeLearningCampaignV160(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.training=self.root/'learner';self.training.mkdir()
        self.final=self.root/'final';self.final.mkdir()
        task(self.training/'train_x.tsk','λa.a')
        task(self.training/'dev_x.tsk','λa.λb.a')
        task(self.final/'final_x.tsk','λa.λb.b')
        task(self.final/'final_y.tsk','λa.λb.λc.a')
        self.base=self.root/'empty.tsv';self.base.write_text('# empty\n')
        self.fake=self.root/'test_double.py'
        self.set_mode('normal')
    def set_mode(self, mode):
        self.fake.write_text(FAKE.replace('__MODE__',repr(mode)),encoding='utf8')
        self.fake.chmod(0o700)
    def arguments(self):
        return ['--binary',str(self.fake),'--learn-tasks',str(self.training),
                '--final-tasks',str(self.final),'--baseline-library',str(self.base),
                '--out-dir',str(self.root/'evidence'),'--train','train_x',
                '--dev','dev_x','--final','final_x,final_y','--max-built','1000',
                '--max-size','5','--rounds','1','--allow-script-test-double']
    def parse(self, args=None):
        import argparse
        # Exact CLI option parser; subprocess not needed for each negative test.
        import subprocess
        process=subprocess.run([sys.executable,str(ROOT/'scripts/native_learning_campaign_v160.py'),
             *(args if args is not None else self.arguments())],text=True,capture_output=True,timeout=15)
        return process
    def test_real_bench_task_format_supported_for_leakage_screen(self):
        examples=canonical_examples(ROOT/'bench/cnat_mul.tsk')
        self.assertEqual(len(examples),1)
        self.assertIn('@main',examples[0])
    def test_completed_double_is_explicitly_unqualified(self):
        result=self.parse();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads((self.root/'evidence/report.json').read_text())
        self.assertEqual(report['qualification_scope'],'test_double_not_native')
        self.assertFalse(report['native_learning_executed'])
        self.assertFalse(report['autonomous_concept_promoted'])
        self.assertFalse(report['transfer_improvement_demonstrated'])
        self.assertFalse(report['rust_source_build_verified'])
        self.assertEqual(report['lineage']['training_built_lower_bound'],23)
        self.assertEqual(report['work_accounting']['final_built_all_baseline'],36)
        self.assertEqual(report['work_accounting']['final_built_all_learned'],10)
        self.assertTrue(report['paired_screen_passed'])
        self.assertEqual(report['journal_audit']['commits'],1)
    def test_non_native_default_rejected(self):
        result=self.parse(self.arguments()[:-1]);self.assertNotEqual(result.returncode,0)
        self.assertIn('not a native executable',result.stderr)
        self.assertFalse((self.root/'evidence').exists())
    def test_no_promotions_cannot_qualify(self):
        self.set_mode('nopromote')
        result=self.parse();self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads((self.root/'evidence/report.json').read_text())
        self.assertEqual(report['journal_audit']['commits'],0)
        self.assertFalse(report['autonomous_concept_promoted'])
    def test_imported_promotion_rejected(self):
        self.set_mode('imported')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('non-native candidate',result.stderr)
    def test_invalid_journal_rejected(self):
        self.set_mode('malformed')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('commit',result.stderr.lower())
        self.assertFalse((self.root/'evidence/report.json').exists())
    def test_native_learning_failure_no_final_evaluation(self):
        self.set_mode('fail')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'evidence/paired').exists())
    def test_modification_of_source_task_rejected(self):
        self.set_mode('tamper')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('modified during learning',result.stderr)
    def test_cross_split_train_dev_leakage(self):
        task(self.training/'dev_x.tsk','λa.a')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('example leakage',result.stderr)
        self.assertFalse((self.root/'evidence').exists())
    def test_cross_split_final_leakage(self):
        task(self.final/'final_x.tsk','λa.a')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('example leakage',result.stderr)
    def test_same_family_prefix_on_final_rejected(self):
        (self.final/'train_other.tsk').write_text((self.final/'final_y.tsk').read_text())
        args=self.arguments();args[args.index('--final')+1]='final_x,train_other'
        result=self.parse(args);self.assertNotEqual(result.returncode,0)
        self.assertIn('task-family',result.stderr)
    def test_symlink_final_rejected(self):
        (self.final/'final_x.tsk').unlink()
        (self.final/'final_x.tsk').symlink_to(self.training/'train_x.tsk')
        result=self.parse();self.assertNotEqual(result.returncode,0)
        self.assertIn('symlinked',result.stderr)
    def test_output_inside_task_dir_rejected(self):
        args=self.arguments();args[args.index('--out-dir')+1]=str(self.training/'outputs')
        result=self.parse(args);self.assertNotEqual(result.returncode,0)
        self.assertIn('overlap',result.stderr)
    def test_existing_evidence_no_overwrite(self):
        first=self.parse();self.assertEqual(first.returncode,0,first.stderr)
        b=(self.root/'evidence/report.json').read_bytes()
        second=self.parse();self.assertNotEqual(second.returncode,0)
        self.assertEqual((self.root/'evidence/report.json').read_bytes(),b)
    def test_disallow_duplicate_task_ids(self):
        args=self.arguments();args[args.index('--final')+1]='final_x,final_x'
        result=self.parse(args);self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'evidence').exists())
    def test_disallow_unbounded_state_budget(self):
        args=self.arguments();args[args.index('--max-built')+1]='0'
        result=self.parse(args);self.assertNotEqual(result.returncode,0)
        self.assertFalse((self.root/'evidence').exists())

if __name__=='__main__': unittest.main()
