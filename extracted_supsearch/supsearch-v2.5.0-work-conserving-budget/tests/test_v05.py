"""Negative integrity controls for v0.5 local qualification.

These tests do not execute the native synthesis engine or attest to learning.
"""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from evidence_integrity import (strict_json_loads, strict_jsonl, library_entries,
                                reconcile_library, result_gate)
from qualified_pipeline import binary_format, parse_eval


class EvidenceIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)

    def file(self, name, content):
        p = self.base / name
        p.write_text(content, encoding='utf8')
        return p

    def valid_lineage(self):
        initial = self.file('initial.tsv', '# empty\n')
        learned = self.file('learned.tsv', '# acquired\nconcept_0001\t2\tλa.λb.a(b)\n')
        ledger = self.file('events.jsonl', '\n'.join(json.dumps(x,ensure_ascii=False) for x in [
            {'event':'start'},
            {'event':'candidate_trial','round':0,'accepted':True},
            {'event':'promotion_intent','name':'concept_0001','term':'λa.λb.a(b)','arity':2},
            {'event':'promotion_committed','name':'concept_0001','concept_count':1}
        ])+'\n')
        return ledger, initial, learned

    def test_duplicate_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            strict_json_loads('{"event":"a","event":"b"}')

    def test_non_finite_json_rejected(self):
        with self.assertRaisesRegex(ValueError, 'non-finite'):
            strict_json_loads('{"score":Infinity}')

    def test_blank_jsonl_row_rejected(self):
        with self.assertRaisesRegex(ValueError, 'blank JSONL'):
            strict_jsonl(self.file('rows.jsonl','{"event":"a"}\n\n'))

    def test_jsonl_byte_limit(self):
        with self.assertRaisesRegex(ValueError, 'exceeds'):
            strict_jsonl(self.file('rows.jsonl','{"a":1}'), max_bytes=4)

    def test_library_valid(self):
        _, initial, learned = self.valid_lineage()
        self.assertEqual(library_entries(initial),[])
        self.assertEqual(len(library_entries(learned)),1)

    def test_library_reject_duplicate_bodies(self):
        p=self.file('concepts.tsv','a\t2\tλa.λb.a(b)\nb\t2\tλa.λb.a(b)\n')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            library_entries(p)

    def test_library_reject_illegal_header(self):
        p=self.file('concepts.tsv','bad name\t2\tλa.λb.a(b)\n')
        with self.assertRaisesRegex(ValueError,'malformed'):
            library_entries(p)

    def test_reconcile_valid(self):
        ledger, initial, learned = self.valid_lineage()
        self.assertEqual(reconcile_library(ledger,initial,learned)['promotions'],1)

    def test_reconcile_detects_modified_term(self):
        ledger, initial, learned = self.valid_lineage()
        learned.write_text('concept_0001\t2\tλa.λb.b(a)\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'ledger/library mismatch'):
            reconcile_library(ledger,initial,learned)

    def test_reconcile_detects_modified_original_library(self):
        ledger, initial, learned = self.valid_lineage()
        initial.write_text('original\t2\tλa.λb.b(a)\n',encoding='utf8')
        with self.assertRaisesRegex(ValueError,'modified original'):
            reconcile_library(ledger,initial,learned)

    def test_reconcile_detects_forged_commit_count(self):
        ledger, initial, learned = self.valid_lineage()
        ledger.write_text(ledger.read_text().replace('"concept_count": 1','"concept_count": 5'))
        with self.assertRaisesRegex(ValueError,'concept_count'):
            reconcile_library(ledger,initial,learned)

    def test_reconcile_detects_missing_commit(self):
        ledger, initial, learned = self.valid_lineage()
        ledger.write_text('\n'.join(ledger.read_text().splitlines()[:-1])+'\n')
        with self.assertRaisesRegex(ValueError,'count mismatch'):
            reconcile_library(ledger,initial,learned)

    def test_result_gate_does_not_claim_independence(self):
        pair={'upgraded_solved':18,'baseline_solved':11,'regressions':[]}
        gate=result_gate(pair,task_count=25,custody_label='local_no_detected_prefix_overlap_not_independent',
                         has_candidates=False,promotions=2)
        self.assertTrue(gate['local_screen_passed'])
        self.assertFalse(gate['independent_validation'])
        self.assertEqual(gate['reasons'],[])

    def test_result_gate_rejects_seeded_demo_or_small_suite(self):
        pair={'upgraded_solved':3,'baseline_solved':1,'regressions':[]}
        gate=result_gate(pair,task_count=4,custody_label='synthetic_fixture_not_holdout',
                         has_candidates=True,promotions=1)
        self.assertFalse(gate['local_screen_passed'])
        self.assertIn('insufficient_final_tasks',gate['reasons'])
        self.assertIn('externally_seeded_candidates',gate['reasons'])
        self.assertIn('synthetic_fixture_mode',gate['reasons'])

    def test_result_gate_blocks_regressions_and_no_effect(self):
        pair={'upgraded_solved':5,'baseline_solved':5,'regressions':['t1']}
        gate=result_gate(pair,task_count=25,custody_label='local_no_detected_prefix_overlap_not_independent',
                         has_candidates=False,promotions=0)
        self.assertFalse(gate['local_screen_passed'])
        self.assertIn('regressions_on_final_tasks',gate['reasons'])
        self.assertIn('no_solve_rate_improvement',gate['reasons'])

    def test_eval_refuses_bogus_frozen_metadata(self):
        m={'event':'evaluation_meta','mode':'concept','task_count':1,'concept_count':17,
           'budget':0.5,'max_size':13,'fuel':20000}
        row={'event':'evaluation','task':'one','mode':'concept','solved':True,
             'built':18,'elapsed_secs':0.05}
        p=self.file('data.jsonl',json.dumps(m)+'\n'+json.dumps(row)+'\n')
        with self.assertRaisesRegex(ValueError,'concept_count disagrees'):
            parse_eval(p,['one'],'concept',expected_concepts=0,expected_settings=m)
        with self.assertRaisesRegex(ValueError,'budget disagrees'):
            parse_eval(p,['one'],'concept',expected_concepts=17,
                       expected_settings={**m,'budget':1.0})
        self.assertEqual(len(parse_eval(p,['one'],'concept',expected_concepts=17,expected_settings=m)),1)

    def test_eval_refuses_non_object_row(self):
        p=self.file('data.jsonl',json.dumps({'event':'evaluation_meta','mode':'raw','task_count':1,
                                              'concept_count':0})+'\n[]\n')
        with self.assertRaisesRegex(ValueError,'not an object'):
            parse_eval(p,['one'],'raw')

    def test_binary_header_classification_only(self):
        self.assertEqual(binary_format(self.file('b','#!/bin/sh\nexit 0\n')), 'script')
        p=self.base/'elf'
        p.write_bytes(b'\x7fELFnot-really-a-binary')
        self.assertEqual(binary_format(p), 'elf')  # not compilation proof

    def test_rust_no_clobber_implementation_present(self):
        native=(ROOT/'src/learning.rs').read_text()
        evaluator=(ROOT/'src/evaluation.rs').read_text()
        self.assertIn('pub(crate) fn atomic_write_new(',native)
        self.assertIn('fs::hard_link(&temp, path)',native)
        self.assertIn('learning::atomic_write_new(&c.out,output.as_bytes())',evaluator)


if __name__ == '__main__':
    unittest.main()
