import React, { useState, useEffect, useRef } from 'react';
import { 
  Search, 
  X, 
  Cpu, 
  Sparkles, 
  FileCode, 
  Terminal, 
  ArrowRight, 
  CheckCircle2, 
  AlertTriangle,
  Layers,
  Clock
} from 'lucide-react';
import { TaskItem, GeneratedImageItem } from '../types';

interface GlobalSearchModalProps {
  isOpen: boolean;
  onClose: () => void;
  tasks: TaskItem[];
  images: GeneratedImageItem[];
  onSelectTask: (taskId: string) => void;
  onSelectFile: (filePath: string) => void;
  onSelectImage: (image: GeneratedImageItem) => void;
  onSelectTab: (tab: 'overview' | 'explorer' | 'synthesizer' | 'tests' | 'code' | 'image-studio') => void;
}

export const GlobalSearchModal: React.FC<GlobalSearchModalProps> = ({
  isOpen,
  onClose,
  tasks,
  images,
  onSelectTask,
  onSelectFile,
  onSelectImage,
  onSelectTab
}) => {
  const [query, setQuery] = useState('');
  const [activeCategory, setActiveCategory] = useState<'all' | 'tasks' | 'images' | 'code' | 'tests'>('all');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 50);
    } else {
      setQuery('');
    }
  }, [isOpen]);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        if (isOpen) onClose();
      }
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const q = query.trim().toLowerCase();

  // Filter tasks
  const matchedTasks = tasks.filter(t => 
    !q || 
    t.id.toLowerCase().includes(q) ||
    t.name.toLowerCase().includes(q) ||
    t.description.toLowerCase().includes(q) ||
    t.category.toLowerCase().includes(q) ||
    t.encoding.toLowerCase().includes(q) ||
    t.tags.some(tag => tag.toLowerCase().includes(q))
  ).slice(0, 8);

  // Filter images
  const matchedImages = images.filter(img => 
    !q || 
    img.prompt.toLowerCase().includes(q) ||
    img.model.toLowerCase().includes(q) ||
    (img.isEdited ? 'edited' : 'created').includes(q)
  ).slice(0, 4);

  // Static files list
  const codeFiles = [
    { path: 'src/search_budget.rs', desc: 'Work-conserving shared search time budget (v2.5.0)', type: 'rust' },
    { path: 'src/learning.rs', desc: 'Learning controller, admission gate & concept mining', type: 'rust' },
    { path: 'src/mdl.rs', desc: 'Minimum Description Length & AST compression gain', type: 'rust' },
    { path: 'src/bank.rs', desc: 'Bottom-up enumerator & raw lambda state bank', type: 'rust' },
    { path: 'src/main.rs', desc: 'CLI entry point and driver for grow/mine/learn/evaluate', type: 'rust' },
    { path: 'docs/V250_SHARED_DEADLINE.md', desc: 'Formal specification of the shared wall-clock allowance', type: 'doc' },
    { path: 'docs/ARCHITECTURE.md', desc: 'Architecture, 4-phase data flow & threat model', type: 'doc' },
    { path: 'RELEASE_NOTES.md', desc: 'Full version release notes v1.0 through v2.5.0', type: 'doc' },
  ];

  const matchedCode = codeFiles.filter(f =>
    !q ||
    f.path.toLowerCase().includes(q) ||
    f.desc.toLowerCase().includes(q)
  );

  // Static test modules
  const testModules = [
    { id: 'test_v250.py', desc: 'Shared search time allowance & zero-time raw fallback tests' },
    { id: 'test_v240.py', desc: 'Nonempty-library native fallback qualification probe' },
    { id: 'test_v230.py', desc: 'Reserved raw fallback candidate allocation limits' },
    { id: 'test_v220.py', desc: 'Concept quality, admission audit & AST MDL gain' },
    { id: 'test_qualified_pipeline.py', desc: 'End-to-end task pipeline protocol qualification' },
  ];

  const matchedTests = testModules.filter(t =>
    !q ||
    t.id.toLowerCase().includes(q) ||
    t.desc.toLowerCase().includes(q)
  );

  const totalMatches = 
    (activeCategory === 'all' || activeCategory === 'tasks' ? matchedTasks.length : 0) +
    (activeCategory === 'all' || activeCategory === 'images' ? matchedImages.length : 0) +
    (activeCategory === 'all' || activeCategory === 'code' ? matchedCode.length : 0) +
    (activeCategory === 'all' || activeCategory === 'tests' ? matchedTests.length : 0);

  return (
    <div 
      className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-start justify-center pt-16 sm:pt-24 p-4"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-2xl bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl overflow-hidden flex flex-col max-h-[80vh] animate-in fade-in zoom-in-95 duration-150"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Search Input Bar */}
        <div className="p-4 border-b border-slate-800 flex items-center gap-3 bg-slate-950/80">
          <Search className="w-5 h-5 text-cyan-400 shrink-0" />
          <input
            ref={inputRef}
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search 120 LamBench tasks, code files, tests, or AI visuals..."
            className="flex-1 bg-transparent text-sm sm:text-base text-white placeholder-slate-500 focus:outline-none"
          />
          {query && (
            <button 
              onClick={() => setQuery('')}
              className="p-1 rounded-md text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
          <span className="hidden sm:inline-block px-2 py-0.5 rounded bg-slate-800 text-[11px] font-mono text-slate-400 border border-slate-700">
            ESC to close
          </span>
        </div>

        {/* Category Filter Pills */}
        <div className="px-4 py-2 border-b border-slate-800/80 bg-slate-900/50 flex items-center gap-1.5 overflow-x-auto text-xs">
          <button
            onClick={() => setActiveCategory('all')}
            className={`px-2.5 py-1 rounded-lg transition-all ${
              activeCategory === 'all' 
                ? 'bg-cyan-500/20 text-cyan-300 font-semibold border border-cyan-500/40' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            All Results
          </button>
          <button
            onClick={() => setActiveCategory('tasks')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeCategory === 'tasks' 
                ? 'bg-indigo-500/20 text-indigo-300 font-semibold border border-indigo-500/40' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Cpu className="w-3 h-3" />
            <span>Tasks ({matchedTasks.length})</span>
          </button>
          <button
            onClick={() => setActiveCategory('images')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeCategory === 'images' 
                ? 'bg-pink-500/20 text-pink-300 font-semibold border border-pink-500/40' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Sparkles className="w-3 h-3" />
            <span>AI Images ({matchedImages.length})</span>
          </button>
          <button
            onClick={() => setActiveCategory('code')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeCategory === 'code' 
                ? 'bg-blue-500/20 text-blue-300 font-semibold border border-blue-500/40' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <FileCode className="w-3 h-3" />
            <span>Code ({matchedCode.length})</span>
          </button>
          <button
            onClick={() => setActiveCategory('tests')}
            className={`px-2.5 py-1 rounded-lg transition-all flex items-center gap-1 ${
              activeCategory === 'tests' 
                ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/40' 
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <Terminal className="w-3 h-3" />
            <span>Tests ({matchedTests.length})</span>
          </button>
        </div>

        {/* Results List */}
        <div className="flex-1 overflow-y-auto p-3 space-y-4">
          {totalMatches === 0 ? (
            <div className="py-12 text-center text-slate-500">
              <p className="text-sm">No matches found for "{query}"</p>
              <p className="text-xs mt-1 text-slate-600">
                Try searching for arithmetic, church, list, tree, sat, or lambda.
              </p>
            </div>
          ) : (
            <>
              {/* Tasks Section */}
              {(activeCategory === 'all' || activeCategory === 'tasks') && matchedTasks.length > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 mb-1.5">
                    <span>LamBench Synthesis Tasks</span>
                    <span>{matchedTasks.length} found</span>
                  </div>
                  <div className="space-y-1">
                    {matchedTasks.map(t => (
                      <div
                        key={t.id}
                        onClick={() => {
                          onSelectTask(t.id);
                          onClose();
                        }}
                        className="p-2.5 rounded-xl hover:bg-slate-800/70 border border-transparent hover:border-indigo-500/30 transition-all flex items-center justify-between gap-3 cursor-pointer group"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-8 h-8 rounded-lg bg-indigo-950/70 text-indigo-400 flex items-center justify-center shrink-0 border border-indigo-800/40 font-mono text-xs font-bold">
                            λ
                          </div>
                          <div className="min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs font-bold text-white group-hover:text-cyan-300 transition-colors truncate">
                                {t.name}
                              </span>
                              <span className={`text-[10px] font-mono px-1.5 rounded ${
                                t.status === 'SOLVED'
                                  ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800'
                                  : 'bg-amber-950/80 text-amber-400 border border-amber-800'
                              }`}>
                                {t.status === 'SOLVED' ? 'Certified' : 'Wall'}
                              </span>
                            </div>
                            <p className="text-xs text-slate-400 truncate">
                              {t.description}
                            </p>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className="text-[11px] font-mono text-slate-500 hidden sm:inline">
                            {t.category}
                          </span>
                          <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-cyan-400 transition-colors" />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Images Section */}
              {(activeCategory === 'all' || activeCategory === 'images') && matchedImages.length > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 mb-1.5">
                    <span>AI Visual Studio Generations</span>
                    <span>{matchedImages.length} found</span>
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {matchedImages.map(img => (
                      <div
                        key={img.id}
                        onClick={() => {
                          onSelectImage(img);
                          onClose();
                        }}
                        className="p-2 rounded-xl bg-slate-950/60 hover:bg-slate-800/70 border border-slate-800 hover:border-pink-500/40 transition-all flex items-center gap-3 cursor-pointer group"
                      >
                        <img
                          src={img.imageUrl}
                          alt={img.prompt}
                          className="w-12 h-12 rounded-lg object-cover bg-slate-900 shrink-0"
                        />
                        <div className="min-w-0 flex-1">
                          <p className="text-xs text-slate-200 group-hover:text-pink-300 transition-colors line-clamp-2">
                            {img.prompt}
                          </p>
                          <div className="flex items-center gap-2 mt-1 text-[10px] text-slate-500 font-mono">
                            <span>{img.aspectRatio}</span>
                            <span>•</span>
                            <span className="text-pink-400">{img.isEdited ? 'Edited' : 'Created'}</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Code Files Section */}
              {(activeCategory === 'all' || activeCategory === 'code') && matchedCode.length > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 mb-1.5">
                    <span>Codebase &amp; Architecture Documents</span>
                    <span>{matchedCode.length} found</span>
                  </div>
                  <div className="space-y-1">
                    {matchedCode.map(f => (
                      <div
                        key={f.path}
                        onClick={() => {
                          onSelectFile(f.path);
                          onClose();
                        }}
                        className="p-2.5 rounded-xl hover:bg-slate-800/70 border border-transparent hover:border-blue-500/30 transition-all flex items-center justify-between gap-3 cursor-pointer group"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <FileCode className="w-4 h-4 text-blue-400 shrink-0" />
                          <div className="min-w-0">
                            <span className="font-mono text-xs font-semibold text-white group-hover:text-blue-300 transition-colors truncate block">
                              {f.path}
                            </span>
                            <span className="text-xs text-slate-400 truncate block">
                              {f.desc}
                            </span>
                          </div>
                        </div>
                        <ArrowRight className="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors shrink-0" />
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Test Suites Section */}
              {(activeCategory === 'all' || activeCategory === 'tests') && matchedTests.length > 0 && (
                <div>
                  <div className="flex items-center justify-between text-[11px] font-mono uppercase tracking-wider text-slate-400 px-2 mb-1.5">
                    <span>Validation Test Suites</span>
                    <span>{matchedTests.length} found</span>
                  </div>
                  <div className="space-y-1">
                    {matchedTests.map(t => (
                      <div
                        key={t.id}
                        onClick={() => {
                          onSelectTab('tests');
                          onClose();
                        }}
                        className="p-2.5 rounded-xl hover:bg-slate-800/70 border border-transparent hover:border-emerald-500/30 transition-all flex items-center justify-between gap-3 cursor-pointer group"
                      >
                        <div className="flex items-center gap-3 min-w-0">
                          <Terminal className="w-4 h-4 text-emerald-400 shrink-0" />
                          <div className="min-w-0">
                            <span className="font-mono text-xs font-semibold text-white group-hover:text-emerald-300 transition-colors truncate block">
                              {t.id}
                            </span>
                            <span className="text-xs text-slate-400 truncate block">
                              {t.desc}
                            </span>
                          </div>
                        </div>
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-emerald-950/70 text-emerald-400 border border-emerald-800/40 shrink-0">
                          Executable
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer shortcuts */}
        <div className="p-3 bg-slate-950/90 border-t border-slate-800 flex items-center justify-between text-xs text-slate-500 font-mono">
          <div className="flex items-center gap-3">
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
            <span>ESC Close</span>
          </div>
          <span>120 Certified LamBench Tasks</span>
        </div>
      </div>
    </div>
  );
};
