"""Static source regressions for v1.8; NOT a substitute for cargo test."""
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
class NativeFallbackSourceChecks(unittest.TestCase):
    def setUp(self): self.src=(ROOT/'src/learning.rs').read_text()
    def test_invalid_some_is_covered_by_fallback(self):
        self.assertIn('if let Some(program) = composed',self.src)
        self.assertIn('let outcome = raw_solver();',self.src)
        self.assertIn('verified_or_raw_fallback(',self.src)
        self.assertNotIn('match composed_solution {',self.src)
    def test_counts_composed_and_raw_work(self):
        self.assertIn('composed_built.saturating_add(raw_built)', self.src)
        self.assertIn('"raw_built":',self.src.replace('\\"','"'))
    def test_rechecks_both_results(self):
        self.assertIn('if solution_matches_examples(task, &program, fuel)',self.src)
        self.assertIn('outcome.solution.filter(|program| solution_matches_examples(task, program, fuel))',self.src)
    def test_native_regression_tests_present(self):
        for name in ('invalid_composed_candidate_falls_back_to_raw',
                     'valid_composed_candidate_skips_raw',
                     'missing_composed_candidate_falls_back_to_raw',
                     'invalid_raw_candidate_not_entered_into_learning_corpus'):
            self.assertIn('fn '+name+'()',self.src)
    def test_candidate_input_refuses_symlinks(self):
        body=self.src.split('fn load_candidate_file(',1)[1].split('pub(crate) fn load_library',1)[0]
        self.assertIn('fs::symlink_metadata(path)',body)
        self.assertIn('file.take(2 * 1024 * 1024 + 1)',body)
if __name__=='__main__':unittest.main()
