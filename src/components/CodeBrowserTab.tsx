import React, { useState, useEffect } from 'react';
import { 
  FileCode, 
  Search, 
  Copy, 
  Check, 
  BookOpen, 
  Layers, 
  FolderTree,
  Terminal,
  FileText
} from 'lucide-react';

export const CodeBrowserTab: React.FC = () => {
  const [selectedPath, setSelectedPath] = useState<string>('src/search_budget.rs');
  const [fileContent, setFileContent] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);
  const [searchTerm, setSearchTerm] = useState<string>('');

  const keyFiles = [
    { path: 'src/search_budget.rs', label: 'src/search_budget.rs', type: 'rust', badge: 'v2.5.0 Core' },
    { path: 'src/learning.rs', label: 'src/learning.rs', type: 'rust', badge: 'Promotion Gate' },
    { path: 'src/mdl.rs', label: 'src/mdl.rs', type: 'rust', badge: 'AST Compression' },
    { path: 'src/bank.rs', label: 'src/bank.rs', type: 'rust', badge: 'Enumerator' },
    { path: 'src/main.rs', label: 'src/main.rs', type: 'rust', badge: 'CLI Entry' },
    { path: 'docs/V250_SHARED_DEADLINE.md', label: 'docs/V250_SHARED_DEADLINE.md', type: 'doc', badge: 'Spec' },
    { path: 'docs/ARCHITECTURE.md', label: 'docs/ARCHITECTURE.md', type: 'doc', badge: 'Architecture' },
    { path: 'RELEASE_NOTES.md', label: 'RELEASE_NOTES.md', type: 'doc', badge: 'Release' },
    { path: 'bench/cnat_add.tsk', label: 'bench/cnat_add.tsk', type: 'task', badge: 'LamBench' },
    { path: 'bench/clst_map.tsk', label: 'bench/clst_map.tsk', type: 'task', badge: 'LamBench' },
    { path: 'bench/ctre_rev.tsk', label: 'bench/ctre_rev.tsk', type: 'task', badge: 'LamBench' },
  ];

  useEffect(() => {
    setLoading(true);
    fetch(`/api/supsearch/file?path=${encodeURIComponent(selectedPath)}`)
      .then(res => res.json())
      .then(data => {
        if (data.content) {
          setFileContent(data.content);
        } else {
          setFileContent(`// Error loading file: ${data.error || 'Unknown error'}`);
        }
      })
      .catch(err => setFileContent(`// Error: ${err.message}`))
      .finally(() => setLoading(false));
  }, [selectedPath]);

  const handleCopy = () => {
    navigator.clipboard.writeText(fileContent);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const lines = fileContent.split('\n');
  const filteredLines = lines.map((line, idx) => ({
    lineNum: idx + 1,
    text: line,
    matches: searchTerm && line.toLowerCase().includes(searchTerm.toLowerCase())
  }));

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-white flex items-center gap-2">
          <FileCode className="w-6 h-6 text-blue-400" />
          Codebase &amp; Architecture Explorer
        </h1>
        <p className="text-xs sm:text-sm text-slate-400 mt-1">
          Inspect genuine Rust synthesis engine sources, v2.5.0 shared budget modules, and LamBench task definitions.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: File Picker Navigation */}
        <div className="lg:col-span-4 space-y-4">
          <div className="p-4 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-2">
            <h2 className="text-xs font-mono font-semibold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
              <FolderTree className="w-4 h-4 text-blue-400" />
              Source &amp; Documentation Files
            </h2>

            <div className="space-y-1.5 max-h-[500px] overflow-y-auto">
              {keyFiles.map((f) => (
                <button
                  key={f.path}
                  onClick={() => setSelectedPath(f.path)}
                  className={`w-full text-left p-2.5 rounded-xl text-xs font-mono transition-all flex items-center justify-between gap-2 cursor-pointer ${
                    selectedPath === f.path
                      ? 'bg-blue-600/20 text-blue-300 border border-blue-500/40 font-semibold'
                      : 'bg-slate-950/60 text-slate-400 hover:text-slate-200 border border-slate-900 hover:border-slate-800'
                  }`}
                >
                  <div className="flex items-center gap-2 min-w-0">
                    {f.type === 'rust' ? (
                      <FileCode className="w-3.5 h-3.5 text-orange-400 shrink-0" />
                    ) : f.type === 'doc' ? (
                      <BookOpen className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                    ) : (
                      <FileText className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                    )}
                    <span className="truncate">{f.label}</span>
                  </div>
                  <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-900 text-slate-400 border border-slate-800 shrink-0">
                    {f.badge}
                  </span>
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Right: Code Viewer */}
        <div className="lg:col-span-8 space-y-3">
          <div className="rounded-2xl bg-slate-950 border border-slate-800 overflow-hidden shadow-2xl flex flex-col">
            {/* Viewer Header */}
            <div className="p-3 bg-slate-900 border-b border-slate-800 flex flex-wrap items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <FileCode className="w-4 h-4 text-blue-400" />
                <span className="font-mono text-xs font-bold text-white">
                  {selectedPath}
                </span>
                <span className="text-[11px] text-slate-400 font-mono">
                  ({lines.length} lines)
                </span>
              </div>

              <div className="flex items-center gap-2">
                {/* Search input */}
                <div className="relative">
                  <Search className="w-3.5 h-3.5 text-slate-500 absolute left-2.5 top-2.5" />
                  <input
                    type="text"
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    placeholder="Find in file..."
                    className="bg-slate-950 border border-slate-800 rounded-lg pl-8 pr-3 py-1.5 text-xs text-slate-200 focus:outline-none focus:border-blue-500 w-36 sm:w-48"
                  />
                </div>

                {/* Copy button */}
                <button
                  onClick={handleCopy}
                  className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-all cursor-pointer flex items-center gap-1 text-xs"
                  title="Copy full file"
                >
                  {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                  <span className="hidden sm:inline">{copied ? 'Copied' : 'Copy'}</span>
                </button>
              </div>
            </div>

            {/* Code Lines */}
            <div className="p-4 font-mono text-xs text-slate-300 overflow-x-auto max-h-[600px] overflow-y-auto leading-relaxed select-text">
              {loading ? (
                <div className="text-center py-16 text-slate-500 animate-pulse">
                  Loading {selectedPath}...
                </div>
              ) : (
                filteredLines.map((item) => (
                  <div
                    key={item.lineNum}
                    className={`flex items-start gap-4 hover:bg-slate-900/60 py-0.5 px-1 rounded ${
                      item.matches ? 'bg-amber-950/40 text-amber-200' : ''
                    }`}
                  >
                    <span className="text-slate-600 select-none text-[11px] w-8 text-right shrink-0">
                      {item.lineNum}
                    </span>
                    <pre className="whitespace-pre flex-1 text-slate-200">
                      {item.text || ' '}
                    </pre>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
