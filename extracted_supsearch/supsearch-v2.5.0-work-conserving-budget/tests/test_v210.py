"""V2.1 regression controls: static wiring + executable Python protocol checks.

These are NOT a substitute for Cargo. Native Rust tests are defined in source.
"""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]

class NativeQualificationWiring(unittest.TestCase):
    def test_native_gate_accepts_current_schema_8(self):
        native=(ROOT/'scripts/native_gate.py').read_text()
        rust=(ROOT/'src/learning.rs').read_text()
        self.assertIn('\\"schema_version\\":8',rust)
        self.assertIn("events[0].get('schema_version') != 8",native)
        self.assertNotIn("events[0].get('schema_version') != 7",native)
    def test_native_gate_preflight_fails_without_compiler(self):
        with tempfile.TemporaryDirectory() as d:
            from unittest.mock import patch
            sys.path.insert(0,str(ROOT/'scripts'))
            from native_gate import check_prerequisites
            with patch('native_gate.shutil.which',return_value=None):
                with self.assertRaisesRegex(RuntimeError,'Native compilation is NOT verified'):
                    check_prerequisites(ROOT)
    def test_native_gate_importable_and_help(self):
        x=subprocess.run([sys.executable,str(ROOT/'scripts/native_gate.py'),'--help'],capture_output=True,text=True,timeout=20)
        self.assertEqual(x.returncode,0,x.stderr)
        self.assertIn('--preflight',x.stdout)
    def test_rust_curriculum_has_ever_solved_guard(self):
        source=(ROOT/'src/curriculum.rs').read_text()
        self.assertIn('ever_solved: bool',source)
        self.assertIn('solved && !old.ever_solved',source)
        self.assertIn('old.ever_solved || solved',source)
        self.assertIn('regression_then_recovery_does_not_fabricate_first_solve_reward',source)
    def test_atomic_writes_use_create_new_and_protect_unowned_temps(self):
        src=(ROOT/'src/learning.rs').read_text()
        a=src[src.index('pub(crate) fn atomic_write('):src.index('pub(crate) fn atomic_write_new(')]
        b=src[src.index('pub(crate) fn atomic_write_new('):src.index('pub(crate) fn json_escape(')]
        self.assertIn('create_new(true)',a)
        self.assertIn('create_new(true)',b)
        self.assertIn('atomic_write_refuses_preexisting_temp_without_modifying_it',src)
        self.assertIn('immutable_write_preserves_preexisting_temp_and_destination',src)
    def test_lockfile_matches_cargo_metadata(self):
        lock=(ROOT/'Cargo.lock').read_text()
        toml=(ROOT/'Cargo.toml').read_text()
        import re
        version = re.search(r'^version = "([0-9.]+)"$', toml, re.M)
        self.assertIsNotNone(version)
        self.assertIn('version = "'+version.group(1)+'"',lock)

if __name__=='__main__':unittest.main()
