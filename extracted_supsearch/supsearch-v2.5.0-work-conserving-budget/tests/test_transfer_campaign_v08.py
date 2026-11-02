"""All fixtures are MOCK protocol data; no assertion of native learning."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT/'tests'))
from transfer_campaign import (cluster_ci, evaluate, make_protocol,
                               validate_protocol, main)
from external_replay import verify_result


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.tasks={f'fam{i%4}_task{i}':{'family':f'family{i%4}', 'sha256':hashlib.sha256(str(i).encode()).hexdigest()} for i in range(24)}

    def test_round_trip_hash_and_freeze(self):
        p=make_protocol(self.tasks)
        self.assertEqual(validate_protocol(p),p)
        source=self.root/'map.json'; source.write_text(json.dumps(self.tasks))
        frozen=self.root/'frozen.json'
        self.assertEqual(main(['freeze','--task-map',str(source),'--out',str(frozen)]),0)
        self.assertEqual(validate_protocol(json.loads(frozen.read_text())),p)
        self.assertEqual(main(['freeze','--task-map',str(source),'--out',str(frozen)]),2)

    def test_detect_tampered_criteria_and_task_map(self):
        p=make_protocol(self.tasks)
        p['gate']['min_tasks']=1
        with self.assertRaisesRegex(ValueError, 'changed'):
            validate_protocol(p)
        p=make_protocol(self.tasks)
        p['tasks']['fam0_task0']['family']='newfamily'
        with self.assertRaisesRegex(ValueError,'changed'):
            validate_protocol(p)

    def test_reject_unknown_fields_and_bad_family(self):
        bad=dict(self.tasks)
        bad['fam0_task0']={'family':'unsafe/path','sha256': '0'*64}
        with self.assertRaisesRegex(ValueError,'family'):
            make_protocol(bad)
        bad=dict(self.tasks)
        bad['fam0_task0']={'family':'family0','sha256':'g'*64}
        with self.assertRaisesRegex(ValueError,'hash'):
            make_protocol(bad)

    def test_cluster_ci_perfect_and_flat(self):
        rows=[(f'family{i%4}',1) for i in range(24)]
        self.assertEqual(cluster_ci(rows,0.05,reps=1000),[1.0,1.0])
        rows=[(f'family{i%4}',0) for i in range(24)]
        self.assertEqual(cluster_ci(rows,0.05,reps=1000),[0.0,0.0])

    def make_mock_result(self, names, changed=1):
        out=self.root / ('replay-'+str(len(list(self.root.iterdir()))))
        (out/'inputs').mkdir(parents=True)
        (out/'private_tasks').mkdir()
        for n in names:
            (out/'private_tasks'/f'{n}.tsk').write_text(f'mock task\n---\n@main({n})\n= λx.x\n')
        (out/'inputs'/'native_binary').write_bytes(b'\x7fELF' + b'\x00'*40)
        trial=hashlib.sha256(str(out).encode()).hexdigest()
        payload={'task_sha256':{n:self.tasks[n]['sha256'] for n in names},'mode':'per_task_counterbalanced',
                 'binary_sha256':'0'*64,'initial_library_sha256':'1'*64,
                 'trained_library_sha256':'2'*64,'learning_ledger_sha256':'3'*64}
        snap={'label':'local_no_detected_prefix_overlap_not_independent'}
        report={'trial_key':trial,'custody_label':snap['label'],
                'candidate_origin':'native_mining_only','promotions':1,
                'claimed_independent_validation':False}
        before={n:{'solved':False, 'built':100} for n in names}
        after={n:{'solved':bool(changed), 'built':5} for n in names}
        return out,(snap,report,payload,before,after)

    def make_mock_gate(self):
        p=self.root/'mock-qualification.json'
        p.write_text(json.dumps({'schema':'supsearch-native-gate-v1',
             'state':'native_compiled_smoke_passed','binary_format':'elf',
             'binary_sha256':'0'*64,'independent_holdout_run':False}))
        return p

    def test_all_wins_can_pass_local_gate_in_mocked_calculation(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        with patch('transfer_campaign._replay_records',return_value=data):
            result=evaluate(make_protocol(self.tasks),[replay],native_qualification=self.make_mock_gate())
        self.assertEqual(result['status'],'local_evidence_qualified')
        self.assertFalse(result['independently_validated'])
        self.assertEqual(result['family_count'],4)

    def test_no_gain_fails_even_with_promotions(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names,changed=0)
        with patch('transfer_campaign._replay_records',return_value=data):
            result=evaluate(make_protocol(self.tasks),[replay])
        self.assertEqual(result['status'],'local_evidence_not_qualified')
        self.assertIn('effect_below_preregistered_threshold',result['failures'])

    def test_missing_native_gate_fails_closed(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        with patch('transfer_campaign._replay_records',return_value=data):
            result=evaluate(make_protocol(self.tasks),[replay])
        self.assertEqual(result['status'],'local_evidence_not_qualified')
        self.assertIn('native_build_qualification_missing_or_wrong_binary',result['failures'])

    def test_wrong_native_build_hash_rejected(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        p=self.make_mock_gate(); x=json.loads(p.read_text()); x['binary_sha256']='f'*64;p.write_text(json.dumps(x))
        with patch('transfer_campaign._replay_records',return_value=data):
            result=evaluate(make_protocol(self.tasks),[replay],native_qualification=p)
        self.assertIn('native_build_qualification_missing_or_wrong_binary',result['failures'])

    def test_duplicate_trials_rejected(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        with patch('transfer_campaign._replay_records',return_value=data):
            with self.assertRaisesRegex(ValueError,'duplicate evaluation'):
                evaluate(make_protocol(self.tasks),[replay,replay])

    def test_task_checksum_mismatch_fails(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        data[2]['task_sha256'][names[0]]='f'*64
        with patch('transfer_campaign._replay_records',return_value=data):
            with self.assertRaisesRegex(ValueError,'digest'):
                evaluate(make_protocol(self.tasks),[replay])

    def test_duplicate_task_digests_fail(self):
        dup=dict(self.tasks)
        dup['fam0_task0']={'family':'family0','sha256':self.tasks['fam1_task1']['sha256']}
        with self.assertRaisesRegex(ValueError,'duplicate task file'):
            make_protocol(dup)

    def test_cross_task_reused_examples_fail(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        a,b=names[:2]
        (replay/'private_tasks'/f'{b}.tsk').write_bytes((replay/'private_tasks'/f'{a}.tsk').read_bytes())
        with patch('transfer_campaign._replay_records',return_value=data):
            with self.assertRaisesRegex(ValueError,'cross-task test example'):
                evaluate(make_protocol(self.tasks),[replay])

    def test_incomplete_task_family_fails(self):
        names=list(self.tasks)[:4]
        replay,data=self.make_mock_result(names)
        with patch('transfer_campaign._replay_records',return_value=data):
            with self.assertRaisesRegex(ValueError,'incomplete'):
                evaluate(make_protocol(self.tasks),[replay])

    def test_attestation_rejected_if_not_provided_or_invalid(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        with patch('transfer_campaign._replay_records',return_value=data):
            # A non-attested campaign cannot make an independent claim; local gate only.
            result=evaluate(make_protocol(self.tasks),[replay])
        self.assertIsNone(result['attested_hmac_key_id'])
        with patch('transfer_campaign._replay_records',return_value=data), \
             patch('attested_replay.verify',side_effect=ValueError('invalid hmac')):
            with self.assertRaisesRegex(ValueError,'invalid hmac'):
                evaluate(make_protocol(self.tasks),[replay],attestation_key=self.root/'secret')

    def test_mock_script_binary_cannot_qualify(self):
        names=list(self.tasks)
        replay,data=self.make_mock_result(names)
        (replay/'inputs'/'native_binary').write_bytes(b'#!/bin/sh\nexit 0\n')
        with patch('transfer_campaign._replay_records',return_value=data):
            with self.assertRaisesRegex(ValueError,'non-native executable'):
                evaluate(make_protocol(self.tasks),[replay])


class MockReplayIntegration(unittest.TestCase):
    def test_existing_mock_replay_is_not_native_qualified(self):
        from test_external_replay_v06 import ExternalReplayTests
        case=ExternalReplayTests(methodName='test_counterbalanced_mock_replay')
        case.setUp()
        try:
            self.assertEqual(case.replay('--counterbalanced'),0)
            from transfer_campaign import _replay_records
            snap,report,payload,base,up=_replay_records(case.out)
            task_map={t:{'family':'family_'+t, 'sha256':h} for t,h in payload['task_sha256'].items()}
            with self.assertRaisesRegex(ValueError,'non-native executable'):
                evaluate(make_protocol(task_map,min_families=2,min_tasks=2,min_new=1),[case.out])
        finally:
            case.doCleanups()

if __name__=='__main__': unittest.main()

class TaskMapTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
    def test_create_map_and_no_clobber(self):
        from create_task_map import build, main as cli
        for tid in ('arith_1','list_1','graph_1'):
            (self.root/f'{tid}.tsk').write_text(f'test\n---\n@main({tid})\n= λx.x\n')
        families={'arith_1':'arithmetic','list_1':'lists','graph_1':'graphs'}
        desc=build(self.root,families)
        self.assertEqual(set(desc),set(families))
        inp=self.root/'fams.json';inp.write_text(json.dumps(families))
        out=self.root/'map.json'
        self.assertEqual(cli(['--source',str(self.root),'--families',str(inp),'--out',str(out)]),0)
        self.assertEqual(json.loads(out.read_text()),desc)
        self.assertEqual(cli(['--source',str(self.root),'--families',str(inp),'--out',str(out)]),2)
    def test_path_traversal_rejected(self):
        from create_task_map import build
        with self.assertRaisesRegex(ValueError,'unsafe task'):
            build(self.root,{'../../private':'other'})
    def test_repeated_examples_rejected(self):
        from create_task_map import build
        for tid in ('t1','t2'):
            (self.root/f'{tid}.tsk').write_text('test\n---\n@main(λx.x)\n= λx.x\n')
        with self.assertRaisesRegex(ValueError,'example reuse'):
            build(self.root,{'t1':'a','t2':'b'})
