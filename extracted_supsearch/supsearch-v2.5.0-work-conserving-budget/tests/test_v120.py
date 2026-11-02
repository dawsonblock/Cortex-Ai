"""Fail-closed schema-v7 and full ordered concept-history audit tests.

All fixtures here are synthetic; they do not establish native execution.
"""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from journal_preflight_v110 import audit


def ev(event: str, **kw) -> str:
    import json
    return json.dumps({'event': event, **kw}, ensure_ascii=False) + '\n'


class NativeHistoryQualification(unittest.TestCase):
    def audit_case(self, events, entries='', valid=True):
        with tempfile.TemporaryDirectory() as directory:
            d = Path(directory)
            journal, library = d/'history.jsonl', d/'concepts.tsv'
            journal.write_text(events, encoding='utf-8')
            library.write_text(entries, encoding='utf-8')
            if valid:
                return audit(journal, library)
            with self.assertRaises((ValueError, UnicodeError)):
                audit(journal, library)

    START = ev('start', schema_version=7, initial_concepts=0)
    END0 = ev('session_completed', concept_count=0)
    C1 = ev('promotion_intent', name='concept_0001', arity=1, term='λa.a') + ev('promotion_committed',name='concept_0001', concept_count=1)
    C2 = ev('promotion_intent', name='concept_0002', arity=2, term='λa.λb.b') + ev('promotion_committed',name='concept_0002', concept_count=2)
    GOOD = 'concept_0001\t1\tλa.a\nconcept_0002\t2\tλa.λb.b\n'

    def test_complete_empty_session(self):
        receipt = self.audit_case(self.START + ev('no_promotion', evaluated=0) + self.END0)
        self.assertTrue(receipt['complete_session'])
        self.assertEqual(receipt['concept_count'], 0)

    def test_v7_session_without_completion_fails(self):
        self.audit_case(self.START + ev('no_promotion'), valid=False)

    def test_v7_crash_during_promotion_fails(self):
        self.audit_case(self.START + ev('promotion_intent', name='c', term='λa.a', arity=1), valid=False)

    def test_v7_complete_commit_history(self):
        receipt=self.audit_case(self.START+self.C1+self.C2+ev('session_completed',concept_count=2),self.GOOD)
        self.assertEqual(receipt['commits'], 2)
        self.assertFalse(receipt['baseline_not_attested'])

    def test_earlier_concept_mutation_is_rejected(self):
        bad='concept_0001\t1\tλa.λb.a\nconcept_0002\t2\tλa.λb.b\n'
        self.audit_case(self.START+self.C1+self.C2+ev('session_completed',concept_count=2),bad,valid=False)

    def test_boolean_commit_count_is_rejected(self):
        bad = self.START + ev('promotion_intent', name='concept_0001', arity=1, term='λa.a') + ev('promotion_committed',name='concept_0001',concept_count=True)
        self.audit_case(bad+'', 'concept_0001\t1\tλa.a\n', valid=False)

    def test_reordered_history_is_rejected(self):
        bad='concept_0002\t2\tλa.λb.b\nconcept_0001\t1\tλa.a\n'
        self.audit_case(self.START+self.C1+self.C2+ev('session_completed',concept_count=2),bad,valid=False)

    def test_missing_intermediate_concept_is_rejected(self):
        bad='concept_0002\t2\tλa.λb.b\n'
        self.audit_case(self.START+self.C1+self.C2+ev('session_completed',concept_count=2),bad,valid=False)

    def test_mismatched_terminal_count_is_rejected(self):
        self.audit_case(self.START + ev('session_completed', concept_count=1), valid=False)

    def test_duplicate_terminal_is_rejected(self):
        self.audit_case(self.START+self.END0+self.END0,valid=False)

    def test_new_session_without_earlier_terminal_is_rejected(self):
        self.audit_case(self.START + self.START + self.END0,valid=False)

    def test_multiple_complete_sessions(self):
        history=self.START+self.C1+ev('session_completed',concept_count=1)+ev('start',schema_version=7,initial_concepts=1)+ev('session_completed',concept_count=1)
        lib='concept_0001\t1\tλa.a\n'
        self.assertEqual(self.audit_case(history,lib)['commits'],1)

    def test_v6_legacy_compatibility(self):
        history=ev('start',schema_version=6,initial_concepts=0)+ev('no_promotion')
        result=self.audit_case(history)
        self.assertFalse(result['complete_session'])

    def test_baseline_prefix_is_explicitly_unattested(self):
        start=ev('start',schema_version=7,initial_concepts=1)
        result=self.audit_case(start+ev('session_completed',concept_count=1),
                               'legacy_0001\t1\tλa.a\n')
        self.assertTrue(result['baseline_not_attested'])

    def test_invalid_schema_rejected(self):
        self.audit_case(ev('start',schema_version=True,initial_concepts=0) + self.END0, valid=False)

    def test_no_training_event_after_completion(self):
        self.audit_case(self.START+self.END0+ev('candidate_trial'),valid=False)

    def test_final_then_terminal_is_allowed(self):
        self.audit_case(self.START+ev('final_test_paired')+ev('final_test')+self.END0)

    def test_no_final_after_terminal(self):
        self.audit_case(self.START+self.END0+ev('final_test'),valid=False)


if __name__ == '__main__':
    unittest.main()
