import React, { useState, useEffect } from 'react';
import { 
  Terminal, 
  Play, 
  CheckCircle2, 
  XCircle, 
  Clock, 
  ShieldCheck, 
  FileText, 
  Layers, 
  RotateCcw,
  Sparkles,
  AlertCircle
} from 'lucide-react';
import { TestExecutionResult } from '../types';

export const TestsRunnerTab: React.FC = () => {
  const [running, setRunning] = useState<boolean>(false);
  const [currentTest, setCurrentTest] = useState<string>('test_v250.py');
  const [lastResult, setLastResult] = useState<TestExecutionResult | null>(null);
  const [validations, setValidations] = useState<Record<string, any>>({});
  const [selectedValidationKey, setSelectedValidationKey] = useState<string>('VALIDATION_V250.json');

  const testSuites = [
    { id: 'test_v250.py', label: 'test_v250.py', desc: 'Work-conserving shared search time & zero-time prohibition' },
    { id: 'test_v240.py', label: 'test_v240.py', desc: 'Nonempty-library fallback probe & receipts audit' },
    { id: 'test_v230.py', label: 'test_v230.py', desc: 'Reserved raw fallback allocation & candidate limits' },
    { id: 'test_v220.py', label: 'test_v220.py', desc: 'MDL compression gain & admission gate audit' },
    { id: 'test_v210.py', label: 'test_v210.py', desc: 'Curriculum recovery reward inflation fix' },
    { id: 'test_qualified_pipeline.py', label: 'test_qualified_pipeline.py', desc: 'End-to-end task pipeline protocol qualification' },
    { id: 'audit_shared_deadline', label: 'shared_deadline_audit_v250.py', desc: 'Protocol audit CLI runner' },
    { id: 'check_manifest', label: 'check_manifest.py', desc: 'SHA-256 integrity verification against MANIFEST.sha256' },
  ];

  // Fetch validation files on mount
  useEffect(() => {
    fetch('/api/supsearch/validations')
      .then(res => res.json())
      .then(data => {
        if (data.validations) {
          setValidations(data.validations);
        }
      })
      .catch(err => console.error('Failed to load validations:', err));
  }, []);

  const handleRunTest = async (testId: string) => {
    setCurrentTest(testId);
    setRunning(true);
    try {
      const res = await fetch('/api/supsearch/tests/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ testName: testId })
      });
      const data = await res.json();
      setLastResult(data);
    } catch (err: any) {
      setLastResult({
        target: testId,
        command: `python3 -m unittest tests/${testId}`,
        success: false,
        exitCode: 1,
        stdout: '',
        stderr: err.message || 'Execution failed',
        durationMs: 0
      });
    } finally {
      setRunning(false);
    }
  };

  const validationKeys = Object.keys(validations).sort().reverse();
  const activeValidation = validations[selectedValidationKey];

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Terminal className="w-6 h-6 text-emerald-400" />
          Test Suite &amp; Qualification Protocol Runner
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Execute authentic Python validation scripts directly on the system and audit protocol evidence records.
        </p>
      </div>

      {/* Test Execution Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Test Suites List */}
        <div className="lg:col-span-5 space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800">
            <h2 className="text-sm font-bold text-white mb-3 flex items-center justify-between">
              <span>Executable Test Modules</span>
              <span className="text-[11px] font-mono text-emerald-400 bg-emerald-950/70 px-2 py-0.5 rounded border border-emerald-800/40">
                8 Suites Available
              </span>
            </h2>

            <div className="space-y-2">
              {testSuites.map((suite) => (
                <div
                  key={suite.id}
                  className={`p-3 rounded-xl border transition-all flex items-center justify-between gap-3 ${
                    currentTest === suite.id
                      ? 'bg-emerald-950/20 border-emerald-500/50 text-white'
                      : 'bg-slate-950/60 border-slate-800/80 hover:border-slate-700 text-slate-300'
                  }`}
                >
                  <div className="min-w-0">
                    <span className="font-mono text-xs font-semibold block text-emerald-300 truncate">
                      {suite.label}
                    </span>
                    <span className="text-[11px] text-slate-400 block truncate">
                      {suite.desc}
                    </span>
                  </div>

                  <button
                    onClick={() => handleRunTest(suite.id)}
                    disabled={running}
                    className="shrink-0 p-2 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white disabled:opacity-50 transition-all cursor-pointer shadow-md shadow-emerald-500/10"
                    title={`Run ${suite.label}`}
                  >
                    <Play className="w-3.5 h-3.5 fill-current" />
                  </button>
                </div>
              ))}
            </div>

            <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
              <span className="text-xs text-slate-400">Run primary test suite:</span>
              <button
                onClick={() => handleRunTest('test_v250.py')}
                disabled={running}
                className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-medium text-emerald-400 flex items-center gap-1.5 transition-all cursor-pointer"
              >
                <RotateCcw className="w-3.5 h-3.5" />
                <span>Re-run test_v250.py</span>
              </button>
            </div>
          </div>
        </div>

        {/* Right: Terminal Console Output */}
        <div className="lg:col-span-7 space-y-4">
          <div className="rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden shadow-2xl flex flex-col h-full min-h-[420px]">
            {/* Terminal Header */}
            <div className="px-4 py-3 bg-slate-900 border-b border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-rose-500/80" />
                <div className="w-3 h-3 rounded-full bg-amber-500/80" />
                <div className="w-3 h-3 rounded-full bg-emerald-500/80" />
                <span className="ml-2 font-mono text-xs text-slate-400">
                  {lastResult ? lastResult.command : 'bash — python3 test runner'}
                </span>
              </div>

              {lastResult && (
                <div className="flex items-center gap-2 text-xs font-mono">
                  <span className="text-slate-400 flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    {lastResult.durationMs}ms
                  </span>
                  <span className={`px-2 py-0.5 rounded flex items-center gap-1 font-semibold ${
                    lastResult.success 
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800' 
                      : 'bg-rose-950 text-rose-400 border border-rose-800'
                  }`}>
                    {lastResult.success ? (
                      <>
                        <CheckCircle2 className="w-3 h-3" />
                        PASSED
                      </>
                    ) : (
                      <>
                        <XCircle className="w-3 h-3" />
                        FAILED (code {lastResult.exitCode})
                      </>
                    )}
                  </span>
                </div>
              )}
            </div>

            {/* Terminal Body */}
            <div className="p-4 font-mono text-xs text-slate-300 flex-1 overflow-y-auto max-h-[350px] space-y-1">
              {running ? (
                <div className="flex items-center gap-2 text-cyan-400 py-6 justify-center">
                  <div className="w-2 h-2 rounded-full bg-cyan-400 animate-ping" />
                  <span>Executing {currentTest}...</span>
                </div>
              ) : lastResult ? (
                <div>
                  <div className="text-slate-500 text-[11px] mb-2">
                    $ {lastResult.command}
                  </div>
                  {lastResult.stdout && (
                    <pre className="text-slate-300 whitespace-pre-wrap">{lastResult.stdout}</pre>
                  )}
                  {lastResult.stderr && (
                    <pre className={lastResult.success ? 'text-emerald-400 whitespace-pre-wrap' : 'text-rose-400 whitespace-pre-wrap'}>
                      {lastResult.stderr}
                    </pre>
                  )}
                  {lastResult.success && (
                    <div className="mt-3 text-emerald-400 font-semibold text-[11px] flex items-center gap-1">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      Execution finished cleanly with return code 0.
                    </div>
                  )}
                </div>
              ) : (
                <div className="text-slate-600 text-center py-16">
                  Select a test suite and click the run button to view live verification logs.
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Validation Evidence Records (v100 through v250) */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-5">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-cyan-400" />
              Historical Validation Records &amp; Release Evidence
            </h2>
            <p className="text-xs text-slate-400">
              Audit stored JSON verification reports across all Supsearch development milestones.
            </p>
          </div>

          {/* Validation file pills */}
          <div className="flex flex-wrap gap-1.5">
            {validationKeys.slice(0, 8).map((key) => (
              <button
                key={key}
                onClick={() => setSelectedValidationKey(key)}
                className={`px-2.5 py-1 rounded-lg text-xs font-mono transition-all cursor-pointer ${
                  selectedValidationKey === key
                    ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 font-semibold'
                    : 'bg-slate-950 text-slate-400 hover:text-slate-200 border border-slate-800'
                }`}
              >
                {key.replace('.json', '')}
              </button>
            ))}
          </div>
        </div>

        {activeValidation && (
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-4">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-900 pb-3">
              <div>
                <span className="font-mono font-bold text-sm text-cyan-300">
                  {selectedValidationKey}
                </span>
                <span className="text-xs text-slate-400 ml-3">
                  Release: <strong className="text-white">{activeValidation.release || 'N/A'}</strong>
                </span>
              </div>
              <span className="text-xs text-slate-400 font-mono">
                Scope: {activeValidation.scope || 'Experimental'}
              </span>
            </div>

            {/* Changes list */}
            {activeValidation.changes && (
              <div>
                <span className="text-xs font-semibold text-slate-300 block mb-1">
                  Validated Changes in this Milestone:
                </span>
                <ul className="grid grid-cols-1 md:grid-cols-2 gap-1.5 text-xs text-slate-400">
                  {activeValidation.changes.map((c: string, idx: number) => (
                    <li key={idx} className="flex items-start gap-1.5">
                      <span className="text-cyan-400">•</span>
                      <span>{c}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {/* Checks grid */}
            {activeValidation.checks && (
              <div>
                <span className="text-xs font-semibold text-slate-300 block mb-2">
                  Qualification Verification Checks:
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-3 gap-2">
                  {Object.entries(activeValidation.checks).map(([checkName, checkData]: any) => (
                    <div key={checkName} className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-mono text-slate-300 truncate font-medium">
                          {checkName}
                        </span>
                        <span className={`text-[10px] font-mono px-1.5 py-0.2 rounded ${
                          checkData.status === 'passed'
                            ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                            : checkData.status === 'timed_out'
                            ? 'bg-amber-950 text-amber-400 border border-amber-800'
                            : 'bg-slate-800 text-slate-400'
                        }`}>
                          {checkData.status}
                        </span>
                      </div>
                      <div className="text-[10px] text-slate-400">
                        {checkData.count ? `${checkData.count} targeted tests` : checkData.reason || checkData.note || 'Verified'}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Limits */}
            {activeValidation.limits && (
              <div className="pt-2 border-t border-slate-900">
                <span className="text-xs font-semibold text-slate-300 block mb-1">
                  Documented Scientific Limits &amp; Non-Claims:
                </span>
                <div className="space-y-1 text-[11px] text-slate-400 italic">
                  {activeValidation.limits.map((lim: string, idx: number) => (
                    <div key={idx}>— {lim}</div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
};
