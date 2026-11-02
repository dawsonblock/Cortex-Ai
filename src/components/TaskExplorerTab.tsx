import React, { useState, useMemo } from 'react';
import { 
  Search, 
  Filter, 
  Cpu, 
  CheckCircle2, 
  AlertTriangle, 
  Layers, 
  Copy, 
  Check, 
  ArrowRight, 
  SlidersHorizontal, 
  X, 
  RotateCcw,
  Code2,
  Calendar,
  Grid,
  List,
  Sparkles,
  ExternalLink,
  BookOpen
} from 'lucide-react';
import { TaskItem } from '../types';

interface TaskExplorerTabProps {
  tasks: TaskItem[];
  onSelectTaskForSynthesis: (taskId: string) => void;
}

export const TaskExplorerTab: React.FC<TaskExplorerTabProps> = ({
  tasks,
  onSelectTaskForSynthesis
}) => {
  // Search & Filter State
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [selectedCategory, setSelectedCategory] = useState<string>('All');
  const [selectedEncoding, setSelectedEncoding] = useState<string>('All');
  const [selectedStatus, setSelectedStatus] = useState<string>('All');
  const [selectedComplexity, setSelectedComplexity] = useState<string>('All');
  const [sortBy, setSortBy] = useState<'id' | 'name' | 'status' | 'complexity'>('id');
  const [viewMode, setViewMode] = useState<'grid' | 'table'>('grid');

  // Detail Modal State
  const [inspectedTask, setInspectedTask] = useState<TaskItem | null>(null);
  const [copiedTaskId, setCopiedTaskId] = useState<string | null>(null);

  // Extract unique categories & encodings
  const categories = useMemo(() => {
    const set = new Set<string>();
    tasks.forEach(t => { if (t.category) set.add(t.category); });
    return ['All', ...Array.from(set).sort()];
  }, [tasks]);

  const encodings = useMemo(() => {
    const set = new Set<string>();
    tasks.forEach(t => { if (t.encoding) set.add(t.encoding); });
    return ['All', ...Array.from(set).sort()];
  }, [tasks]);

  const complexities = ['All', 'O(1)', 'O(log n)', 'O(n)', 'O(n log n)', 'O(n²)', 'O(√n)', 'NP-Complete', 'Turing-Complete'];

  // Filtering & Sorting logic
  const filteredTasks = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();

    return tasks.filter(t => {
      // Keyword search
      const matchesQuery = 
        !q ||
        t.id.toLowerCase().includes(q) ||
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q) ||
        t.solution.toLowerCase().includes(q) ||
        t.tags.some(tag => tag.toLowerCase().includes(q));

      // Category
      const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;

      // Encoding
      const matchesEncoding = selectedEncoding === 'All' || t.encoding === selectedEncoding;

      // Status
      const matchesStatus = 
        selectedStatus === 'All' ||
        (selectedStatus === 'SOLVED' && t.status === 'SOLVED') ||
        (selectedStatus === 'ALGO_WALL' && t.status === 'ALGO_WALL');

      // Complexity
      const matchesComplexity = 
        selectedComplexity === 'All' ||
        t.complexity.toLowerCase().includes(selectedComplexity.toLowerCase());

      return matchesQuery && matchesCategory && matchesEncoding && matchesStatus && matchesComplexity;
    }).sort((a, b) => {
      if (sortBy === 'name') return a.name.localeCompare(b.name);
      if (sortBy === 'status') return a.status.localeCompare(b.status);
      if (sortBy === 'complexity') return a.complexity.localeCompare(b.complexity);
      return a.id.localeCompare(b.id);
    });
  }, [tasks, searchQuery, selectedCategory, selectedEncoding, selectedStatus, selectedComplexity, sortBy]);

  const handleCopySolution = (taskId: string, solution: string) => {
    navigator.clipboard.writeText(solution);
    setCopiedTaskId(taskId);
    setTimeout(() => setCopiedTaskId(null), 2000);
  };

  const handleResetFilters = () => {
    setSearchQuery('');
    setSelectedCategory('All');
    setSelectedEncoding('All');
    setSelectedStatus('All');
    setSelectedComplexity('All');
    setSortBy('id');
  };

  const hasActiveFilters = 
    searchQuery !== '' || 
    selectedCategory !== 'All' || 
    selectedEncoding !== 'All' || 
    selectedStatus !== 'All' || 
    selectedComplexity !== 'All';

  return (
    <div className="space-y-6 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-cyan-500/20 text-cyan-400">
              <Search className="w-5 h-5" />
            </span>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              LamBench Benchmark &amp; Task Explorer
            </h1>
            <span className="px-2 py-0.5 rounded-md text-xs font-mono font-bold bg-cyan-950/80 text-cyan-300 border border-cyan-800/60">
              120 Total Tasks
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Search, filter, and inspect synthesized lambda programs across 12 representation families and formal referee specifications.
          </p>
        </div>

        {/* View Mode Toggle */}
        <div className="flex items-center gap-1 p-1 bg-slate-900 rounded-xl border border-slate-800 text-xs self-start">
          <button
            onClick={() => setViewMode('grid')}
            className={`p-1.5 rounded-lg transition-all ${
              viewMode === 'grid' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-white'
            }`}
            title="Grid View"
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('table')}
            className={`p-1.5 rounded-lg transition-all ${
              viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-400 hover:text-white'
            }`}
            title="List Table View"
          >
            <List className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Search & Multi-Criteria Filtering Controls */}
      <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4 shadow-xl">
        {/* Main Search Bar */}
        <div className="relative">
          <Search className="w-4 h-4 text-cyan-400 absolute left-3.5 top-3.5" />
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search by task name, ID (e.g. cnat_add, clst_map), formula, description, or keyword..."
            className="w-full bg-slate-950 border border-slate-700/80 rounded-xl pl-10 pr-10 py-2.5 text-xs sm:text-sm text-white placeholder-slate-500 focus:border-cyan-500 focus:outline-none"
          />
          {searchQuery && (
            <button
              onClick={() => setSearchQuery('')}
              className="absolute right-3.5 top-3 text-slate-400 hover:text-white"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Filter Selectors Row */}
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 text-xs">
          {/* Category */}
          <div>
            <label className="block text-slate-400 font-medium mb-1 text-[11px]">
              Category
            </label>
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              {categories.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Encoding */}
          <div>
            <label className="block text-slate-400 font-medium mb-1 text-[11px]">
              Encoding
            </label>
            <select
              value={selectedEncoding}
              onChange={(e) => setSelectedEncoding(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              {encodings.map((enc) => (
                <option key={enc} value={enc}>
                  {enc}
                </option>
              ))}
            </select>
          </div>

          {/* Solve Status */}
          <div>
            <label className="block text-slate-400 font-medium mb-1 text-[11px]">
              Solve Status
            </label>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              <option value="All">All Statuses (120)</option>
              <option value="SOLVED">Certified Solved (108)</option>
              <option value="ALGO_WALL">Algo Wall Unsolved (12)</option>
            </select>
          </div>

          {/* Complexity */}
          <div>
            <label className="block text-slate-400 font-medium mb-1 text-[11px]">
              Complexity
            </label>
            <select
              value={selectedComplexity}
              onChange={(e) => setSelectedComplexity(e.target.value)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              {complexities.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </select>
          </div>

          {/* Sort By */}
          <div>
            <label className="block text-slate-400 font-medium mb-1 text-[11px]">
              Sort By
            </label>
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value as any)}
              className="w-full bg-slate-950 border border-slate-700 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-500 focus:outline-none font-mono"
            >
              <option value="id">Task ID (A-Z)</option>
              <option value="name">Title Name</option>
              <option value="status">Status (Solved first)</option>
              <option value="complexity">Complexity Class</option>
            </select>
          </div>
        </div>

        {/* Active Filter Chips & Clear */}
        <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800 text-xs">
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-slate-400 font-mono">
              Found <strong className="text-cyan-400">{filteredTasks.length}</strong> of {tasks.length} tasks
            </span>

            {selectedCategory !== 'All' && (
              <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 flex items-center gap-1 font-mono text-[11px]">
                Category: {selectedCategory}
                <X className="w-3 h-3 cursor-pointer hover:text-white" onClick={() => setSelectedCategory('All')} />
              </span>
            )}

            {selectedEncoding !== 'All' && (
              <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 flex items-center gap-1 font-mono text-[11px]">
                Encoding: {selectedEncoding}
                <X className="w-3 h-3 cursor-pointer hover:text-white" onClick={() => setSelectedEncoding('All')} />
              </span>
            )}

            {selectedStatus !== 'All' && (
              <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 flex items-center gap-1 font-mono text-[11px]">
                Status: {selectedStatus === 'SOLVED' ? 'Solved' : 'Algo Wall'}
                <X className="w-3 h-3 cursor-pointer hover:text-white" onClick={() => setSelectedStatus('All')} />
              </span>
            )}

            {selectedComplexity !== 'All' && (
              <span className="px-2 py-0.5 rounded-md bg-slate-800 text-slate-300 flex items-center gap-1 font-mono text-[11px]">
                Complexity: {selectedComplexity}
                <X className="w-3 h-3 cursor-pointer hover:text-white" onClick={() => setSelectedComplexity('All')} />
              </span>
            )}
          </div>

          {hasActiveFilters && (
            <button
              onClick={handleResetFilters}
              className="text-xs text-rose-400 hover:text-rose-300 font-medium flex items-center gap-1 cursor-pointer"
            >
              <RotateCcw className="w-3.5 h-3.5" />
              <span>Reset All Filters</span>
            </button>
          )}
        </div>
      </div>

      {/* Tasks View: Grid Cards vs List Table */}
      {filteredTasks.length === 0 ? (
        <div className="py-16 text-center rounded-2xl bg-slate-900/40 border border-dashed border-slate-800">
          <Search className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <h3 className="text-sm font-semibold text-slate-300">No matching tasks found</h3>
          <p className="text-xs text-slate-500 max-w-sm mx-auto mt-1 mb-4">
            Try adjusting your search keywords or clearing active category filters.
          </p>
          <button
            onClick={handleResetFilters}
            className="px-3 py-1.5 rounded-lg bg-slate-800 text-xs text-cyan-400 hover:bg-slate-700 cursor-pointer"
          >
            Reset Filters
          </button>
        </div>
      ) : viewMode === 'grid' ? (
        /* Grid Mode */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredTasks.map((task) => (
            <div
              key={task.id}
              className="p-4 rounded-xl bg-slate-900/70 border border-slate-800/80 hover:border-slate-700 hover:shadow-xl transition-all flex flex-col justify-between"
            >
              <div>
                {/* Header row */}
                <div className="flex items-start justify-between gap-2 mb-2">
                  <div className="min-w-0">
                    <span className="font-mono text-xs font-bold text-cyan-400 bg-cyan-950/50 px-2 py-0.5 rounded border border-cyan-800/40">
                      {task.id}
                    </span>
                    <h3 className="font-semibold text-white text-sm mt-1.5 truncate">
                      {task.name}
                    </h3>
                  </div>

                  <span className={`text-[10px] font-mono font-semibold px-2 py-0.5 rounded shrink-0 ${
                    task.status === 'SOLVED'
                      ? 'bg-emerald-950/80 text-emerald-400 border border-emerald-800/50'
                      : 'bg-amber-950/80 text-amber-400 border border-amber-800/50'
                  }`}>
                    {task.status === 'SOLVED' ? '108 Certified' : 'Algo Wall'}
                  </span>
                </div>

                <p className="text-xs text-slate-300 mb-3 line-clamp-2 leading-relaxed">
                  {task.description}
                </p>

                {/* Metadata Pills */}
                <div className="flex flex-wrap items-center gap-1.5 text-[10px] font-mono text-slate-400 mb-3">
                  <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800">
                    {task.category}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-indigo-400">
                    {task.encoding}
                  </span>
                  <span className="px-1.5 py-0.5 rounded bg-slate-950 border border-slate-800 text-purple-400">
                    {task.complexity}
                  </span>
                </div>
              </div>

              {/* Action Buttons */}
              <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                <button
                  onClick={() => setInspectedTask(task)}
                  className="text-xs text-slate-400 hover:text-white flex items-center gap-1 transition-colors cursor-pointer"
                >
                  <BookOpen className="w-3.5 h-3.5" />
                  <span>Inspect λ</span>
                </button>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => handleCopySolution(task.id, task.solution)}
                    className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white cursor-pointer"
                    title="Copy Lambda Solution"
                  >
                    {copiedTaskId === task.id ? (
                      <Check className="w-3.5 h-3.5 text-emerald-400" />
                    ) : (
                      <Copy className="w-3.5 h-3.5" />
                    )}
                  </button>

                  <button
                    onClick={() => onSelectTaskForSynthesis(task.id)}
                    className="px-2.5 py-1 rounded-lg bg-indigo-600/30 hover:bg-indigo-600 text-indigo-300 hover:text-white border border-indigo-500/40 text-xs font-medium flex items-center gap-1 transition-all cursor-pointer"
                  >
                    <span>Synthesize</span>
                    <ArrowRight className="w-3 h-3" />
                  </button>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        /* Table Mode */
        <div className="rounded-2xl bg-slate-900/70 border border-slate-800 overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-950 text-slate-400 font-mono border-b border-slate-800">
                <tr>
                  <th className="py-3 px-4">Task ID</th>
                  <th className="py-3 px-4">Name / Title</th>
                  <th className="py-3 px-4">Category</th>
                  <th className="py-3 px-4">Encoding</th>
                  <th className="py-3 px-4">Complexity</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60 font-mono">
                {filteredTasks.map((task) => (
                  <tr key={task.id} className="hover:bg-slate-800/40 transition-colors">
                    <td className="py-3 px-4 font-bold text-cyan-300">
                      {task.id}
                    </td>
                    <td className="py-3 px-4 font-sans text-white font-medium">
                      {task.name}
                    </td>
                    <td className="py-3 px-4 text-slate-400">
                      {task.category}
                    </td>
                    <td className="py-3 px-4 text-indigo-300">
                      {task.encoding}
                    </td>
                    <td className="py-3 px-4 text-purple-300">
                      {task.complexity}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[10px] ${
                        task.status === 'SOLVED'
                          ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                          : 'bg-amber-950 text-amber-400 border border-amber-800'
                      }`}>
                        {task.status === 'SOLVED' ? 'Solved' : 'Wall'}
                      </span>
                    </td>
                    <td className="py-3 px-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => setInspectedTask(task)}
                          className="px-2 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-300 font-sans text-xs cursor-pointer"
                        >
                          Inspect
                        </button>
                        <button
                          onClick={() => onSelectTaskForSynthesis(task.id)}
                          className="px-2.5 py-1 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-sans text-xs cursor-pointer"
                        >
                          Synthesize
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Task Detail Modal */}
      {inspectedTask && (
        <div
          className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setInspectedTask(null)}
        >
          <div
            className="relative max-w-3xl w-full bg-slate-900 border border-slate-700 rounded-2xl overflow-hidden p-6 space-y-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-start justify-between border-b border-slate-800 pb-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-mono text-sm font-bold text-cyan-400 bg-cyan-950/60 px-2 py-0.5 rounded border border-cyan-800">
                    {inspectedTask.id}
                  </span>
                  <span className={`text-xs font-mono font-semibold px-2 py-0.5 rounded ${
                    inspectedTask.status === 'SOLVED'
                      ? 'bg-emerald-950 text-emerald-400 border border-emerald-800'
                      : 'bg-amber-950 text-amber-400 border border-amber-800'
                  }`}>
                    {inspectedTask.status === 'SOLVED' ? 'Certified Solved (108)' : 'Algo Wall Unsolved'}
                  </span>
                </div>
                <h2 className="text-lg font-bold text-white mt-1">
                  {inspectedTask.name}
                </h2>
              </div>
              <button
                onClick={() => setInspectedTask(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800 cursor-pointer"
              >
                ✕ Close
              </button>
            </div>

            <p className="text-xs sm:text-sm text-slate-300 leading-relaxed">
              {inspectedTask.description}
            </p>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-xs font-mono">
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block">CATEGORY</span>
                <span className="text-slate-200">{inspectedTask.category}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block">ENCODING</span>
                <span className="text-indigo-400">{inspectedTask.encoding}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block">COMPLEXITY</span>
                <span className="text-purple-400">{inspectedTask.complexity}</span>
              </div>
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800">
                <span className="text-slate-500 text-[10px] block">MILESTONE</span>
                <span className="text-emerald-400">{inspectedTask.dateAdded}</span>
              </div>
            </div>

            {/* Synthesized Lambda Solution */}
            <div>
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-xs font-semibold text-slate-400">
                  Synthesized Affine Lambda Program:
                </span>
                <button
                  onClick={() => handleCopySolution(inspectedTask.id, inspectedTask.solution)}
                  className="text-xs text-cyan-400 hover:text-cyan-300 flex items-center gap-1 cursor-pointer font-mono"
                >
                  <Copy className="w-3.5 h-3.5" />
                  <span>{copiedTaskId === inspectedTask.id ? 'Copied' : 'Copy Program'}</span>
                </button>
              </div>

              <div className="p-3.5 rounded-xl bg-slate-950 font-mono text-xs text-cyan-300 border border-slate-800 max-h-56 overflow-y-auto leading-relaxed select-text whitespace-pre-wrap">
                {inspectedTask.solution}
              </div>
            </div>

            <div className="pt-3 border-t border-slate-800 flex justify-end gap-2">
              <button
                onClick={() => {
                  onSelectTaskForSynthesis(inspectedTask.id);
                  setInspectedTask(null);
                }}
                className="px-4 py-2 rounded-xl bg-gradient-to-r from-cyan-600 to-indigo-600 hover:from-cyan-500 hover:to-indigo-500 text-white font-medium text-xs flex items-center gap-1.5 shadow-md shadow-cyan-500/20 cursor-pointer"
              >
                <Cpu className="w-4 h-4" />
                <span>Launch in Synthesizer</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
