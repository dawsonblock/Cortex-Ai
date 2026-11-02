import React, { useState } from 'react';
import { 
  Trophy, 
  Clock, 
  Layers, 
  ShieldCheck, 
  ArrowRight, 
  Code2, 
  AlertTriangle,
  Zap,
  BarChart3,
  Search,
  CheckCircle2,
  Database,
  Sliders
} from 'lucide-react';
import { OverviewData } from '../types';

interface OverviewTabProps {
  overview: OverviewData | null;
  onNavigateToSynthesizer: (taskId?: string) => void;
  onNavigateToTests: () => void;
}

export const OverviewTab: React.FC<OverviewTabProps> = ({
  overview,
  onNavigateToSynthesizer,
  onNavigateToTests,
}) => {
  const [familyFilter, setFamilyFilter] = useState<'all' | '100' | 'partial' | 'wall'>('all');

  const leaderboard = [
    { rank: 1, name: 'Supsearch v2.5.0 (Pure Enumerative + DSL)', score: '108/120', pct: '90.0%', mechanism: 'Affine λ search, behavioral dedup, shared deadline', highlight: true },
    { rank: 1, name: 'GPT-5.3 Codex', score: '108/120', pct: '90.0%', mechanism: 'Massive code LLM + reasoning tokens', highlight: false },
    { rank: 1, name: 'Opus 4.6', score: '108/120', pct: '90.0%', mechanism: 'Frontier multi-modal reasoning LLM', highlight: false },
    { rank: 4, name: 'Opus 4.7 / Gemini 3.1 Pro', score: '106/120', pct: '88.3%', mechanism: 'Frontier generalist LLM', highlight: false },
    { rank: 5, name: 'GPT-5.4', score: '96/120', pct: '80.0%', mechanism: 'Frontier model', highlight: false },
    { rank: 6, name: 'GPT-5.5', score: '89/120', pct: '74.2%', mechanism: 'Frontier model', highlight: false },
    { rank: 7, name: 'Sonnet 4.6', score: '87/120', pct: '72.5%', mechanism: 'Frontier model', highlight: false },
  ];

  const families = overview?.families || [];

  const filteredFamilies = families.filter(f => {
    if (familyFilter === '100') return f.status === '100%';
    if (familyFilter === 'partial') return f.status.includes('90%');
    if (familyFilter === 'wall') return f.status.includes('0%');
    return true;
  });

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Hero Banner */}
      <div className="relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-900 via-indigo-950/70 to-slate-900 border border-indigo-500/30 p-6 sm:p-8 shadow-2xl">
        <div className="absolute top-0 right-0 -mr-16 -mt-16 w-80 h-80 bg-cyan-500/10 rounded-full blur-3xl pointer-events-none" />
        <div className="absolute bottom-0 left-1/3 -mb-20 w-80 h-80 bg-purple-500/10 rounded-full blur-3xl pointer-events-none" />

        <div className="relative z-10">
          <div className="flex flex-wrap items-center gap-2 mb-3">
            <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 flex items-center gap-1.5">
              <Trophy className="w-3.5 h-3.5 text-cyan-400" />
              LamBench TIE #1 CERTIFIED
            </span>
            <span className="px-2.5 py-1 rounded-md text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/40 flex items-center gap-1.5">
              <Zap className="w-3.5 h-3.5 text-purple-400" />
              Zero LLM / Zero Neural Weights
            </span>
            <span className="px-2.5 py-1 rounded-md text-xs font-mono text-emerald-400 bg-emerald-950/70 border border-emerald-600/40">
              v2.5.0 Work-Conserving Budget
            </span>
          </div>

          <h1 className="text-2xl sm:text-4xl font-extrabold tracking-tight text-white mb-3 leading-tight">
            Supsearch: Mathematical Program Synthesis at Frontier Scale
          </h1>
          <p className="text-slate-300 text-sm sm:text-base max-w-3xl leading-relaxed mb-6">
            A pure enumerative synthesizer with bottom-up behavioral deduplication, Church &amp; Scott value recognizers, 
            affine λ standard library compilation, and a work-conserving shared search deadline across concept search and raw fallback.
          </p>

          <div className="flex flex-wrap items-center gap-3">
            <button
              onClick={() => onNavigateToSynthesizer('cnat_add')}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-gradient-to-r from-cyan-500 to-indigo-600 text-white font-medium text-sm shadow-lg shadow-cyan-500/25 hover:from-cyan-400 hover:to-indigo-500 transition-all cursor-pointer"
            >
              <Zap className="w-4 h-4" />
              <span>Launch Interactive Synthesizer</span>
            </button>
            <button
              onClick={onNavigateToTests}
              className="flex items-center gap-2 px-4 py-2.5 rounded-xl bg-slate-800/80 hover:bg-slate-700/80 text-slate-200 border border-slate-700 text-sm font-medium transition-all cursor-pointer"
            >
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <span>Run Validation Suite</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Metric Highlights */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-cyan-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Certified Tasks</span>
            <Trophy className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white font-mono">108</span>
            <span className="text-slate-400 text-sm">/ 120 (90%)</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Certified by LamBench referee (<code className="text-cyan-300">bun src/check.ts</code>)
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-indigo-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Execution Speed</span>
            <Clock className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white font-mono">1.3s</span>
            <span className="text-slate-400 text-sm">avg / task</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            3m 27s total run across all 120 tasks on single Apple Silicon core
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-emerald-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">v2.5.0 Time Budget</span>
            <ShieldCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-black text-emerald-400 font-mono">Shared</span>
            <span className="text-slate-400 text-sm">Conservation</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Soft deadline shared across concept search &amp; verified raw fallback
          </p>
        </div>

        <div className="p-5 rounded-xl bg-slate-900/80 border border-slate-800 hover:border-purple-500/40 transition-all">
          <div className="flex items-center justify-between text-slate-400 mb-2">
            <span className="text-xs font-medium uppercase tracking-wider">Family Mastery</span>
            <Layers className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black text-white font-mono">11 / 12</span>
            <span className="text-slate-400 text-sm">families</span>
          </div>
          <p className="text-xs text-slate-400 mt-2">
            Complete solution of nats, lists, tuples, trees &amp; ADTs
          </p>
        </div>
      </div>

      {/* 4-Phase Architecture Pipeline */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6">
        <h2 className="text-lg font-bold text-white mb-2 flex items-center gap-2">
          <Code2 className="w-5 h-5 text-cyan-400" />
          The 4-Phase Synthesis Architecture
        </h2>
        <p className="text-xs sm:text-sm text-slate-400 mb-6">
          How Supsearch synthesizes sound, verified lambda expressions without generative hallucinations or approximations:
        </p>

        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="p-4 rounded-xl bg-slate-950/70 border border-cyan-500/30 relative">
            <div className="w-7 h-7 rounded-lg bg-cyan-500/20 text-cyan-400 font-mono font-bold text-xs flex items-center justify-center mb-3">
              01
            </div>
            <h3 className="font-semibold text-white text-sm mb-1">Shape Decoder</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Test inputs and outputs are pure λ-normal forms. Recognizers decode Church/Scott nats, lists, binary trees, and opaque symbols into native host representations.
            </p>
            <div className="mt-3 font-mono text-[11px] text-cyan-300 bg-slate-900/90 px-2 py-1 rounded">
              λ-NF ➔ Native Val
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-indigo-500/30 relative">
            <div className="w-7 h-7 rounded-lg bg-indigo-500/20 text-indigo-400 font-mono font-bold text-xs flex items-center justify-center mb-3">
              02
            </div>
            <h3 className="font-semibold text-white text-sm mb-1">Bottom-Up Search</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Enumerates expressions over a ~40-operator typed DSL with behavioral deduplication. Evaluates candidate terms on examples, pruning semantically redundant states.
            </p>
            <div className="mt-3 font-mono text-[11px] text-indigo-300 bg-slate-900/90 px-2 py-1 rounded">
              Behavioral Dedup
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-purple-500/30 relative">
            <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-400 font-mono font-bold text-xs flex items-center justify-center mb-3">
              03
            </div>
            <h3 className="font-semibold text-white text-sm mb-1">DSL Compiler</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Compiles discovered DSL operations into pure affine λ-calculus using a verified ~90-def stdlib (Scott-encoded internals, explicit <code className="text-purple-300">@sdup</code> duplication).
            </p>
            <div className="mt-3 font-mono text-[11px] text-purple-300 bg-slate-900/90 px-2 py-1 rounded">
              DSL ➔ Affine λ Term
            </div>
          </div>

          <div className="p-4 rounded-xl bg-slate-950/70 border border-emerald-500/30 relative">
            <div className="w-7 h-7 rounded-lg bg-emerald-500/20 text-emerald-400 font-mono font-bold text-xs flex items-center justify-center mb-3">
              04
            </div>
            <h3 className="font-semibold text-white text-sm mb-1">Referee Normalizer</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Evaluates the compiled lambda term against all test vectors via Normalization by Evaluation (NBE). Soundness is formally validated: no false positive escapes.
            </p>
            <div className="mt-3 font-mono text-[11px] text-emerald-300 bg-slate-900/90 px-2 py-1 rounded">
              NBE Normalizer
            </div>
          </div>
        </div>
      </div>

      {/* Leaderboard Table & The Algo Wall Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
        {/* Leaderboard Table */}
        <div className="lg:col-span-7 rounded-2xl bg-slate-900/70 border border-slate-800 p-6">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan-400" />
                LamBench Benchmark Leaderboard
              </h2>
              <p className="text-xs text-slate-400">
                Official LamBench synthesis referee certified score
              </p>
            </div>
            <span className="text-xs font-mono text-cyan-400 bg-cyan-950/50 px-2.5 py-1 rounded border border-cyan-800/40">
              120 Total Tasks
            </span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950/60 text-slate-400 border-b border-slate-800 font-mono">
                <tr>
                  <th className="py-2.5 px-3">#</th>
                  <th className="py-2.5 px-3">Model / System</th>
                  <th className="py-2.5 px-3">Certified</th>
                  <th className="py-2.5 px-3">Rate</th>
                  <th className="py-2.5 px-3">Mechanism</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50 font-mono">
                {leaderboard.map((item, idx) => (
                  <tr
                    key={idx}
                    className={`transition-colors ${
                      item.highlight 
                        ? 'bg-cyan-950/30 text-cyan-200 font-semibold' 
                        : 'hover:bg-slate-800/30 text-slate-300'
                    }`}
                  >
                    <td className="py-2.5 px-3">
                      {item.highlight ? (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-cyan-500/20 text-cyan-400 text-[10px]">
                          ★
                        </span>
                      ) : (
                        item.rank
                      )}
                    </td>
                    <td className="py-2.5 px-3 font-sans font-medium text-slate-100 flex items-center gap-1.5">
                      {item.name}
                      {item.highlight && (
                        <span className="text-[10px] px-1 py-0.2 rounded bg-cyan-500/30 text-cyan-300 border border-cyan-500/40">
                          Active
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-3 text-white font-bold">{item.score}</td>
                    <td className="py-2.5 px-3 text-emerald-400">{item.pct}</td>
                    <td className="py-2.5 px-3 text-slate-400 font-sans text-[11px] truncate max-w-xs">
                      {item.mechanism}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* The Algo Wall Analysis */}
        <div className="lg:col-span-5 rounded-2xl bg-slate-900/70 border border-slate-800 p-6 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-base font-bold text-white flex items-center gap-2">
                <AlertTriangle className="w-4 h-4 text-amber-400" />
                The "Algo Wall" (12 Unsolved Tasks)
              </h2>
              <span className="px-2 py-0.5 rounded bg-amber-950/80 text-amber-300 text-[10px] font-mono border border-amber-700/50">
                0/12 Solved
              </span>
            </div>
            <p className="text-xs text-slate-300 leading-relaxed mb-4">
              While Supsearch achieves 108/120 on LamBench, the remaining 12 tasks hit an explicit architectural barrier:
            </p>

            <div className="space-y-2 mb-4">
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300">
                <span className="font-mono text-cyan-300 font-semibold">Turing-Complete Algorithms:</span> Brainfuck interpreter, SAT solver, Sudoku solver, Maze pathfinder.
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300">
                <span className="font-mono text-purple-300 font-semibold">Graph &amp; Geometry:</span> Minimum Spanning Tree (MST), Convex Hull, Traveling Salesperson (TSP).
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 text-xs text-slate-300">
                <span className="font-mono text-indigo-300 font-semibold">Meta-Evaluators:</span> Full λ-term evaluator, Typed descriptor checker, Balanced-ternary FFT.
              </div>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              <strong className="text-slate-300">Why?</strong> These tasks require unbounded state search and general recursion. Supsearch’s affine DSL and bounded enumeration provably cannot fit complex backtracking loops within reasonable candidate bounds.
            </p>
          </div>

          <div className="mt-4 pt-4 border-t border-slate-800 flex items-center justify-between">
            <span className="text-xs text-slate-400">Explore task benchmarks:</span>
            <button
              onClick={() => onNavigateToSynthesizer('algo_sat')}
              className="text-xs text-cyan-400 hover:text-cyan-300 font-medium flex items-center gap-1 cursor-pointer"
            >
              <span>Inspect Wall Task</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {/* Task Families Matrix */}
      <div className="rounded-2xl bg-slate-900/60 border border-slate-800 p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Database className="w-4 h-4 text-cyan-400" />
              12 LamBench Task Families
            </h2>
            <p className="text-xs text-slate-400">
              Categorized by data structure representations and synthesis mechanisms
            </p>
          </div>

          {/* Filter Pills */}
          <div className="flex items-center gap-1.5 p-1 bg-slate-950 rounded-xl border border-slate-800 text-xs">
            <button
              onClick={() => setFamilyFilter('all')}
              className={`px-3 py-1 rounded-lg transition-all ${
                familyFilter === 'all' ? 'bg-cyan-500/20 text-cyan-300 font-medium' : 'text-slate-400 hover:text-white'
              }`}
            >
              All (12)
            </button>
            <button
              onClick={() => setFamilyFilter('100')}
              className={`px-3 py-1 rounded-lg transition-all ${
                familyFilter === '100' ? 'bg-emerald-500/20 text-emerald-300 font-medium' : 'text-slate-400 hover:text-white'
              }`}
            >
              100% Solved (9)
            </button>
            <button
              onClick={() => setFamilyFilter('partial')}
              className={`px-3 py-1 rounded-lg transition-all ${
                familyFilter === 'partial' ? 'bg-indigo-500/20 text-indigo-300 font-medium' : 'text-slate-400 hover:text-white'
              }`}
            >
              90% Solved (2)
            </button>
            <button
              onClick={() => setFamilyFilter('wall')}
              className={`px-3 py-1 rounded-lg transition-all ${
                familyFilter === 'wall' ? 'bg-amber-500/20 text-amber-300 font-medium' : 'text-slate-400 hover:text-white'
              }`}
            >
              The Wall (1)
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredFamilies.map((family, idx) => (
            <div
              key={idx}
              className="p-4 rounded-xl bg-slate-950/60 border border-slate-800/80 hover:border-slate-700 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-center justify-between mb-2">
                  <span className="font-mono font-bold text-sm text-cyan-400 bg-cyan-950/40 px-2 py-0.5 rounded border border-cyan-800/40">
                    {family.name}
                  </span>
                  <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                    family.status === '100%' 
                      ? 'bg-emerald-950/60 text-emerald-400 border border-emerald-800/40' 
                      : family.status.includes('90%')
                      ? 'bg-indigo-950/60 text-indigo-300 border border-indigo-800/40'
                      : 'bg-amber-950/60 text-amber-300 border border-amber-800/40'
                  }`}>
                    {family.status} ({family.solved}/{family.total})
                  </span>
                </div>
                <p className="text-xs text-slate-300 mb-3">
                  {family.description}
                </p>
              </div>

              <div className="pt-3 border-t border-slate-900 flex items-center justify-between">
                <span className="text-[11px] text-slate-400 font-mono">
                  {family.solved} solved
                </span>
                <button
                  onClick={() => onNavigateToSynthesizer(`${family.name}_add`)}
                  className="text-xs text-indigo-400 hover:text-indigo-300 flex items-center gap-1 font-medium cursor-pointer"
                >
                  <span>Synthesize</span>
                  <ArrowRight className="w-3 h-3" />
                </button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* v2.5.0 Shared Deadline Technical Detail */}
      <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-cyan-950/30 to-slate-900 border border-cyan-500/30 p-6">
        <div className="flex items-start gap-4">
          <div className="p-3 rounded-xl bg-cyan-500/20 text-cyan-400 mt-1">
            <Sliders className="w-6 h-6" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white mb-1">
              v2.5.0 Core Innovation: Work-Conserving Shared Search Time
            </h3>
            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed mb-3">
              In v2.3 and earlier, candidate expansion limits were capped, but a failed concept-first search would leave raw enumeration with an independent full wall-clock allocation. v2.5.0 introduces <code className="text-cyan-300 font-mono">--shared-time-budget true</code>:
            </p>
            <ul className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs text-slate-400 font-mono">
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>Single shared deadline across concept &amp; raw fallback</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>Zero-time raw fallback strictly rejected</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>Self-reported timing receipts audited by Python verifiers</span>
              </li>
              <li className="flex items-center gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <span>Nonempty-library native fallback probe in CI wiring</span>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};
