"""v0.7 adversarial evidence tests; native replay fixture remains a MOCK."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from attested_replay import _inventory, _load_key, init_key, seal, verify, main
from native_gate import check_prerequisites, qualify
import test_external_replay_v06 as mock_replay


class AttestationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.output = self.root / 'result'; self.output.mkdir()
        (self.output/'snapshot.json').write_text('{"ok":true}\n')
        (self.output/'report.json').write_text('{"score":2}\n')
        self.key = self.root/'private-key.bin'
        init_key(self.key)
        self.fake_verified = {'trial_key':'trusted-fixture-test', 'claimed_independent_validation':False}
        self.patcher = patch('attested_replay.verify_result', return_value=self.fake_verified)
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

    def test_authenticated_round_trip(self):
        self.assertTrue(seal(self.output,self.key)['sealed'])
        self.assertTrue(verify(self.output,self.key)['authenticated_evidence'])
        self.assertEqual(len(_inventory(self.output)),2)

    def test_modification_detected(self):
        seal(self.output,self.key)
        (self.output/'report.json').write_text('{"score":999}\n')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            verify(self.output,self.key)

    def test_added_file_detected(self):
        seal(self.output,self.key)
        (self.output/'new.txt').write_text('unauthorized')
        with self.assertRaisesRegex(ValueError,'mismatch'):
            verify(self.output,self.key)

    def test_deleted_file_detected(self):
        seal(self.output,self.key)
        (self.output/'snapshot.json').unlink()
        with self.assertRaisesRegex(ValueError,'mismatch'):
            verify(self.output,self.key)

    def test_modified_attestation_detected(self):
        seal(self.output,self.key)
        path=self.output/'attestation.json'
        data=json.loads(path.read_text()); data['trial_key']='substituted'; path.write_text(json.dumps(data))
        with self.assertRaisesRegex(ValueError,'mismatch'):
            verify(self.output,self.key)

    def test_wrong_key_detected(self):
        seal(self.output,self.key)
        different=self.root/'other.bin'; init_key(different)
        with self.assertRaisesRegex(ValueError,'mismatch'):
            verify(self.output,different)

    def test_prevents_re_sealing(self):
        seal(self.output,self.key)
        with self.assertRaisesRegex(ValueError,'already exists'):
            seal(self.output,self.key)

    def test_reject_key_inside_replay(self):
        embedded=self.output/'secret.bin'; init_key(embedded)
        with self.assertRaisesRegex(ValueError,'outside'):
            seal(self.output,embedded)

    def test_symlink_in_evidence_tree_rejected(self):
        (self.output/'link').symlink_to(self.output/'report.json')
        with self.assertRaisesRegex(ValueError,'symlink forbidden'):
            seal(self.output,self.key)

    def test_key_length_rejected(self):
        self.key.write_bytes(b'short')
        with self.assertRaisesRegex(ValueError,'32 random bytes'):
            seal(self.output,self.key)

    @unittest.skipUnless(os.name == 'posix','POSIX file mode')
    def test_key_mode_rejected(self):
        self.key.chmod(0o644)
        with self.assertRaisesRegex(ValueError,'0600'):
            seal(self.output,self.key)

    def test_key_no_overwrite(self):
        with self.assertRaises(FileExistsError):
            init_key(self.key)

    def test_missing_cargo_fails(self):
        with self.assertRaisesRegex(RuntimeError,'unavailable'):
            check_prerequisites(ROOT,'cargo-THIS-IS-ABSENT')

    def test_native_gate_does_not_create_success_without_cargo(self):
        out=self.root/'native-evidence'
        with self.assertRaisesRegex(RuntimeError,'unavailable'):
            qualify(ROOT,out,'cargo-THIS-IS-ABSENT',5)
        self.assertFalse(out.exists())


class FullMockReplayAttestationIntegration(unittest.TestCase):
    def test_seal_mock_replay_end_to_end(self):
        # Explicit mock: verifies protocol integration, not a native synthesizer.
        case=mock_replay.ExternalReplayTests(methodName='test_local_mock_batch_and_verify')
        case.setUp()
        try:
            self.assertEqual(case.replay(),0)
            secret=case.base/'independent-custodian-secret.bin'
            self.assertEqual(main(['init-key','--key',str(secret)]),0)
            self.assertEqual(main(['seal','--out',str(case.out),'--key',str(secret)]),0)
            self.assertEqual(main(['verify','--out',str(case.out),'--key',str(secret)]),0)
            # Mutation of receipt and report while preserving their ordinary
            # hash relation cannot reproduce the evaluator-held HMAC.
            report=case.out/'report.json'; receipt=case.out/'receipt.json'
            data=json.loads(report.read_text()); data['caution']='forged'; report.write_text(json.dumps(data))
            import hashlib
            obj=json.loads(receipt.read_text()); obj['report_sha256']=hashlib.sha256(report.read_bytes()).hexdigest()
            receipt.write_text(json.dumps(obj))
            self.assertEqual(main(['verify','--out',str(case.out),'--key',str(secret)]),2)
        finally:
            case.doCleanups()

if __name__=='__main__': unittest.main()
