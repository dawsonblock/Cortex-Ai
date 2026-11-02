"""v0.9 negative-case and protocol compatibility tests. All mocked outcomes are SYNTHETIC."""
import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from transfer_campaign import (SCHEMA, LEGACY_SCHEMA, make_protocol, validate_protocol,
                               evaluate, cluster_ci)


def task_map(n=24, families=4):
    return {f'task_{i:03}': {'family': f'family_{i%families}',
            'sha256': hashlib.sha256(f'opaque-{i}'.encode()).hexdigest()}
            for i in range(n)}


class PreregisteredBreadthTests(unittest.TestCase):
    def test_new_protocol_has_explicit_family_controls(self):
        doc=make_protocol(task_map())
        self.assertEqual(doc['schema'], SCHEMA)
        self.assertEqual(doc['gate']['min_positive_families'],2)
        self.assertEqual(doc['gate']['min_family_size'],2)
        self.assertEqual(validate_protocol(doc),doc)

    def test_old_preregistration_has_identical_digest(self):
        doc=make_protocol(task_map(),schema=LEGACY_SCHEMA)
        self.assertNotIn('min_positive_families', doc['gate'])
        self.assertEqual(validate_protocol(doc),doc)
        old=hashlib.sha256(json.dumps({k:v for k,v in doc.items() if k!='content_sha256'},
                 sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False).encode('ascii')).hexdigest()
        self.assertEqual(old,doc['content_sha256'])

    def test_new_thresholds_are_integrity_bound(self):
        doc=make_protocol(task_map())
        doc['gate']['min_positive_families']=1
        with self.assertRaisesRegex(ValueError,'changed'):
            validate_protocol(doc)

    def test_no_silent_reinterpretation_legacy_v1(self):
        doc=make_protocol(task_map(),schema=LEGACY_SCHEMA)
        doc['gate']['min_family_size']=3
        with self.assertRaisesRegex(ValueError,'changed'):
            validate_protocol(doc)

    def test_disallow_impossible_positive_family_gate(self):
        with self.assertRaisesRegex(ValueError,'exceeds'):
            make_protocol(task_map(),min_families=2,min_positive_families=3)

    def test_min_family_size_required_positive(self):
        with self.assertRaisesRegex(ValueError,'positive'):
            make_protocol(task_map(),min_family_size=0)

    def test_existing_bootstrap_is_deterministic(self):
        rows=[(str(i%4),i%2) for i in range(32)]
        self.assertEqual(cluster_ci(rows,0.05,reps=250,seed=999),
                         cluster_ci(rows,0.05,reps=250,seed=999))

    def test_single_family_gain_rejected_even_if_task_aggregate_positive(self):
        from unittest.mock import patch
        import tempfile
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            tasks=task_map()
            replay=root/'replay'; replay.mkdir()
            (replay/'inputs').mkdir()
            (replay/'private_tasks').mkdir()
            (replay/'inputs'/'native_binary').write_bytes(b'\x7fELF' + b'\x00'*40)
            for tid in tasks:
                (replay/'private_tasks'/f'{tid}.tsk').write_text(
                    'fixture\n---\n@main('+tid+')\n= λa.a\n')
            payload={'task_sha256':{tid:tasks[tid]['sha256'] for tid in tasks},
                     'mode':'per_task_counterbalanced', 'binary_sha256':'1'*64,
                     'initial_library_sha256':'2'*64,
                     'trained_library_sha256':'3'*64, 'learning_ledger_sha256':'4'*64}
            label='local_no_detected_prefix_overlap_not_independent'
            snap={'label':label}
            report={'trial_key':'test_trial','custody_label':label,
                    'candidate_origin':'native_mining_only', 'promotions':1,
                    'claimed_independent_validation':False}
            base={tid:{'solved':False} for tid in tasks}
            learned={tid:{'solved':data['family']=='family_0'} for tid,data in tasks.items()}
            native=root/'native.json'; native.write_text(json.dumps({
                'schema':'supsearch-native-gate-v1','state':'native_compiled_smoke_passed',
                'binary_format':'elf','binary_sha256':'1'*64,
                'independent_holdout_run':False}))
            with patch('transfer_campaign._replay_records',return_value=(snap,report,payload,base,learned)):
                result=evaluate(make_protocol(tasks),[replay],native_qualification=native)
            self.assertEqual(result['positive_family_count'],1)
            self.assertIn('effect_concentrated_in_too_few_families',result['failures'])
            self.assertEqual(result['status'],'local_evidence_not_qualified')

    def test_not_forge_proof_from_python_tests(self):
        native_source=Path(__file__).resolve().parents[1]/'src'/'learning.rs'
        txt=native_source.read_text()
        self.assertIn('reject_cross_split_examples(&train, &dev)?',txt)
        self.assertIn('"final_test_paired',txt)
        self.assertIn('alpha_equivalent_train_dev_examples_rejected',txt)


if __name__=='__main__': unittest.main()
