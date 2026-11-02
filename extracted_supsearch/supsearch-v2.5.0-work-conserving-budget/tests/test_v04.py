"""v0.4 protocol tests. Most are pure stdlib and deliberately do not claim native validation."""
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest
from contextlib import contextmanager

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from task_custody import canonical_examples, scan_splits, assess_custody
from paired_statistics import exact_mcnemar, paired_bootstrap_success_ci, paired_work_geometric_ratio
from qualified_pipeline import main, parse_eval, exclusive_run


def sample(expr: str, *, header: str = 'fixture', second: str = '= λx.x') -> str:
    return f'{header}\n---\n@main({expr})\n{second}\n'


class LeakageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)

    def path(self, name, content):
        dest = self.dir/(name+'.tsk')
        dest.write_text(content, encoding='utf8')
        return dest

    def test_ignores_header_and_whitespace(self):
        a = self.path('train', sample('λx.x', header='First name'))
        b = self.path('test', sample('λx.x', header='Different header'))
        self.assertEqual(canonical_examples(a), canonical_examples(b))
        report = scan_splits({'train':a,'test':b}, {'train':'train','test':'test'})
        self.assertEqual(len(report['cross_split_example_overlaps']), 1)
        with self.assertRaisesRegex(ValueError, 'cross-split example leakage'):
            assess_custody(report, fixture_mode=False, require_family_disjoint=False)
        self.assertEqual(assess_custody(report, fixture_mode=True, require_family_disjoint=False),
                         'synthetic_fixture_not_holdout')

    def test_partial_example_leakage(self):
        a=self.path('train', sample('λx.x'))
        b=self.path('test', sample('λx.x')+'@main(λf.f)\n= λf.f\n')
        result=scan_splits({'train':a,'test':b},{'train':'train','test':'test'})
        self.assertEqual(result['cross_split_example_overlaps'][0]['shared_example_count'],1)
        self.assertFalse(result['cross_split_example_overlaps'][0]['identical_example_sets'])

    def test_rejects_malformed_task(self):
        p=self.path('bad', 'missing separator\n@main(x)\n= x\n')
        with self.assertRaisesRegex(ValueError, 'delimiter'):
            canonical_examples(p)

    def test_rejects_family_overlap_strict(self):
        a=self.path('arith_train', sample('λx.x'))
        b=self.path('arith_test', sample('λx.λy.y'))
        s=scan_splits({'arith_train':a,'arith_test':b}, {'arith_train':'train','arith_test':'test'})
        self.assertEqual(s['cross_split_id_families'], ['arith'])
        self.assertEqual(s['cross_split_example_overlaps'], [])
        with self.assertRaisesRegex(ValueError, 'task-family overlap'):
            assess_custody(s, fixture_mode=False, require_family_disjoint=True)

    def test_original_demo_has_leakage(self):
        path=ROOT/'examples/curriculum'
        names=['prod_train2','prod_train3','prod_dev3','prod_dev4','prod_final4','prod_final5']
        files={name:path/(name+'.tsk') for name in names}
        splits={name:('train' if 'train' in name else 'dev' if 'dev' in name else 'test') for name in names}
        s=scan_splits(files,splits)
        exact=[(x['left'],x['right']) for x in s['cross_split_example_overlaps'] if x['identical_example_sets']]
        self.assertIn(('prod_dev3','prod_train3'),exact)
        self.assertIn(('prod_dev4','prod_final4'),exact)

    def test_audit_splits_subcommand_fails_and_fixture_mode_passes(self):
        args=['audit-splits','--source',str(ROOT/'examples/curriculum'),
              '--train','prod_train2,prod_train3','--dev','prod_dev3,prod_dev4',
              '--test','prod_final4,prod_final5']
        self.assertEqual(main(args),2)
        self.assertEqual(main(args+['--fixture-mode']),0)


class PairedStatsTests(unittest.TestCase):
    def test_exact_mcnemar(self):
        self.assertEqual(exact_mcnemar(0,0),1.0)
        self.assertEqual(exact_mcnemar(1,1),1.0)
        self.assertEqual(exact_mcnemar(4,0),0.125)
        self.assertEqual(exact_mcnemar(0,4),0.125)
        with self.assertRaises(ValueError):exact_mcnemar(-1, 0)

    def test_work_ratio(self):
        a={'x':{'solved':True,'built':100},'y':{'solved':True,'built':20},'z':{'solved':False,'built':5}}
        b={'x':{'solved':True,'built':50},'y':{'solved':True,'built':10},'z':{'solved':True,'built':5}}
        self.assertAlmostEqual(paired_work_geometric_ratio(a,b),0.5)
        ci=paired_bootstrap_success_ci(a,b)
        self.assertEqual(len(ci),2)
        self.assertGreaterEqual(ci[0],0)
        self.assertLessEqual(ci[1],1)
        self.assertEqual(paired_bootstrap_success_ci(a,b),ci)
        self.assertIsNone(paired_work_geometric_ratio({'x':{'solved':False,'built':1}}, b))

    def test_nonfinite_and_wrong_metadata_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'data.jsonl'
            def write(meta, row):
                p.write_text(json.dumps(meta)+'\n'+json.dumps(row)+'\n')
            meta={'event':'evaluation_meta','mode':'concept','task_count':1,'concept_count':0}
            row={'event':'evaluation','mode':'concept','task':'x','solved':True,'built':10,'elapsed_secs':0.1}
            write(meta,{**row,'elapsed_secs':float('nan')})
            with self.assertRaisesRegex(ValueError, 'non-finite|invalid metric'):
                parse_eval(p,['x'],'concept')
            write({**meta,'concept_count':-1},row)
            with self.assertRaisesRegex(ValueError, 'concept_count'):
                parse_eval(p,['x'],'concept')
            write(meta,{**row,'built':True})
            with self.assertRaisesRegex(ValueError, 'non-finite|invalid metric'):
                parse_eval(p,['x'],'concept')

    def test_run_lock_is_exclusive(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)
            with exclusive_run(path):
                with self.assertRaisesRegex(ValueError, 'locked'):
                    with exclusive_run(path):pass
            self.assertFalse((path/'OPERATION_IN_PROGRESS.lock').exists())


if __name__=='__main__': unittest.main()
