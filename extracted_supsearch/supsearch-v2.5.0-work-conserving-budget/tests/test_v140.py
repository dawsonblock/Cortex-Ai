"""Executable reference-learning tests; no assertion here qualifies native Rust."""
from __future__ import annotations
import json
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import reference_learning_v140 as r


class ReferenceLearningV140(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = r.experiment()

    def test_true_mining_from_two_solved_training_tasks(self):
        self.assertEqual(self.report['discovery']['definition'], '(+ v0 v0)')
        self.assertEqual(self.report['discovery']['chosen_source_tasks'],
                         ['train_double_x','train_double_y'])
        self.assertEqual(self.report['discovery']['candidate_count'], 1)
        self.assertTrue(self.report['discovery']['training_all_solved'])

    def test_stable_admission_decision(self):
        self.assertTrue(self.report['promotion']['accepted'])
        self.assertEqual(self.report['promotion']['concept'], '(+ v0 v0)')
        dev = self.report['development']['metrics']
        self.assertEqual(dev['before_solved'], 2)
        self.assertEqual(dev['after_solved'], 2)
        self.assertGreater(dev['paired_shared_work_reduction'], .05)
        self.assertFalse(dev['lost_solved'])
        self.assertFalse(dev['severe_search_regressions'])

    def test_new_final_tasks_unlocked_under_equal_limits(self):
        final = self.report['final']['metrics']
        self.assertEqual(final['before_solved'], 0)
        self.assertEqual(final['after_solved'], 2)
        self.assertEqual(len(final['new_solved']), 2)
        self.assertEqual(self.report['max_size'], 9)
        self.assertEqual(self.report['max_built_per_solve'], 30000)
        self.assertFalse(self.report['independent_external_holdout'])
        self.assertFalse(self.report['native_rust_executed'])

    def test_negative_control_is_rejected(self):
        self.assertEqual(self.report['negative_control']['definition'], 'v0')
        self.assertFalse(self.report['negative_control']['accepted'])

    def test_candidate_definitional_equivalence(self):
        c = r.add(r.var(0),r.var(0))
        self.assertTrue(r.checks_template_definition(c))
        self.assertEqual(r.evaluate(r.Expr('learned', (r.var(0),)), (-11,),c), -22)
        with self.assertRaises(ValueError):
            r.evaluate(r.Expr('learned',(r.var(0),)),(1,),None)

    def test_unsafe_reuse_between_splits_rejected(self):
        bad = r.Task('bad','copied',1,(((2,),4),))
        with self.assertRaisesRegex(ValueError,'cross-split'):
            r.example_leakage({'train':(bad,), 'final':(bad,)})

    def test_training_alone_cannot_force_non_repeating_concept(self):
        task=r.Task.make('single','double',1, lambda x: 2*x, ((1,),(3,),(7,)))
        solve=r.synthesize(task,concept=None,max_size=5,max_built=100)
        concept, evidence=r.mine_from_training((task,), {'single':solve})
        self.assertIsNone(concept)
        self.assertEqual(evidence['candidate_count'],0)

    def test_search_hard_resource_cap(self):
        task=r.fixture()['final'][0]
        got=r.synthesize(task,concept=None,max_size=9,max_built=20)
        self.assertFalse(got.solved)
        self.assertEqual(got.built,20)

    def test_reject_invalid_experiment_options(self):
        for config in ({'max_size':11},{'max_built':0},{'require_gain':2}):
            with self.assertRaises(ValueError):
                r.experiment(**config)

    def test_bytewise_deterministic_replay(self):
        self.assertEqual(r.canonical(r.experiment()),r.canonical(self.report))

    def test_digest_detects_mutations(self):
        envelope=r.seal(copy.deepcopy(self.report))
        self.assertTrue(r.verify_envelope(envelope))
        envelope['result']['promotion']['accepted']=False
        self.assertFalse(r.verify_envelope(envelope))

    def test_cli_write_and_replay(self):
        script=ROOT/'scripts'/'reference_learning_v140.py'
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/'report.json'
            created=subprocess.run([sys.executable,str(script),'--out',str(report)],
                                   capture_output=True,text=True,timeout=20)
            self.assertEqual(created.returncode,0,created.stderr)
            self.assertTrue(report.exists())
            again=subprocess.run([sys.executable,str(script),'--out',str(report)],
                                 capture_output=True,text=True,timeout=20)
            self.assertNotEqual(again.returncode,0)
            audited=subprocess.run([sys.executable,str(script),'--audit',str(report)],
                                   capture_output=True,text=True,timeout=20)
            self.assertEqual(audited.returncode,0,audited.stderr)
            data=json.loads(report.read_text())
            data['result']['final']['metrics']['after_solved']=999
            report.write_text(json.dumps(data))
            bad=subprocess.run([sys.executable,str(script),'--audit',str(report)],
                               capture_output=True,text=True,timeout=20)
            self.assertNotEqual(bad.returncode,0)

    def test_parse_rejects_duplicate_keys(self):
        script=ROOT/'scripts'/'reference_learning_v140.py'
        with tempfile.TemporaryDirectory() as d:
            report=Path(d)/'duplicate.json'
            report.write_text('{"result": {}, "sha256": "x", "sha256": "y"}')
            result=subprocess.run([sys.executable,str(script),'--audit',str(report)],
                                  capture_output=True,text=True,timeout=20)
            self.assertNotEqual(result.returncode,0)
            self.assertIn('duplicate JSON key',result.stderr)


if __name__ == '__main__':
    unittest.main()
