import React, { useState, useEffect } from 'react';
import { Navbar } from './components/Navbar';
import { OverviewTab } from './components/OverviewTab';
import { TaskExplorerTab } from './components/TaskExplorerTab';
import { SynthesizerTab } from './components/SynthesizerTab';
import { TestsRunnerTab } from './components/TestsRunnerTab';
import { CodeBrowserTab } from './components/CodeBrowserTab';
import { ImageStudioTab } from './components/ImageStudioTab';
import { GlobalSearchModal } from './components/GlobalSearchModal';
import { OverviewData, TaskItem, GeneratedImageItem } from './types';

export default function App() {
  const [activeTab, setActiveTab] = useState<'overview' | 'explorer' | 'synthesizer' | 'tests' | 'code' | 'image-studio'>('overview');
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [serverOnline, setServerOnline] = useState<boolean>(true);
  const [targetTaskId, setTargetTaskId] = useState<string>('cnat_add');
  const [isSearchOpen, setIsSearchOpen] = useState<boolean>(false);

  // Gallery items for search
  const [galleryImages] = useState<GeneratedImageItem[]>([
    {
      id: 'sample-1',
      imageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A luminous abstract syntax tree with glowing cyan and violet mathematical branches in a dark quantum realm',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '1:1',
      timestamp: '2026-11-01T18:00:00.000Z'
    },
    {
      id: 'sample-2',
      imageUrl: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A sleek retro-futuristic laboratory terminal analyzing pure lambda calculus beta reductions on holographic glass',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '16:9',
      timestamp: '2026-11-01T18:15:00.000Z'
    },
    {
      id: 'sample-3',
      imageUrl: 'https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A vintage blueprint schematic of a Church numeral computing engine with fine copper traces and algebraic notations',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '4:3',
      timestamp: '2026-10-31T14:20:00.000Z',
      isEdited: true
    }
  ]);

  useEffect(() => {
    // Load overview
    fetch('/api/supsearch/overview')
      .then(res => res.json())
      .then(data => {
        setOverview(data);
        setServerOnline(true);
      })
      .catch(err => {
        console.error('Failed to connect to backend overview API:', err);
        setServerOnline(false);
      });

    // Load full tasks catalog
    fetch('/api/supsearch/tasks')
      .then(res => res.json())
      .then(data => {
        if (data.tasks) {
          setTasks(data.tasks);
        }
      })
      .catch(err => console.error('Failed to load tasks:', err));
  }, []);

  const handleNavigateToSynthesizer = (taskId?: string) => {
    if (taskId) {
      setTargetTaskId(taskId);
    }
    setActiveTab('synthesizer');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleNavigateToTests = () => {
    setActiveTab('tests');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectTaskFromSearch = (taskId: string) => {
    setTargetTaskId(taskId);
    setActiveTab('synthesizer');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectFileFromSearch = (_filePath: string) => {
    setActiveTab('code');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleSelectImageFromSearch = (_image: GeneratedImageItem) => {
    setActiveTab('image-studio');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500/30 selection:text-cyan-200">
      {/* Top Navigation */}
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        serverOnline={serverOnline}
        onOpenSearch={() => setIsSearchOpen(true)}
      />

      {/* Global Command Palette / Search Modal */}
      <GlobalSearchModal
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        tasks={tasks}
        images={galleryImages}
        onSelectTask={handleSelectTaskFromSearch}
        onSelectFile={handleSelectFileFromSearch}
        onSelectImage={handleSelectImageFromSearch}
        onSelectTab={setActiveTab}
      />

      {/* Main Tab Content */}
      <main className="flex-1 pb-16">
        {activeTab === 'overview' && (
          <OverviewTab
            overview={overview}
            onNavigateToSynthesizer={handleNavigateToSynthesizer}
            onNavigateToTests={handleNavigateToTests}
          />
        )}

        {activeTab === 'explorer' && (
          <TaskExplorerTab
            tasks={tasks}
            onSelectTaskForSynthesis={handleNavigateToSynthesizer}
          />
        )}

        {activeTab === 'synthesizer' && (
          <SynthesizerTab initialTaskId={targetTaskId} />
        )}

        {activeTab === 'tests' && (
          <TestsRunnerTab />
        )}

        {activeTab === 'code' && (
          <CodeBrowserTab />
        )}

        {activeTab === 'image-studio' && (
          <ImageStudioTab />
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/80 py-6 px-4 text-center text-xs text-slate-500 font-mono">
        <div className="max-w-7xl mx-auto flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            <span className="font-bold text-slate-400">SUPSEARCH v2.5.0</span>
            <span>•</span>
            <span>Work-Conserving Shared Deadline</span>
            <span>•</span>
            <span>LamBench 108/120</span>
          </div>
          <div className="flex items-center gap-3 text-slate-400">
            <span>Powered by @google/genai (gemini-nano-banana-2.1)</span>
            <span>•</span>
            <span>Press ⌘K for instant search</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
