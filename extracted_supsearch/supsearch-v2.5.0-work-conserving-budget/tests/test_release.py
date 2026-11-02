"""Offline source/package checks. These do NOT substitute for cargo test."""
import pathlib
import sys
import tempfile
import unittest

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from generate_curriculum import church, task, write_all
from audit_run import audit_events


class FixtureTests(unittest.TestCase):
    def test_church_zero_one(self):
        self.assertEqual(church(0), 'λf.λx.x')
        self.assertEqual(church(1), 'λf.λx.f(x)')

    def test_task_shape_and_example_count(self):
        t = task(3, 1)
        self.assertIn('\n---\n', t)
        self.assertEqual(t.count('@main('), 5)
        self.assertEqual(t.count('\n= '), 5)

    def test_split_fixtures_are_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            ps = write_all(pathlib.Path(d))
            self.assertEqual(len(ps), 6)
            self.assertEqual(len(set(p.stem for p in ps)), 6)
            for p in ps:
                self.assertTrue(p.stat().st_size > 40)

    def test_native_components_present(self):
        main = (ROOT / 'src/main.rs').read_text()
        learning = (ROOT / 'src/learning.rs').read_text()
        bank = (ROOT / 'src/bank.rs').read_text()
        self.assertIn('mod learning;', main)
        self.assertIn('learning::run(&argv[1..])', main)
        self.assertIn('fn compare(before:', learning)
        self.assertIn('fn choose_tasks', learning)
        self.assertIn('fn load_library', learning)
        self.assertIn('fn atomic_write', learning)
        self.assertIn('values_match_targets(&vs, &target, opts.fuel)', bank)
        self.assertIn('values_match_targets(&e.vals, &target, opts.fuel)', bank)

    def test_closed_candidate_example(self):
        example = (ROOT / 'examples/multiplication.candidates').read_text()
        exprs = [ln.strip() for ln in example.splitlines() if ln.strip() and not ln.startswith('//')]
        self.assertEqual(exprs, ['λa.λb.λc.b(a(c))'])


class LedgerTests(unittest.TestCase):
    def setUp(self):
        from audit_run import audit_events
        self.audit = audit_events

    def test_valid_promotion(self):
        import json
        entries = [{'event':'start'}, {'event':'candidate_trial'},
                   {'event':'promotion_intent','name':'c1'},
                   {'event':'promotion_committed','name':'c1'},
                   {'event':'final_test','task':'t1'}]
        result = self.audit(json.dumps(x) for x in entries)
        self.assertTrue(result['consistent'])
        self.assertEqual(result['promotions'],1)

    def test_dangling_intent(self):
        self.assertFalse(self.audit(['{"event":"promotion_intent","name":"x"}'])['consistent'])

    def test_reused_ledger_separate_runs(self):
        import json
        sequence = [{'event':'start'}, {'event':'final_test'},
                    {'event':'start'}, {'event':'promotion_intent', 'name':'c1'},
                    {'event':'promotion_committed','name':'c1'}]
        summary = self.audit(json.dumps(e) for e in sequence)
        self.assertTrue(summary['consistent'])
        self.assertEqual(summary['runs'],2)

    def test_rejects_test_leakage_in_log(self):
        with self.assertRaisesRegex(ValueError,'after final test'):
            self.audit(['{"event":"final_test"}', '{"event":"candidate_trial"}'])


if __name__ == "__main__":
    unittest.main()
