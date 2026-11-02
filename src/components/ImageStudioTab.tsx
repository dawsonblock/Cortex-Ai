import React, { useState, useRef } from 'react';
import { 
  Sparkles, 
  Image as ImageIcon, 
  Wand2, 
  Download, 
  Upload, 
  Maximize2, 
  Copy, 
  Check, 
  RefreshCw, 
  Sliders, 
  Search, 
  Layers, 
  Info,
  Clock,
  ArrowRight,
  Split,
  Eye,
  Trash2,
  X
} from 'lucide-react';
import { GeneratedImageItem } from '../types';

export const ImageStudioTab: React.FC = () => {
  const [activeMode, setActiveMode] = useState<'create' | 'edit'>('create');
  const [model, setModel] = useState<string>('gemini-nano-banana-2.1');
  const [prompt, setPrompt] = useState<string>('');
  const [aspectRatio, setAspectRatio] = useState<string>('1:1');
  const [imageSize, setImageSize] = useState<string>('1K');
  const [enableSearch, setEnableSearch] = useState<boolean>(false);

  // Edit Mode state
  const [sourceImage, setSourceImage] = useState<string | null>(null);
  const [sourceImageMime, setSourceImageMime] = useState<string>('image/png');
  const [editPrompt, setEditPrompt] = useState<string>('');

  // Processing state
  const [loading, setLoading] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [selectedImageModal, setSelectedImageModal] = useState<GeneratedImageItem | null>(null);
  const [copiedPromptId, setCopiedPromptId] = useState<string | null>(null);

  // Gallery search & filtering state
  const [gallerySearch, setGallerySearch] = useState<string>('');
  const [galleryCategory, setGalleryCategory] = useState<string>('All');
  const [galleryType, setGalleryType] = useState<string>('All');
  const [galleryModel, setGalleryModel] = useState<string>('All');
  const [galleryDate, setGalleryDate] = useState<string>('All');
  const [gallerySort, setGallerySort] = useState<'newest' | 'oldest' | 'prompt'>('newest');

  // Gallery
  const [gallery, setGallery] = useState<GeneratedImageItem[]>([
    {
      id: 'sample-1',
      imageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A luminous abstract syntax tree with glowing cyan and violet mathematical branches in a dark quantum realm',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '1:1',
      timestamp: '2026-11-01T18:00:00.000Z',
      isEdited: false
    },
    {
      id: 'sample-2',
      imageUrl: 'https://images.unsplash.com/photo-1509228468518-180dd4864904?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A sleek retro-futuristic laboratory terminal analyzing pure lambda calculus beta reductions on holographic glass',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '16:9',
      timestamp: '2026-11-01T18:15:00.000Z',
      isEdited: false
    },
    {
      id: 'sample-3',
      imageUrl: 'https://images.unsplash.com/photo-1634017839464-5c339ebe3cb4?auto=format&fit=crop&w=1000&q=80',
      prompt: 'A vintage blueprint schematic of a Church numeral computing engine with fine copper traces and algebraic notations',
      model: 'gemini-nano-banana-2.1',
      aspectRatio: '4:3',
      timestamp: '2026-10-31T14:20:00.000Z',
      isEdited: true,
      originalImageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80'
    },
    {
      id: 'sample-4',
      imageUrl: 'https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?auto=format&fit=crop&w=1000&q=80',
      prompt: 'Refracted neon prism projecting recursive combinator graphs into an ethereal cyberpunk void',
      model: 'gemini-3.1-flash-lite-image',
      aspectRatio: '1:1',
      timestamp: '2026-10-28T09:30:00.000Z',
      isEdited: false
    }
  ]);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Prompt suggestions
  const promptSuggestions = [
    {
      label: 'Recursive Lambda Tree',
      text: 'A glowing fractal tree representing recursive lambda calculus expressions, with branches splitting into glowing beta-reduction nodes in deep navy, neon cyan, and electric magenta.'
    },
    {
      label: 'Computational Mind',
      text: 'An intricate cybernetic crystal prism refracting lines of functional program code and mathematical proofs into shimmering holographic light, hyper-detailed 3D render.'
    },
    {
      label: 'Church Encoding Blueprint',
      text: 'A vintage technical architectural blueprint of an abstract Church numeral computing engine with fine copper schematics, gears, and mathematical notations.'
    },
    {
      label: 'Quantum Synthesis Core',
      text: 'A futuristic quantum supercomputer core synthesizing algorithm ASTs inside an obsidian vacuum chamber, illuminated by pulsed laser beams and glowing particle streams.'
    }
  ];

  const editSuggestions = [
    'Add radiant neon lambda symbols (λ) floating gracefully in the foreground',
    'Transform into an architectural blueprint blueprint style with glowing cyan lines',
    'Add an algorithmic digital HUD overlay with beta-reduction metrics and code trees',
    'Convert lighting into dramatic golden hour sunset with volumetric atmospheric fog',
  ];

  const aspectRatios = [
    { id: '1:1', label: '1:1 Square' },
    { id: '16:9', label: '16:9 Widescreen' },
    { id: '9:16', label: '9:16 Portrait' },
    { id: '4:3', label: '4:3 Standard' },
    { id: '3:4', label: '3:4 Vertical' },
    { id: '4:1', label: '4:1 Panoramic' },
    { id: '1:4', label: '1:4 Tall' },
  ];

  const handleFileUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setSourceImageMime(file.type || 'image/png');
    const reader = new FileReader();
    reader.onload = (event) => {
      if (typeof event.target?.result === 'string') {
        setSourceImage(event.target.result);
      }
    };
    reader.readAsDataURL(file);
  };

  const handleGenerate = async () => {
    if (!prompt.trim()) {
      setErrorMsg('Please enter a descriptive prompt to generate an image.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch('/api/image/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt,
          aspectRatio,
          imageSize,
          model,
          enableSearch
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Image generation failed');
      }

      const newItem: GeneratedImageItem = {
        id: `gen-${Date.now()}`,
        imageUrl: data.imageUrl,
        prompt: data.prompt,
        model: data.modelUsed,
        aspectRatio,
        timestamp: data.timestamp
      };

      setGallery(prev => [newItem, ...prev]);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Image generation encountered an error.');
    } finally {
      setLoading(false);
    }
  };

  const handleEdit = async () => {
    if (!sourceImage) {
      setErrorMsg('Please upload or select a source image to edit.');
      return;
    }
    if (!editPrompt.trim()) {
      setErrorMsg('Please enter instructions for what changes to make to the image.');
      return;
    }

    setLoading(true);
    setErrorMsg(null);

    try {
      const res = await fetch('/api/image/edit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: editPrompt,
          base64ImageData: sourceImage,
          mimeType: sourceImageMime,
          model,
          aspectRatio
        })
      });

      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.error || 'Image editing failed');
      }

      const newItem: GeneratedImageItem = {
        id: `edit-${Date.now()}`,
        imageUrl: data.imageUrl,
        originalImageUrl: sourceImage,
        prompt: data.prompt,
        model: data.modelUsed,
        aspectRatio,
        timestamp: data.timestamp,
        isEdited: true
      };

      setGallery(prev => [newItem, ...prev]);
    } catch (err: any) {
      console.error(err);
      setErrorMsg(err.message || 'Image editing encountered an error.');
    } finally {
      setLoading(false);
    }
  };

  const handleStartEditFromGallery = (item: GeneratedImageItem) => {
    setSourceImage(item.imageUrl);
    setEditPrompt('');
    setActiveMode('edit');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  };

  const handleCopyPrompt = (id: string, text: string) => {
    navigator.clipboard.writeText(text);
    setCopiedPromptId(id);
    setTimeout(() => setCopiedPromptId(null), 2000);
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      {/* Studio Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="p-1.5 rounded-lg bg-pink-500/20 text-pink-400">
              <Sparkles className="w-5 h-5 animate-pulse" />
            </span>
            <h1 className="text-2xl font-bold text-white tracking-tight">
              AI Visual Synthesis Studio
            </h1>
            <span className="px-2 py-0.5 rounded-md text-xs font-mono font-bold bg-pink-950/80 text-pink-300 border border-pink-700/60">
              gemini-nano-banana-2.1
            </span>
          </div>
          <p className="text-xs sm:text-sm text-slate-400">
            Create high-fidelity images from text prompts and edit existing visuals with natural language instructions.
          </p>
        </div>

        {/* Mode Selector Tabs */}
        <div className="flex items-center p-1 bg-slate-900 rounded-xl border border-slate-800 text-xs self-start">
          <button
            onClick={() => setActiveMode('create')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${
              activeMode === 'create'
                ? 'bg-gradient-to-r from-pink-600 to-purple-600 text-white shadow-md shadow-pink-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Wand2 className="w-3.5 h-3.5" />
            <span>Create New Image</span>
          </button>
          <button
            onClick={() => setActiveMode('edit')}
            className={`flex items-center gap-1.5 px-4 py-2 rounded-lg font-medium transition-all cursor-pointer ${
              activeMode === 'edit'
                ? 'bg-gradient-to-r from-pink-600 to-purple-600 text-white shadow-md shadow-pink-500/20'
                : 'text-slate-400 hover:text-slate-200'
            }`}
          >
            <Layers className="w-3.5 h-3.5" />
            <span>Edit Existing Image</span>
          </button>
        </div>
      </div>

      {/* Main Studio Workspace */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Input & Controls */}
        <div className="lg:col-span-6 space-y-5">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 space-y-4">
            {/* Model & Resolution row */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  AI Model
                </label>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-pink-500 focus:outline-none font-mono"
                >
                  <option value="gemini-nano-banana-2.1">gemini-nano-banana-2.1 (Ultra HQ)</option>
                  <option value="gemini-3.1-flash-lite-image">gemini-3.1-flash-lite-image (Fast)</option>
                </select>
              </div>

              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1">
                  Resolution Size
                </label>
                <select
                  value={imageSize}
                  onChange={(e) => setImageSize(e.target.value)}
                  disabled={model !== 'gemini-nano-banana-2.1'}
                  className="w-full bg-slate-950 border border-slate-700 rounded-lg px-3 py-2 text-xs text-white focus:border-pink-500 focus:outline-none font-mono disabled:opacity-50"
                >
                  <option value="1K">1K Standard (1024×1024)</option>
                  <option value="2K">2K High Definition (2048×2048)</option>
                  <option value="4K">4K Ultra Resolution (4096×4096)</option>
                </select>
              </div>
            </div>

            {/* Aspect Ratio Selector */}
            <div>
              <label className="block text-xs font-medium text-slate-300 mb-1.5">
                Aspect Ratio
              </label>
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-1.5">
                {aspectRatios.map((ar) => (
                  <button
                    key={ar.id}
                    type="button"
                    onClick={() => setAspectRatio(ar.id)}
                    className={`py-1.5 px-2 rounded-lg text-xs font-mono transition-all text-center border cursor-pointer ${
                      aspectRatio === ar.id
                        ? 'bg-pink-500/20 border-pink-500/50 text-pink-300 font-semibold'
                        : 'bg-slate-950 border-slate-800 text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {ar.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Search Grounding Toggle */}
            {model === 'gemini-nano-banana-2.1' && (
              <div className="flex items-center justify-between p-2.5 rounded-xl bg-slate-950/70 border border-slate-800">
                <div className="flex items-center gap-2">
                  <Search className="w-3.5 h-3.5 text-cyan-400" />
                  <span className="text-xs text-slate-300">
                    Google Image &amp; Web Grounding
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={enableSearch}
                  onChange={(e) => setEnableSearch(e.target.checked)}
                  className="rounded accent-pink-500 w-4 h-4 cursor-pointer"
                />
              </div>
            )}

            {/* Mode-Specific Input: Create vs Edit */}
            {activeMode === 'create' ? (
              <div>
                <label className="block text-xs font-medium text-slate-300 mb-1.5">
                  Text Prompt
                </label>
                <textarea
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  placeholder="Describe the image you want to create in vivid detail..."
                  rows={4}
                  className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-slate-200 placeholder-slate-600 focus:border-pink-500 focus:outline-none resize-none leading-relaxed"
                />

                {/* Prompt Suggestions */}
                <div className="mt-2.5 space-y-1.5">
                  <span className="text-[11px] text-slate-500 font-medium block">
                    Inspiration presets:
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {promptSuggestions.map((ps, idx) => (
                      <button
                        key={idx}
                        type="button"
                        onClick={() => setPrompt(ps.text)}
                        className="px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 hover:border-pink-500/40 text-[11px] text-slate-300 hover:text-pink-300 transition-all cursor-pointer"
                      >
                        {ps.label}
                      </button>
                    ))}
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleGenerate}
                  disabled={loading || !prompt.trim()}
                  className="mt-4 w-full py-3 px-4 rounded-xl bg-gradient-to-r from-pink-600 via-purple-600 to-indigo-600 hover:from-pink-500 hover:to-indigo-500 text-white font-medium text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-pink-500/25 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Synthesizing Image with {model}...</span>
                    </>
                  ) : (
                    <>
                      <Sparkles className="w-4 h-4" />
                      <span>Generate Image</span>
                    </>
                  )}
                </button>
              </div>
            ) : (
              /* Edit Mode */
              <div className="space-y-4">
                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    1. Source Image to Edit
                  </label>
                  
                  {sourceImage ? (
                    <div className="relative rounded-xl overflow-hidden border border-slate-700 bg-slate-950 p-2 flex items-center justify-center max-h-56">
                      <img
                        src={sourceImage}
                        alt="Source"
                        className="max-h-48 rounded object-contain"
                      />
                      <button
                        onClick={() => setSourceImage(null)}
                        className="absolute top-3 right-3 p-1.5 rounded-full bg-slate-900/80 text-rose-400 hover:bg-slate-900 border border-slate-700 transition-all cursor-pointer"
                        title="Remove image"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>
                  ) : (
                    <div
                      onClick={() => fileInputRef.current?.click()}
                      className="border-2 border-dashed border-slate-700 hover:border-pink-500/60 rounded-xl p-6 text-center cursor-pointer transition-all bg-slate-950/40 hover:bg-slate-950"
                    >
                      <Upload className="w-8 h-8 text-slate-500 mx-auto mb-2" />
                      <span className="text-xs text-slate-300 font-medium block">
                        Click to upload an image or select from gallery below
                      </span>
                      <span className="text-[10px] text-slate-500 mt-1 block">
                        PNG, JPG, WebP supported
                      </span>
                      <input
                        type="file"
                        ref={fileInputRef}
                        onChange={handleFileUpload}
                        accept="image/*"
                        className="hidden"
                      />
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-slate-300 mb-1.5">
                    2. Edit Instructions
                  </label>
                  <textarea
                    value={editPrompt}
                    onChange={(e) => setEditPrompt(e.target.value)}
                    placeholder="e.g. Add neon glowing lambda symbols (λ) around the structure, adjust lighting to volumetric twilight..."
                    rows={3}
                    className="w-full bg-slate-950 border border-slate-700 rounded-xl p-3 text-xs sm:text-sm text-slate-200 placeholder-slate-600 focus:border-pink-500 focus:outline-none resize-none leading-relaxed"
                  />

                  {/* Edit suggestions */}
                  <div className="mt-2 space-y-1">
                    <span className="text-[11px] text-slate-500 font-medium block">
                      Quick edit instructions:
                    </span>
                    <div className="flex flex-wrap gap-1.5">
                      {editSuggestions.map((es, idx) => (
                        <button
                          key={idx}
                          type="button"
                          onClick={() => setEditPrompt(es)}
                          className="px-2.5 py-1 rounded-md bg-slate-950 border border-slate-800 hover:border-pink-500/40 text-[10px] text-slate-300 hover:text-pink-300 transition-all cursor-pointer"
                        >
                          {es}
                        </button>
                      ))}
                    </div>
                  </div>
                </div>

                <button
                  type="button"
                  onClick={handleEdit}
                  disabled={loading || !sourceImage || !editPrompt.trim()}
                  className="w-full py-3 px-4 rounded-xl bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium text-xs sm:text-sm flex items-center justify-center gap-2 shadow-lg shadow-purple-500/25 disabled:opacity-50 transition-all cursor-pointer"
                >
                  {loading ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin" />
                      <span>Editing Image with {model}...</span>
                    </>
                  ) : (
                    <>
                      <Wand2 className="w-4 h-4" />
                      <span>Apply Edit to Image</span>
                    </>
                  )}
                </button>
              </div>
            )}

            {errorMsg && (
              <div className="p-3 rounded-xl bg-rose-950/60 border border-rose-800/80 text-xs text-rose-300 flex items-start gap-2">
                <Info className="w-4 h-4 text-rose-400 shrink-0 mt-0.5" />
                <span>{errorMsg}</span>
              </div>
            )}
          </div>
        </div>

        {/* Right: Latest Output / Active Preview */}
        <div className="lg:col-span-6 space-y-4">
          <div className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800 flex flex-col justify-between min-h-[460px]">
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-semibold text-slate-300 flex items-center gap-1.5">
                  <ImageIcon className="w-4 h-4 text-pink-400" />
                  Synthesis Preview Canvas
                </span>
                {gallery[0] && (
                  <span className="text-[11px] font-mono text-slate-400">
                    Latest result • {gallery[0].model}
                  </span>
                )}
              </div>

              {gallery[0] ? (
                <div className="space-y-3">
                  <div className="relative group rounded-xl overflow-hidden bg-slate-950 border border-slate-800 shadow-xl flex items-center justify-center">
                    <img
                      src={gallery[0].imageUrl}
                      alt={gallery[0].prompt}
                      className="w-full max-h-[380px] object-contain rounded-xl"
                    />
                    
                    {/* Hover Overlay Controls */}
                    <div className="absolute inset-0 bg-slate-950/70 backdrop-blur-xs opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-3">
                      <button
                        onClick={() => setSelectedImageModal(gallery[0])}
                        className="p-2.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 border border-slate-700 transition-all cursor-pointer"
                        title="View Fullscreen"
                      >
                        <Maximize2 className="w-4 h-4" />
                      </button>
                      <a
                        href={gallery[0].imageUrl}
                        download={`supsearch-${gallery[0].id}.png`}
                        className="p-2.5 rounded-full bg-slate-900 text-white hover:bg-slate-800 border border-slate-700 transition-all cursor-pointer"
                        title="Download Image"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      <button
                        onClick={() => handleStartEditFromGallery(gallery[0])}
                        className="p-2.5 rounded-full bg-pink-600 text-white hover:bg-pink-500 shadow-md shadow-pink-500/30 transition-all cursor-pointer"
                        title="Edit this Image"
                      >
                        <Wand2 className="w-4 h-4" />
                      </button>
                    </div>
                  </div>

                  <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80">
                    <div className="flex items-start justify-between gap-2">
                      <p className="text-xs text-slate-300 italic leading-relaxed">
                        "{gallery[0].prompt}"
                      </p>
                      <button
                        onClick={() => handleCopyPrompt(gallery[0].id, gallery[0].prompt)}
                        className="text-slate-500 hover:text-slate-300 p-1"
                        title="Copy prompt"
                      >
                        {copiedPromptId === gallery[0].id ? (
                          <Check className="w-3.5 h-3.5 text-emerald-400" />
                        ) : (
                          <Copy className="w-3.5 h-3.5" />
                        )}
                      </button>
                    </div>

                    {gallery[0].originalImageUrl && (
                      <div className="mt-2 pt-2 border-t border-slate-900 flex items-center gap-2">
                        <span className="text-[10px] text-pink-400 font-mono">
                          ★ Edited from previous visual
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              ) : (
                <div className="h-64 rounded-xl bg-slate-950/60 border border-dashed border-slate-800 flex flex-col items-center justify-center text-slate-600">
                  <ImageIcon className="w-10 h-10 mb-2 opacity-50" />
                  <span className="text-xs">No generated images yet</span>
                </div>
              )}
            </div>

            <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-500 font-mono">
              <span>Aspect: {aspectRatio}</span>
              <span>Model: {model}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Gallery Section with Search and Multi-Filtering */}
      <div className="p-6 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <h2 className="text-base font-bold text-white flex items-center gap-2">
              <Layers className="w-4 h-4 text-pink-400" />
              Generated &amp; Edited Visuals Gallery
            </h2>
            <p className="text-xs text-slate-400">
              Filter by keywords, dates, generation mode, and aspect ratio.
            </p>
          </div>
          <span className="text-xs font-mono text-slate-400 bg-slate-950 px-2.5 py-1 rounded border border-slate-800 self-start sm:self-auto">
            {gallery.length} Total Visuals
          </span>
        </div>

        {/* Gallery Search & Filter Toolbar */}
        <div className="p-4 rounded-xl bg-slate-950/80 border border-slate-800 space-y-3">
          <div className="relative">
            <Search className="w-4 h-4 text-pink-400 absolute left-3 top-3" />
            <input
              type="text"
              value={gallerySearch}
              onChange={(e) => setGallerySearch(e.target.value)}
              placeholder="Search visuals by prompt keywords (e.g. tree, blueprint, lambda, neon)..."
              className="w-full bg-slate-900 border border-slate-800 rounded-lg pl-9 pr-9 py-2 text-xs text-white placeholder-slate-500 focus:border-pink-500 focus:outline-none"
            />
            {gallerySearch && (
              <button
                onClick={() => setGallerySearch('')}
                className="absolute right-3 top-2.5 text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5 text-xs">
            {/* Mode: Created vs Edited */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Mode / Type</label>
              <select
                value={galleryType}
                onChange={(e) => setGalleryType(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-pink-500 focus:outline-none font-mono"
              >
                <option value="All">All Types</option>
                <option value="created">Created (Text-to-Image)</option>
                <option value="edited">Edited (Image-to-Image)</option>
              </select>
            </div>

            {/* AI Model */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Model</label>
              <select
                value={galleryModel}
                onChange={(e) => setGalleryModel(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-pink-500 focus:outline-none font-mono"
              >
                <option value="All">All Models</option>
                <option value="gemini-nano-banana-2.1">gemini-nano-banana-2.1</option>
                <option value="gemini-3.1-flash-lite-image">gemini-3.1-flash-lite-image</option>
              </select>
            </div>

            {/* Date Range */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Date Created</label>
              <select
                value={galleryDate}
                onChange={(e) => setGalleryDate(e.target.value)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-pink-500 focus:outline-none font-mono"
              >
                <option value="All">All Time</option>
                <option value="today">Today (Nov 1, 2026)</option>
                <option value="week">Past 7 Days</option>
                <option value="older">Older</option>
              </select>
            </div>

            {/* Sort */}
            <div>
              <label className="block text-[11px] text-slate-400 mb-1">Sort Order</label>
              <select
                value={gallerySort}
                onChange={(e) => setGallerySort(e.target.value as any)}
                className="w-full bg-slate-900 border border-slate-800 rounded-lg px-2.5 py-1.5 text-xs text-slate-200 focus:border-pink-500 focus:outline-none font-mono"
              >
                <option value="newest">Newest First</option>
                <option value="oldest">Oldest First</option>
                <option value="prompt">Prompt Length</option>
              </select>
            </div>
          </div>
        </div>

        {/* Filtered Gallery Grid */}
        {(() => {
          const q = gallerySearch.trim().toLowerCase();
          const filtered = gallery.filter(item => {
            const matchesQuery = !q || item.prompt.toLowerCase().includes(q) || item.model.toLowerCase().includes(q);
            const matchesType = 
              galleryType === 'All' || 
              (galleryType === 'created' && !item.isEdited) ||
              (galleryType === 'edited' && item.isEdited);
            const matchesModel = galleryModel === 'All' || item.model === galleryModel;
            
            // Date filter logic
            let matchesDate = true;
            if (galleryDate === 'today') {
              matchesDate = item.timestamp.startsWith('2026-11-01');
            } else if (galleryDate === 'week') {
              matchesDate = item.timestamp >= '2026-10-25';
            } else if (galleryDate === 'older') {
              matchesDate = item.timestamp < '2026-10-25';
            }

            return matchesQuery && matchesType && matchesModel && matchesDate;
          }).sort((a, b) => {
            if (gallerySort === 'oldest') return a.timestamp.localeCompare(b.timestamp);
            if (gallerySort === 'prompt') return b.prompt.length - a.prompt.length;
            return b.timestamp.localeCompare(a.timestamp);
          });

          if (filtered.length === 0) {
            return (
              <div className="py-12 text-center text-slate-500 rounded-xl bg-slate-950/40 border border-dashed border-slate-800">
                <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p className="text-xs">No visuals found matching your filters.</p>
                <button
                  onClick={() => {
                    setGallerySearch('');
                    setGalleryType('All');
                    setGalleryModel('All');
                    setGalleryDate('All');
                  }}
                  className="mt-2 text-xs text-pink-400 hover:text-pink-300 font-medium cursor-pointer"
                >
                  Clear Filters
                </button>
              </div>
            );
          }

          return (
            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
              {filtered.map((item) => (
                <div
                  key={item.id}
                  className="group rounded-xl overflow-hidden bg-slate-950 border border-slate-800/80 hover:border-pink-500/50 transition-all flex flex-col shadow-md"
                >
                  <div className="relative aspect-square overflow-hidden bg-slate-900">
                    <img
                      src={item.imageUrl}
                      alt={item.prompt}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />

                    <div className="absolute inset-0 bg-slate-950/60 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center gap-2">
                      <button
                        onClick={() => setSelectedImageModal(item)}
                        className="p-1.5 rounded-lg bg-slate-900 text-white hover:bg-slate-800 border border-slate-700 cursor-pointer"
                        title="Fullscreen Preview"
                      >
                        <Eye className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleStartEditFromGallery(item)}
                        className="p-1.5 rounded-lg bg-pink-600 text-white hover:bg-pink-500 cursor-pointer"
                        title="Edit this visual"
                      >
                        <Wand2 className="w-4 h-4" />
                      </button>
                      <a
                        href={item.imageUrl}
                        download={`supsearch-${item.id}.png`}
                        className="p-1.5 rounded-lg bg-slate-900 text-white hover:bg-slate-800 border border-slate-700 cursor-pointer"
                        title="Download"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                    </div>
                  </div>

                  <div className="p-3 flex-1 flex flex-col justify-between">
                    <p className="text-xs text-slate-300 line-clamp-2 mb-2 leading-relaxed">
                      {item.prompt}
                    </p>

                    <div className="pt-2 border-t border-slate-900 flex items-center justify-between text-[10px] text-slate-500 font-mono">
                      <span>{item.aspectRatio}</span>
                      <span className={item.isEdited ? 'text-pink-400 font-semibold' : 'text-slate-400'}>
                        {item.isEdited ? '★ Edited' : 'Created'}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          );
        })()}
      </div>

      {/* Fullscreen Image Modal */}
      {selectedImageModal && (
        <div 
          className="fixed inset-0 z-50 bg-slate-950/90 backdrop-blur-md flex items-center justify-center p-4"
          onClick={() => setSelectedImageModal(null)}
        >
          <div 
            className="relative max-w-4xl w-full bg-slate-900 border border-slate-800 rounded-2xl overflow-hidden p-4 space-y-4 shadow-2xl"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex items-center justify-between border-b border-slate-800 pb-3">
              <div>
                <span className="text-xs font-mono font-bold text-pink-400">
                  {selectedImageModal.model}
                </span>
                <span className="text-xs text-slate-400 ml-2">
                  Aspect {selectedImageModal.aspectRatio}
                </span>
              </div>
              <button
                onClick={() => setSelectedImageModal(null)}
                className="text-slate-400 hover:text-white text-xs px-2 py-1 rounded bg-slate-800 cursor-pointer"
              >
                Close ✕
              </button>
            </div>

            <div className="flex items-center justify-center max-h-[60vh] overflow-hidden rounded-xl bg-slate-950">
              <img
                src={selectedImageModal.imageUrl}
                alt={selectedImageModal.prompt}
                className="max-h-[60vh] object-contain rounded-xl"
              />
            </div>

            <p className="text-xs text-slate-300 italic p-3 bg-slate-950 rounded-xl border border-slate-800">
              "{selectedImageModal.prompt}"
            </p>

            <div className="flex justify-end gap-2">
              <button
                onClick={() => {
                  handleStartEditFromGallery(selectedImageModal);
                  setSelectedImageModal(null);
                }}
                className="px-4 py-2 rounded-xl bg-pink-600 hover:bg-pink-500 text-white text-xs font-medium flex items-center gap-2 cursor-pointer"
              >
                <Wand2 className="w-3.5 h-3.5" />
                <span>Edit this Image</span>
              </button>
              <a
                href={selectedImageModal.imageUrl}
                download={`supsearch-${selectedImageModal.id}.png`}
                className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-white text-xs font-medium flex items-center gap-2 cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download High-Res</span>
              </a>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
