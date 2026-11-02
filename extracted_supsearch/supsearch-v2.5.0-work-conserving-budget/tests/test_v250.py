"""Protocol and source qualification for v2.5; no native execution claimed."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from shared_deadline_audit_v250 import audit
from native_shared_deadline_v250 import run


def rows(shared=True):
    return [
      dict(event='start',schema_version=8,time_budget_secs=1.0,shared_time_budget=shared),
      dict(event='train_attempt',kind='raw',composed_elapsed_secs=.25,
           raw_time_limit_secs=.7499 if shared else 1.0,
           raw_elapsed_secs=.45,wall_elapsed_secs=.71),
      dict(event='session_completed')]


class DeadlineReceiptTests(unittest.TestCase):
    def check(self, parts, invalid=None):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'j.jsonl'
            f.write_text(''.join(json.dumps(x)+'\n' for x in parts))
            if invalid:
                with self.assertRaisesRegex(ValueError,invalid):
                    audit(f)
            else:
                return audit(f)

    def test_good_shared(self):
        v=self.check(rows())
        self.assertTrue(v['shared_time_budget'])
        self.assertFalse(v['hard_wall_clock_enforced'])
    def test_good_legacy(self):
        self.assertFalse(self.check(rows(False))['shared_time_budget'])
    def test_replenished_phase_rejected(self):
        x=rows();x[1]['raw_time_limit_secs']=1
        self.check(x,'replenished')
    def test_concept_without_fallback(self):
        x=rows();x[1].update(kind='composed',raw_time_limit_secs=0,raw_elapsed_secs=0)
        self.check(x)
    def test_composed_claim_hiding_raw_work(self):
        x=rows();x[1]['kind']='composed'
        self.check(x,'unexpected raw')
    def test_negative_elapsed_rejected(self):
        x=rows();x[1]['raw_elapsed_secs']=-.2
        self.check(x,'finite')
    def test_nonfinite_elapsed_rejected(self):
        x=rows();x[1]['wall_elapsed_secs']=float('nan')
        self.check(x,'finite')
    def test_bool_elapsed_rejected(self):
        x=rows();x[1]['composed_elapsed_secs']=True
        self.check(x,'finite')
    def test_phase_sum_rejected(self):
        x=rows();x[1]['wall_elapsed_secs']=.4
        self.check(x,'exceed')
    def test_exhausted_budget_cannot_run_raw(self):
        x=rows();x[1].update(composed_elapsed_secs=1.0,raw_time_limit_secs=0.0,raw_elapsed_secs=.01,wall_elapsed_secs=1.05)
        self.check(x,'after time budget')
    def test_missing_metadata_rejected(self):
        x=rows();x[0].pop('shared_time_budget')
        self.check(x,'metadata')
    def test_incomplete_session_rejected(self):
        self.check(rows()[:-1],'complete native session')
    def test_duplicate_key_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            f=Path(td)/'j.jsonl'
            f.write_text(json.dumps(rows()[0])+'\n'+ '{"event":"train_attempt","raw_elapsed_secs":0,"raw_elapsed_secs":1}\n'+json.dumps(rows()[-1])+'\n')
            with self.assertRaisesRegex(ValueError,'duplicate JSON key'):
                audit(f)
    def test_native_probe_is_required(self):
        with tempfile.TemporaryDirectory() as td:
            fake=Path(td)/'fake'; fake.write_text('this is not an executable')
            with self.assertRaisesRegex(ValueError,'native Rust executable required'):
                run(fake,ROOT,Path(td)/'output')
    def test_source_flag_and_native_probe_wired(self):
        source=(ROOT/'src/learning.rs').read_text()
        assert '--shared-time-budget' in source
        assert 'remaining_time_secs(cfg.budget, attempt_start.elapsed())' in source
        assert 'raw_options.time_budget_secs = raw_seconds;' in source
        assert '--shared-time-budget' in (ROOT/'scripts/native_reserved_fallback_v240.py').read_text()
    def test_package_versions(self):
        self.assertIn('version = "2.5.0"',(ROOT/'Cargo.toml').read_text())
        self.assertIn('version = "2.5.0"',(ROOT/'Cargo.lock').read_text())

if __name__=='__main__':unittest.main()
