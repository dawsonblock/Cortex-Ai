"""v1.3 negative cases exercise evidence behavior using synthetic JSONL.

Passing these Python tests says nothing about Rust compilation or independent transfer.
"""
from pathlib import Path
import json
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from state_budget_audit_v130 import compare_native_reports
from qualified_pipeline import parse_eval


class CappedEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.base=self.root/'base.jsonl'
        self.learned=self.root/'learned.jsonl'
        self.settings={'budget':5.0,'max_size':8,'fuel':1000,'max_built':42}

    def write(self,path,count,built=(12,42),solved=(True,False),cap=42,mode='concept'):
        meta={'event':'evaluation_meta','schema_version':5,'mode':mode,'concept_count':count,
              'task_count':2,'budget':5.0,'max_size':8,'fuel':1000,'max_built':cap}
        rows=[{'event':'evaluation','task':t,'mode':mode,'solved':s,'built':n,
               'kept':0,'aborted':0,'elapsed_secs':0.01} for t,s,n in zip(('a','b'),solved,built)]
        path.write_text(''.join(json.dumps(row)+'\n' for row in (meta,*rows)))

    def compare(self):
        return compare_native_reports(self.base,self.learned,['a','b'],
                                      budget=5,max_size=8,fuel=1000,max_built=42)

    def test_paired_under_equal_caps(self):
        self.write(self.base,0)
        self.write(self.learned,1,(8,30),(True,True))
        result=self.compare()
        self.assertEqual(result['newly_solved'],['b'])
        self.assertEqual(result['baseline_solved'],1)
        self.assertEqual(result['learned_solved'],2)
        self.assertEqual(result['frozen_settings']['max_built'],42)
        self.assertFalse(result['native_execution_verified_by_this_script'])

    def test_rejects_cap_mismatch(self):
        self.write(self.base,0)
        self.write(self.learned,1,cap=0)
        with self.assertRaisesRegex(ValueError,'max_built'):
            self.compare()

    def test_rejects_over_budget_states(self):
        self.write(self.base,0)
        self.write(self.learned,1,(8,43))
        with self.assertRaisesRegex(ValueError,'built count'):
            self.compare()

    def test_rejects_wrong_algorithm(self):
        self.write(self.base,0)
        self.write(self.learned,1,mode='raw')
        with self.assertRaisesRegex(ValueError,'invalid evaluation metadata'):
            self.compare()

    def test_rejects_concept_count_regression(self):
        self.write(self.base,2)
        self.write(self.learned,1)
        with self.assertRaisesRegex(ValueError,'strictly more'):
            self.compare()

    def test_rejects_duplicate_row(self):
        self.write(self.base,0)
        self.write(self.learned,1)
        text=self.learned.read_text().splitlines()
        self.learned.write_text('\n'.join((text[0],text[1],text[1]))+'\n')
        with self.assertRaises(ValueError):
            self.compare()

    def test_rejects_missing_input(self):
        self.write(self.base,0)
        with self.assertRaisesRegex(ValueError,'unsafe, absent'):
            self.compare()

    def test_rejects_unsafe_task_name(self):
        self.write(self.base,0)
        self.write(self.learned,1)
        with self.assertRaisesRegex(ValueError,'unsafe task ID'):
            compare_native_reports(self.base,self.learned,['../t'],**self.settings)

    def test_rejects_same_receipt_as_both_arms(self):
        self.write(self.base,0)
        with self.assertRaisesRegex(ValueError,'distinct'):
            compare_native_reports(self.base,self.base,['a','b'],**self.settings)

    def test_legacy_pipeline_requires_uncapped_if_unfrozen(self):
        self.write(self.base,0)
        old={'budget':5,'max_size':8,'fuel':1000}
        with self.assertRaisesRegex(ValueError,'max_built'):
            parse_eval(self.base,['a','b'],'concept',expected_settings=old)

    def test_accepts_legacy_meta_without_state_cap(self):
        self.write(self.base,0,cap=0)
        old={'budget':5,'max_size':8,'fuel':1000}
        text=self.base.read_text().replace(', "max_built": 0','')
        self.base.write_text(text)
        self.assertEqual(len(parse_eval(self.base,['a','b'],'concept',expected_settings=old)),2)

    def test_rejects_symlink_to_input(self):
        self.write(self.base,0)
        self.learned.symlink_to(self.base)
        with self.assertRaisesRegex(ValueError,'distinct|unsafe'):
            self.compare()

    def test_lexical_static_wiring(self):
        bank=(ROOT/'src/bank.rs').read_text()
        self.assertEqual(bank.count('opts.max_built != 0 && built >= opts.max_built'),3)
        self.assertIn('self.stats.built >= self.opts.max_built',bank)
        self.assertIn('max_built = c.max_built;', (ROOT/'src/learning.rs').read_text())
        self.assertIn('opts.max_built=c.max_built;', (ROOT/'src/evaluation.rs').read_text())


if __name__=='__main__':
    unittest.main()
