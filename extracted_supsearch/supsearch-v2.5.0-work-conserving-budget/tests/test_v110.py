"""Protocol regression tests for v1.1's independently executable local audit."""
import importlib.util
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'journal_preflight_v110.py'
spec = importlib.util.spec_from_file_location('journal_preflight_v110', SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class JournalTest(unittest.TestCase):
    START = '{"event":"start","initial_concepts":0}\n'
    INTENT = '{"event":"promotion_intent","name":"concept_0001","term":"λa.a","arity":1}\n'
    COMMIT = '{"event":"promotion_committed","name":"concept_0001","concept_count":1}\n'

    def run_case(self, text, concepts='', good=False):
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            ledger, library = d / 'journal.jsonl', d / 'library.tsv'
            ledger.write_text(text, encoding='utf8')
            library.write_text(concepts, encoding='utf8')
            if good:
                return mod.audit(ledger, library)
            with self.assertRaises((ValueError, UnicodeError)):
                mod.audit(ledger, library)

    def test_valid_empty_session(self):
        self.assertEqual(self.run_case(self.START, good=True)['commits'], 0)

    def test_valid_commit(self):
        result = self.run_case(self.START+self.INTENT+self.COMMIT,
                               'concept_0001\t1\tλa.a\n', good=True)
        self.assertEqual(result['concept_count'], 1)

    def test_rejects_pending_intent(self):
        self.run_case(self.START+self.INTENT)

    def test_rejects_forged_event_substring(self):
        masked = '{"event":"promotion_intent","name":"concept_0001","term":"λa.a","arity":1,"note":"\\\"event\\\":\\\"promotion_committed\\\""}\n'
        self.run_case(self.START+masked)

    def test_rejects_orphan_commit(self):
        self.run_case(self.START+self.COMMIT)

    def test_rejects_duplicate_key(self):
        self.run_case('{"event":"start","initial_concepts":0,"event":"promotion_committed"}\n')

    def test_rejects_missing_newline(self):
        self.run_case(self.START.rstrip('\n'))

    def test_rejects_library_mismatch(self):
        self.run_case(self.START+self.INTENT+self.COMMIT, 'concept_0001\t1\tλa.λb.b\n')

    def test_rejects_multiple_reused_name(self):
        self.run_case(self.START+self.INTENT+self.COMMIT+
                      '{"event":"start","initial_concepts":1}\n'+self.INTENT)

    def test_rejects_train_after_final(self):
        self.run_case(self.START+'{"event":"final_test_paired"}\n'+
                      '{"event":"train_attempt"}\n')

    def test_rejects_final_row_without_paired(self):
        self.run_case(self.START+'{"event":"final_test"}\n')

    def test_rejects_session_baseline_jump(self):
        self.run_case(self.START+self.INTENT+self.COMMIT+
                      '{"event":"start","initial_concepts":0}\n',
                      'concept_0001\t1\tλa.a\n')

    def test_two_sessions(self):
        history = (self.START+self.INTENT+self.COMMIT+
                   '{"event":"start","initial_concepts":1}\n'+
                   '{"event":"no_promotion"}\n')
        result=self.run_case(history,'concept_0001\t1\tλa.a\n',good=True)
        self.assertEqual(result['commits'],1)


if __name__ == '__main__':
    unittest.main()
