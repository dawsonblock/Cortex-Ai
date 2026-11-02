import React from 'react';
import { 
  Cpu, 
  Terminal, 
  FileCode, 
  Sparkles, 
  Activity, 
  CheckCircle2, 
  ShieldCheck,
  Search,
  Zap,
  SlidersHorizontal
} from 'lucide-react';

interface NavbarProps {
  activeTab: 'overview' | 'explorer' | 'synthesizer' | 'tests' | 'code' | 'image-studio';
  setActiveTab: (tab: 'overview' | 'explorer' | 'synthesizer' | 'tests' | 'code' | 'image-studio') => void;
  serverOnline: boolean;
  onOpenSearch: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ 
  activeTab, 
  setActiveTab, 
  serverOnline,
  onOpenSearch 
}) => {
  return (
    <header className="sticky top-0 z-40 bg-slate-950/90 backdrop-blur-md border-b border-slate-800 text-white">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & title */}
          <div className="flex items-center gap-3">
            <div 
              onClick={() => setActiveTab('overview')}
              className="w-10 h-10 rounded-xl bg-gradient-to-tr from-cyan-600 via-indigo-600 to-purple-600 flex items-center justify-center shadow-lg shadow-cyan-500/20 ring-1 ring-cyan-400/30 cursor-pointer"
            >
              <span className="font-mono text-xl font-black tracking-tight text-white">λ</span>
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span 
                  onClick={() => setActiveTab('overview')}
                  className="font-bold text-lg tracking-tight bg-gradient-to-r from-cyan-300 via-blue-200 to-indigo-300 bg-clip-text text-transparent cursor-pointer"
                >
                  SUPSEARCH
                </span>
                <span className="px-1.5 py-0.5 text-[11px] font-mono font-semibold rounded bg-cyan-950/80 text-cyan-400 border border-cyan-700/50">
                  v2.5.0
                </span>
              </div>
              <p className="text-[11px] text-slate-400 hidden sm:block">
                Work-Conserving Shared Search Time • LamBench 108/120 Leader
              </p>
            </div>
          </div>

          {/* Quick Search Hotkey Button */}
          <div className="flex items-center gap-2">
            <button
              onClick={onOpenSearch}
              className="hidden md:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-900 hover:bg-slate-800 border border-slate-700/80 text-slate-400 hover:text-slate-200 text-xs font-mono transition-all cursor-pointer shadow-inner"
              title="Global Quick Search (Cmd+K)"
            >
              <Search className="w-3.5 h-3.5 text-cyan-400" />
              <span>Search tasks, code, visuals...</span>
              <kbd className="px-1.5 py-0.5 rounded bg-slate-950 text-[10px] text-slate-400 border border-slate-800">
                ⌘K
              </kbd>
            </button>

            {/* Quick Metrics Badges */}
            <div className="hidden lg:flex items-center gap-2">
              <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-slate-900 border border-emerald-500/30 text-emerald-400 text-xs font-mono">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span>108/120</span>
              </div>
              <div className="flex items-center gap-1 px-2 py-1 rounded-full bg-slate-900 border border-slate-700 text-slate-300 text-xs">
                <span className={`w-2 h-2 rounded-full ${serverOnline ? 'bg-emerald-500 shadow-sm shadow-emerald-400' : 'bg-amber-500'}`} />
                <span className="text-[11px] font-mono">{serverOnline ? 'Online' : 'Reconnecting'}</span>
              </div>
            </div>
          </div>

          {/* Tab Navigation */}
          <nav className="flex items-center space-x-1 sm:space-x-1.5">
            <button
              onClick={() => setActiveTab('overview')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'overview'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Activity className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Overview</span>
            </button>

            <button
              onClick={() => setActiveTab('explorer')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'explorer'
                  ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm shadow-cyan-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Search className="w-3.5 h-3.5" />
              <span>Tasks</span>
              <span className="px-1 text-[9px] bg-slate-800 text-slate-300 rounded font-mono hidden md:inline">
                120
              </span>
            </button>

            <button
              onClick={() => setActiveTab('synthesizer')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'synthesizer'
                  ? 'bg-indigo-500/20 text-indigo-300 border border-indigo-500/40 shadow-sm shadow-indigo-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Cpu className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Synthesizer</span>
            </button>

            <button
              onClick={() => setActiveTab('tests')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'tests'
                  ? 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm shadow-emerald-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <Terminal className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Tests</span>
            </button>

            <button
              onClick={() => setActiveTab('code')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                activeTab === 'code'
                  ? 'bg-blue-500/20 text-blue-300 border border-blue-500/40 shadow-sm shadow-blue-500/10'
                  : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
              }`}
            >
              <FileCode className="w-3.5 h-3.5" />
              <span className="hidden md:inline">Code</span>
            </button>

            <button
              onClick={() => setActiveTab('image-studio')}
              className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium transition-all relative ${
                activeTab === 'image-studio'
                  ? 'bg-gradient-to-r from-purple-500/30 to-pink-500/30 text-pink-200 border border-pink-500/50 shadow-sm shadow-pink-500/20'
                  : 'text-slate-400 hover:text-pink-300 hover:bg-slate-900 border border-transparent'
              }`}
            >
              <Sparkles className="w-3.5 h-3.5 text-pink-400 animate-pulse" />
              <span className="font-semibold">AI Studio</span>
            </button>
          </nav>
        </div>
      </div>
    </header>
  );
};
