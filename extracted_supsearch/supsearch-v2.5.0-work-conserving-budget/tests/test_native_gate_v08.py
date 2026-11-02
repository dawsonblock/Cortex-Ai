"""Mock-based structural tests; never report these as actual native compilation."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from native_gate import qualify

class NativeQualificationIsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name)
        self.src=self.base/'src';self.src.mkdir()
        (self.src/'Cargo.toml').write_text('[package]\nname = "supsearch"\nversion = "0.8.0"\nedition = "2021"\n')
        (self.src/'Cargo.lock').write_text('version = 4\n')
        self.out=self.base/'evidence'

    def test_native_cargo_commands_are_offline_and_build_isolated(self):
        commands=[]
        def mock_exec(argv, cwd, log, seconds, *, env=None):
            commands.append((argv,cwd,log,env))
        with patch('native_gate.check_prerequisites', return_value={'cargo':'cargo','project':str(self.src)}), \
             patch('native_gate._exec',side_effect=mock_exec):
            with self.assertRaisesRegex(RuntimeError,'no native executable'):
                qualify(self.src,self.out,'cargo',10)
        self.assertTrue((self.out/'FAILURE.txt').exists())
        self.assertFalse((self.out/'qualification.json').exists())
        self.assertEqual(len(commands),2)
        for args,cwd,log,env in commands:
            self.assertIn('--locked',args)
            self.assertIn('--offline',args)
            self.assertEqual(cwd,self.src)
            self.assertEqual(env['CARGO_TARGET_DIR'],str((self.out/'target').resolve()))
            self.assertEqual(env['CARGO_INCREMENTAL'],'0')
        self.assertIn('test',commands[0][0])
        self.assertIn('--release',commands[1][0])

    def test_output_inside_source_rejected(self):
        sub=self.src/'out'
        with patch('native_gate.check_prerequisites',return_value={'cargo':'cargo','project':str(self.src)}):
            with self.assertRaisesRegex(ValueError,'separate'):
                qualify(self.src,sub,'cargo',10)
        self.assertFalse(sub.exists())

    def test_missing_cargo_is_fail_closed(self):
        with patch('native_gate.check_prerequisites',side_effect=RuntimeError('Cargo missing')):
            with self.assertRaisesRegex(RuntimeError,'Cargo missing'):
                qualify(self.src,self.out,'cargo',10)
        self.assertFalse(self.out.exists())

if __name__=='__main__':unittest.main()
