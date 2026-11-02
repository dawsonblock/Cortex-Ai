import React, { useState } from 'react';
import { 
  Play, 
  Cpu, 
  Sparkles, 
  RotateCcw, 
  CheckCircle, 
  Clock, 
  FileCode, 
  Sliders, 
  ShieldCheck, 
  Layers, 
  Code2, 
  Terminal,
  ArrowRight
} from 'lucide-react';
import { SynthesisResult, LambdaEvalResult } from '../types';

interface SynthesizerTabProps {
  initialTaskId?: string;
}

export const SynthesizerTab: React.FC<SynthesizerTabProps> = ({ initialTaskId = 'cnat_add' }) => {
  const [selectedTask, setSelectedTask] = useState<string>(initialTaskId);
  const [sharedTimeBudget, setSharedTimeBudget] = useState<boolean>(true);
  const [rawReservePct, setRawReservePct] = useState<number>(20);
  const [timeBudgetMs, setTimeBudgetMs] = useState<number>(5000);
  const [maxBuilt, setMaxBuilt] = useState<number>(100);
  const [preloadedLibrary, setPreloadedLibrary] = useState<boolean>(true);

  const [synthesizing, setSynthesizing] = useState<boolean>(false);
  const [synthesisResult, setSynthesisResult] = useState<SynthesisResult | null>(null);

  // Lambda Playground state
  const [lambdaExpr, setLambdaExpr] = useState<string>('(λm.λn.λf.λx.m(f)(n(f)(x)))(λf.λx.f(x))(λf.λx.f(x))');
  const [evaluating, setEvaluating] = useState<boolean>(false);
  const [evalResult, setEvalResult] = useState<LambdaEvalResult | null>(null);

  const taskPresets = [
    { id: 'cnat_add', label: 'cnat_add (Church Addition)', family: 'cnat', expected: 'λa.λb.λc.λd. a c (b c d)' },
    { id: 'clst_map', label: 'clst_map (Church List Map)', family: 'clst', expected: 'λf.λxs.λc.λn. xs (λx.λacc. c (f x) acc) n' },
    { id: 'ctre_rev', label: 'ctre_rev (Tree Branch Mirror)', family: 'ctre', expected: 'λt.λleaf.λnode. t leaf (λl.λv.λr. node r v l)' },
    { id: 'ntup_hed', label: 'ntup_hed (Tuple Head Projection)', family: 'ntup', expected: 'λt. t (λh.λr. h)' },
    { id: 'cbin_mul', label: 'cbin_mul (Binary Bitstring Mul)', family: 'cbin', expected: 'λa.λb. a (λacc. add b (shift acc)) zero' },
    { id: 'algo_sat', label: 'algo_sat (The Algo Wall / SAT)', family: 'algo_', expected: 'Unsolved (Exhausts Bounded DSL)' },
  ];

  const evalPresets = [
    { label: 'Church 1 + 1 = 2', expr: '(λm.λn.λf.λx.m(f)(n(f)(x)))(λf.λx.f(x))(λf.λx.f(x))' },
    { label: 'Church Succ(1) = 2', expr: '(λn.λf.λx.f(n(f)(x)))(λf.λx.f(x))' },
    { label: 'K-Combinator / Select First', expr: '(λx.λy.x)(Alpha)(Beta)' },
    { label: 'Boolean AND (True, False)', expr: '(λp.λq.p(q)(p))(λx.λy.x)(λx.λy.y)' },
    { label: 'Boolean NOT (False = True)', expr: '(λp.λa.λb.p(b)(a))(λx.λy.y)' },
  ];

  const handleSynthesize = async () => {
    setSynthesizing(true);
    try {
      const res = await fetch('/api/supsearch/synthesize', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          taskId: selectedTask,
          timeBudgetMs,
          sharedTimeBudget,
          rawReservePct,
          maxBuilt,
          preloadedLibrary
        })
      });
      const data = await res.json();
      setSynthesisResult(data);
    } catch (err) {
      console.error('Synthesis failed:', err);
    } finally {
      setSynthesizing(false);
    }
  };

  const handleEvaluateLambda = async (customExpr?: string) => {
    const expr = customExpr || lambdaExpr;
    setEvaluating(true);
    try {
      const res = await fetch('/api/supsearch/lambda/evaluate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ expression: expr })
      });
      const data = await res.json();
      setEvalResult(data);
    } catch (err) {
      console.error('Lambda evaluation failed:', err);
    } finally {
      setEvaluating(false);
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <Cpu className="w-6 h-6 text-indigo-400" />
          Interactive Lambda Synthesizer &amp; NBE Normalizer
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Simulate Supsearch's work-conserving search engine with live budget receipts, phase audits, and AST beta-reduction.
        </p>
      </div>

      {/* Synthesis Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Configuration & Controls */}
        <div className="lg:col-span-5 space-y-5">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            <h2 className="text-sm font-bold text-white flex items-center gap-2">
              <Sliders className="w-4 h-4 text-cyan-400" />
              Benchmark Task &amp; Budget Controls
            </h2>

            {/* Task selector */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Target LamBench Task
              </label>
              <select
                value={selectedTask}
                onChange={(e) => setSelectedTask(e.target.value)}
                className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white font-mono focus:border-cyan-500 focus:outline-none"
              >
                {taskPresets.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.label}
                  </option>
                ))}
              </select>
            </div>

            {/* v2.5.0 Shared Time Budget Toggle */}
            <div className="p-3 rounded-xl bg-slate-950/70 border border-cyan-500/30 flex items-center justify-between">
              <div>
                <span className="text-xs font-semibold text-white block">
                  --shared-time-budget
                </span>
                <span className="text-[11px] text-slate-400">
                  Enforces single deadline across concept &amp; raw
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSharedTimeBudget(!sharedTimeBudget)}
                className={`relative inline-flex h-5 w-10 shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none ${
                  sharedTimeBudget ? 'bg-cyan-500' : 'bg-slate-700'
                }`}
              >
                <span
                  className={`pointer-events-none inline-block h-4 w-4 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                    sharedTimeBudget ? 'translate-x-5' : 'translate-x-0'
                  }`}
                />
              </button>
            </div>

            {/* Raw Reserve % Slider */}
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>--raw-reserve-pct</span>
                <span className="font-mono text-cyan-400">{rawReservePct}%</span>
              </div>
              <input
                type="range"
                min="0"
                max="90"
                step="5"
                value={rawReservePct}
                onChange={(e) => setRawReservePct(Number(e.target.value))}
                className="w-full accent-cyan-500 cursor-pointer"
              />
              <span className="text-[10px] text-slate-500">
                Guarantees candidate budget for raw search if concept fails
              </span>
            </div>

            {/* Time Allowance (ms) */}
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>--budget (Time Allowance)</span>
                <span className="font-mono text-indigo-400">{timeBudgetMs} ms</span>
              </div>
              <input
                type="range"
                min="1000"
                max="10000"
                step="500"
                value={timeBudgetMs}
                onChange={(e) => setTimeBudgetMs(Number(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
            </div>

            {/* Max Built Expansions */}
            <div>
              <div className="flex justify-between text-xs text-slate-300 mb-1">
                <span>--max-built (Candidate States)</span>
                <span className="font-mono text-purple-400">{maxBuilt} states</span>
              </div>
              <input
                type="range"
                min="20"
                max="500"
                step="20"
                value={maxBuilt}
                onChange={(e) => setMaxBuilt(Number(e.target.value))}
                className="w-full accent-purple-500 cursor-pointer"
              />
            </div>

            {/* Preloaded Library Toggle */}
            <div className="flex items-center justify-between pt-1">
              <span className="text-xs text-slate-300">Preload Concept Library</span>
              <input
                type="checkbox"
                checked={preloadedLibrary}
                onChange={(e) => setPreloadedLibrary(e.target.checked)}
                className="rounded accent-cyan-500 w-4 h-4 cursor-pointer"
              />
            </div>

            {/* Action button */}
            <button
              onClick={handleSynthesize}
              disabled={synthesizing}
              className="w-full py-2.5 px-4 rounded-xl bg-gradient-to-r from-cyan-600 via-indigo-600 to-purple-600 hover:from-cyan-500 hover:to-purple-500 text-white font-medium text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-indigo-500/20 disabled:opacity-50 cursor-pointer transition-all"
            >
              <Play className="w-4 h-4 fill-current" />
              <span>{synthesizing ? 'Synthesizing...' : 'Run Supsearch Synthesizer'}</span>
            </button>
          </div>
        </div>

        {/* Right: Synthesis Output & Execution Receipt */}
        <div className="lg:col-span-7 space-y-5">
          {synthesisResult ? (
            <div className="space-y-4">
              {/* Solution card */}
              <div className="p-5 rounded-2xl bg-slate-900/90 border border-slate-800 relative overflow-hidden">
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800/40">
                      {synthesisResult.taskId}
                    </span>
                    <span className="text-xs text-slate-400">
                      {synthesisResult.description}
                    </span>
                  </div>
                  <span className="px-2 py-0.5 rounded text-xs font-mono font-semibold bg-emerald-950/80 text-emerald-400 border border-emerald-700/50 flex items-center gap-1">
                    <CheckCircle className="w-3.5 h-3.5" />
                    {synthesisResult.status}
                  </span>
                </div>

                <div className="mt-2">
                  <span className="text-[11px] font-semibold text-slate-400 block mb-1">
                    Synthesized Affine λ-Term:
                  </span>
                  <div className="p-3 rounded-xl bg-slate-950 font-mono text-xs sm:text-sm text-cyan-300 border border-slate-800 overflow-x-auto selection:bg-cyan-900 selection:text-white">
                    {synthesisResult.solution}
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap gap-2 text-[11px] font-mono">
                  <span className="px-2 py-1 rounded bg-slate-800/80 text-slate-300">
                    MDL AST Gain: +{synthesisResult.receipt.mdlAstGain}x
                  </span>
                  <span className="px-2 py-1 rounded bg-slate-800/80 text-slate-300">
                    Composition Arity: {synthesisResult.receipt.compositionArity}
                  </span>
                  <span className="px-2 py-1 rounded bg-emerald-950/50 text-emerald-300 border border-emerald-800/40">
                    Dev Regression: 0
                  </span>
                  <span className="px-2 py-1 rounded bg-indigo-950/50 text-indigo-300 border border-indigo-800/40">
                    NBE Normal Form: Sound
                  </span>
                </div>
              </div>

              {/* v2.5.0 Detailed Budget Receipt */}
              <div className="p-5 rounded-2xl bg-slate-950/80 border border-cyan-500/30">
                <h3 className="text-xs font-mono font-bold text-cyan-400 uppercase tracking-wider mb-3 flex items-center gap-1.5">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  v2.5.0 Self-Reported Budget Receipt
                </h3>

                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-xs font-mono">
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">TOTAL ALLOWANCE</span>
                    <span className="text-white font-bold">{synthesisResult.receipt.totalTimeAllowanceMs} ms</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">TIME SPENT</span>
                    <span className="text-cyan-400 font-bold">{synthesisResult.receipt.timeSpentMs} ms</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">TIME REMAINING</span>
                    <span className="text-emerald-400 font-bold">{synthesisResult.receipt.timeRemainingMs} ms</span>
                  </div>
                  <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
                    <span className="text-slate-400 text-[10px] block">BUDGET POLICY</span>
                    <span className="text-indigo-400 font-bold">Shared Soft Deadline</span>
                  </div>
                </div>

                {/* Phase Comparison */}
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs">
                  {/* Concept Phase */}
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-slate-200">Phase 1: Concept-First Search</span>
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300">
                        {synthesisResult.receipt.phases.conceptPhase.result}
                      </span>
                    </div>
                    <div className="space-y-1 text-slate-400 font-mono text-[11px]">
                      <div>Allocated: {synthesisResult.receipt.phases.conceptPhase.budgetMs} ms</div>
                      <div>Spent: {synthesisResult.receipt.phases.conceptPhase.spentMs} ms</div>
                      <div>Expansions: {synthesisResult.receipt.phases.conceptPhase.expansions} states</div>
                    </div>
                  </div>

                  {/* Raw Fallback Phase */}
                  <div className="p-3 rounded-xl bg-slate-900/60 border border-slate-800">
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-semibold text-slate-200">Phase 2: Raw Fallback</span>
                      <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-indigo-950 text-indigo-300">
                        {synthesisResult.receipt.phases.rawFallbackPhase.result}
                      </span>
                    </div>
                    <div className="space-y-1 text-slate-400 font-mono text-[11px]">
                      <div>Budget: {synthesisResult.receipt.phases.rawFallbackPhase.budgetMs} ms</div>
                      <div>Spent: {synthesisResult.receipt.phases.rawFallbackPhase.spentMs} ms</div>
                      <div>Expansions: {synthesisResult.receipt.phases.rawFallbackPhase.expansions} states</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="h-full min-h-[320px] rounded-2xl bg-slate-900/40 border border-slate-800 border-dashed flex flex-col items-center justify-center p-8 text-center">
              <Cpu className="w-12 h-12 text-slate-700 mb-3 animate-pulse" />
              <h3 className="text-sm font-semibold text-slate-300">Synthesizer Standby</h3>
              <p className="text-xs text-slate-500 max-w-sm mt-1">
                Configure your search budget and click "Run Supsearch Synthesizer" to trigger the bottom-up enumerator.
              </p>
            </div>
          )}
        </div>
      </div>

      {/* Lambda Calculus NBE Normalizer Playground */}
      <div className="p-6 rounded-2xl bg-slate-900/70 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Code2 className="w-5 h-5 text-purple-400" />
              Pure λ-Calculus Evaluator &amp; Beta-Reduction Stepper
            </h2>
            <p className="text-xs text-slate-400">
              Run Normalization by Evaluation (NBE) and inspect reduction traces step by step.
            </p>
          </div>

          {/* Quick presets */}
          <div className="flex flex-wrap items-center gap-1.5">
            {evalPresets.map((p, idx) => (
              <button
                key={idx}
                onClick={() => {
                  setLambdaExpr(p.expr);
                  handleEvaluateLambda(p.expr);
                }}
                className="px-2.5 py-1 rounded-lg bg-slate-950 border border-slate-800 hover:border-purple-500/50 text-[11px] font-mono text-purple-300 hover:text-white transition-all cursor-pointer"
              >
                {p.label}
              </button>
            ))}
          </div>
        </div>

        {/* Input box */}
        <div className="flex gap-2">
          <input
            type="text"
            value={lambdaExpr}
            onChange={(e) => setLambdaExpr(e.target.value)}
            placeholder="e.g. (λx.λy.x)(a)(b)"
            className="flex-1 bg-slate-950 border border-slate-700 rounded-xl px-4 py-2.5 text-xs sm:text-sm font-mono text-cyan-300 focus:border-purple-500 focus:outline-none"
          />
          <button
            onClick={() => handleEvaluateLambda()}
            disabled={evaluating}
            className="px-5 py-2.5 rounded-xl bg-purple-600 hover:bg-purple-500 text-white font-medium text-xs sm:text-sm flex items-center gap-2 transition-all cursor-pointer disabled:opacity-50"
          >
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>Evaluate</span>
          </button>
        </div>

        {/* Evaluation Output */}
        {evalResult && (
          <div className="p-4 rounded-xl bg-slate-950 border border-purple-500/30 space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-mono font-semibold text-purple-300">
                Evaluation Trace ({evalResult.totalSteps} β-reduction steps):
              </span>
              <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                Normal Form Reached
              </span>
            </div>

            <div className="space-y-1.5 font-mono text-xs max-h-48 overflow-y-auto">
              {evalResult.steps.map((step, idx) => (
                <div key={idx} className="flex items-start gap-3 text-slate-300 py-0.5 border-b border-slate-900">
                  <span className="text-slate-600 select-none text-[10px] w-6 text-right">#{idx}</span>
                  <span className={idx === evalResult.steps.length - 1 ? 'text-emerald-400 font-bold' : 'text-slate-300'}>
                    {step}
                  </span>
                </div>
              ))}
            </div>

            <div className="pt-2 border-t border-slate-900 flex items-center justify-between text-xs font-mono">
              <span className="text-slate-400">Final Normal Form:</span>
              <span className="font-bold text-emerald-400 text-sm bg-slate-900 px-3 py-1 rounded border border-emerald-800/40">
                {evalResult.normalForm}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
