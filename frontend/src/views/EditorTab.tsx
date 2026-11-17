import React, { useState, useEffect, useRef } from 'react';
import {
  Play, Pause, RotateCcw, RotateCw, Save, Download, Sliders, Type, Layout,
  Volume2, Check, Sparkles, Scissors, Eye, Maximize2, Layers
} from 'lucide-react';
import { Project, ClipCandidate, ClipEdit, CaptionStyle, LayoutPreset } from '../types';
import { fetchClipEdit, updateClipEdit, fetchCaptionStyles, fetchLayoutPresets, exportClip } from '../api';

interface EditorTabProps {
  project: Project;
  clipId: string;
  onNavigateToExports: () => void;
}

export const EditorTab: React.FC<EditorTabProps> = ({ project, clipId, onNavigateToExports }) => {
  const media = project.source_media;
  const videoRef = useRef<HTMLVideoElement>(null);

  const [edit, setEdit] = useState<ClipEdit | null>(null);
  const [captionStyles, setCaptionStyles] = useState<CaptionStyle[]>([]);
  const [layoutPresets, setLayoutPresets] = useState<LayoutPreset[]>([]);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [activeSubTab, setActiveSubTab] = useState<'layout' | 'captions' | 'audio' | 'export'>('layout');
  
  const [isSaving, setIsSaving] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);

  // Undo / Redo history
  const [history, setHistory] = useState<ClipEdit[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Load edit and presets
  useEffect(() => {
    fetchClipEdit(project.id, clipId).then((data) => {
      setEdit(data);
      setHistory([data]);
      setHistoryIndex(0);
      if (videoRef.current) {
        videoRef.current.currentTime = data.trim_start;
      }
    });

    fetchCaptionStyles().then(setCaptionStyles);
    fetchLayoutPresets().then(setLayoutPresets);
  }, [project.id, clipId]);

  const updateEditState = (updates: Partial<ClipEdit>) => {
    if (!edit) return;
    const next = { ...edit, ...updates };
    setEdit(next);
    
    // Push to undo history
    const nextHist = history.slice(0, historyIndex + 1);
    setHistory([...nextHist, next]);
    setHistoryIndex(nextHist.length);
  };

  const handleUndo = () => {
    if (historyIndex > 0) {
      setHistoryIndex(historyIndex - 1);
      setEdit(history[historyIndex - 1]);
    }
  };

  const handleRedo = () => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex(historyIndex + 1);
      setEdit(history[historyIndex + 1]);
    }
  };

  const handleSave = async () => {
    if (!edit) return;
    try {
      setIsSaving(true);
      await updateClipEdit(project.id, clipId, edit);
      setStatusMsg('Edits saved successfully!');
      setTimeout(() => setStatusMsg(null), 3000);
    } catch (e: any) {
      setStatusMsg(`Save failed: ${e.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleExport = async () => {
    if (!edit) return;
    try {
      setIsExporting(true);
      setStatusMsg('Saving edits and enqueuing export job...');
      await updateClipEdit(project.id, clipId, edit);
      await exportClip(clipId, {
        resolution: '1080p',
        quality: 'high',
        burn_captions: edit.caption_enabled,
      });
      setStatusMsg('Export enqueued! Navigating to Export Queue...');
      setTimeout(() => {
        onNavigateToExports();
      }, 1000);
    } catch (e: any) {
      setStatusMsg(`Export failed: ${e.message}`);
      setIsExporting(false);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current && edit) {
      const cur = videoRef.current.currentTime;
      setCurrentTime(cur);
      if (cur >= edit.trim_end) {
        videoRef.current.currentTime = edit.trim_start;
        if (!isPlaying) videoRef.current.pause();
      }
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        if (currentTime < (edit?.trim_start || 0) || currentTime >= (edit?.trim_end || 9999)) {
          videoRef.current.currentTime = edit?.trim_start || 0;
        }
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const videoUrl = media?.proxy_path || (media?.file_path ? `/storage/sources/${project.id}_${media.filename}` : '');

  if (!edit) {
    return <div className="p-12 text-center text-studio-muted">Loading clip editor...</div>;
  }

  const duration = Math.max(0.1, edit.trim_end - edit.trim_start);

  return (
    <div className="space-y-6">
      {/* Top Bar with Title and Actions */}
      <div className="p-4 rounded-2xl bg-studio-surface border border-studio-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <div className="p-2 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Scissors className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-base font-bold text-white">Clip Reframing & Caption Editor</h2>
            <p className="text-xs text-studio-muted">
              Trim duration: {duration.toFixed(1)}s • {edit.aspect_ratio} • {edit.layout_type.replace(/_/g, ' ')}
            </p>
          </div>
        </div>

        <div className="flex items-center space-x-2">
          {/* Undo / Redo */}
          <button
            onClick={handleUndo}
            disabled={historyIndex <= 0}
            className="p-2 rounded-xl border border-studio-border text-studio-muted hover:text-white disabled:opacity-30 hover:bg-studio-card transition-colors"
            title="Undo"
          >
            <RotateCcw className="w-4 h-4" />
          </button>
          <button
            onClick={handleRedo}
            disabled={historyIndex >= history.length - 1}
            className="p-2 rounded-xl border border-studio-border text-studio-muted hover:text-white disabled:opacity-30 hover:bg-studio-card transition-colors"
            title="Redo"
          >
            <RotateCw className="w-4 h-4" />
          </button>

          {/* Save Button */}
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-studio-card border border-studio-border hover:border-studio-border/80 text-white flex items-center space-x-1.5 transition-colors"
          >
            <Save className="w-3.5 h-3.5 text-studio-muted" />
            <span>{isSaving ? 'Saving...' : 'Save Changes'}</span>
          </button>

          {/* Export Button */}
          <button
            onClick={handleExport}
            disabled={isExporting}
            className="px-5 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 flex items-center space-x-1.5 transition-all active:scale-95"
          >
            <Download className="w-3.5 h-3.5" />
            <span>{isExporting ? 'Exporting...' : 'Render & Export'}</span>
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-studio-card border border-studio-border text-xs text-indigo-400 flex items-center space-x-2">
          <Sparkles className="w-4 h-4" />
          <span>{statusMsg}</span>
        </div>
      )}

      {/* Main Workspace Layout (2 columns: Video Preview left, Controls right) */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Left Column: Interactive Visual Preview Canvas (7 cols) */}
        <div className="lg:col-span-7 space-y-4">
          <div className="p-6 rounded-2xl bg-studio-surface border border-studio-border flex flex-col items-center justify-center min-h-[520px]">
            {/* Visual Aspect Ratio Container (9:16 or selected) */}
            <div
              className="relative bg-black rounded-2xl overflow-hidden shadow-2xl border-2 border-studio-border"
              style={{
                width: edit.aspect_ratio === '9:16' ? '280px' : edit.aspect_ratio === '1:1' ? '400px' : '440px',
                aspectRatio:
                  edit.aspect_ratio === '9:16'
                    ? '9/16'
                    : edit.aspect_ratio === '1:1'
                    ? '1/1'
                    : edit.aspect_ratio === '4:5'
                    ? '4/5'
                    : '16/9',
              }}
            >
              {/* If split facecam & gameplay */}
              {edit.layout_type === 'split_facecam_gameplay' ? (
                <div className="w-full h-full flex flex-col">
                  {/* Top: Facecam (35%) */}
                  <div className="h-[35%] w-full relative overflow-hidden border-b border-indigo-500/50 bg-studio-card">
                    <video
                      ref={videoRef}
                      src={videoUrl}
                      onTimeUpdate={handleTimeUpdate}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute top-2 left-2 px-1.5 py-0.5 rounded bg-black/70 text-[9px] font-mono text-indigo-400 border border-indigo-500/30">
                      Facecam Region
                    </div>
                  </div>
                  {/* Bottom: Gameplay (65%) */}
                  <div className="h-[65%] w-full relative overflow-hidden bg-black">
                    <video
                      src={videoUrl}
                      className="w-full h-full object-cover"
                    />
                    <div className="absolute bottom-2 left-2 px-1.5 py-0.5 rounded bg-black/70 text-[9px] font-mono text-emerald-400 border border-emerald-500/30">
                      Gameplay Region
                    </div>
                  </div>
                </div>
              ) : edit.layout_type === 'blurred_background' ? (
                /* Blurred background landscape */
                <div className="w-full h-full relative overflow-hidden bg-black flex items-center justify-center">
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    onTimeUpdate={handleTimeUpdate}
                    className="absolute inset-0 w-full h-full object-cover blur-md opacity-40 scale-110"
                  />
                  <video
                    src={videoUrl}
                    className="relative w-full z-10 object-contain shadow-2xl"
                  />
                </div>
              ) : (
                /* Full-frame standard vertical crop */
                <div className="w-full h-full relative overflow-hidden bg-black">
                  <video
                    ref={videoRef}
                    src={videoUrl}
                    onTimeUpdate={handleTimeUpdate}
                    className="w-full h-full object-cover"
                  />
                </div>
              )}

              {/* Subtitle Caption Preview Overlay */}
              {edit.caption_enabled && (
                <div className="absolute inset-x-4 bottom-12 z-20 pointer-events-none text-center">
                  <div className="inline-block px-3 py-1.5 rounded-lg bg-black/70 backdrop-blur-sm border border-white/10 shadow-lg">
                    <span className="font-bold uppercase tracking-wide text-white text-sm drop-shadow-md">
                      LOOK AT THIS <span className="text-yellow-400">AMAZING</span> MOMENT
                    </span>
                  </div>
                </div>
              )}

              {/* Central Play/Pause Toggle */}
              <button
                onClick={togglePlay}
                className="absolute inset-0 m-auto w-12 h-12 rounded-full bg-black/60 hover:bg-black/80 backdrop-blur-md border border-white/20 flex items-center justify-center text-white transition-all transform active:scale-90"
              >
                {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
              </button>
            </div>
          </div>

          {/* Timeline & Precise Numeric Trim Sliders */}
          <div className="p-5 rounded-2xl bg-studio-surface border border-studio-border space-y-4">
            <div className="flex items-center justify-between text-xs text-studio-muted">
              <span className="font-semibold uppercase tracking-wider text-white">Clip Trimming Timeline</span>
              <span className="font-mono text-indigo-400 font-semibold">{duration.toFixed(2)}s selected</span>
            </div>

            {/* Start and End Sliders */}
            <div className="space-y-3">
              <div>
                <div className="flex justify-between text-xs mb-1 text-studio-muted">
                  <span>Start Time</span>
                  <span className="font-mono text-white">{edit.trim_start.toFixed(2)}s</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={media?.duration || 100}
                  step={0.1}
                  value={edit.trim_start}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (val < edit.trim_end - 0.5) {
                      updateEditState({ trim_start: val });
                      if (videoRef.current) videoRef.current.currentTime = val;
                    }
                  }}
                  className="w-full h-1.5 bg-studio-card rounded-lg appearance-none cursor-pointer"
                />
              </div>

              <div>
                <div className="flex justify-between text-xs mb-1 text-studio-muted">
                  <span>End Time</span>
                  <span className="font-mono text-white">{edit.trim_end.toFixed(2)}s</span>
                </div>
                <input
                  type="range"
                  min={0}
                  max={media?.duration || 100}
                  step={0.1}
                  value={edit.trim_end}
                  onChange={(e) => {
                    const val = parseFloat(e.target.value);
                    if (val > edit.trim_start + 0.5) {
                      updateEditState({ trim_end: val });
                    }
                  }}
                  className="w-full h-1.5 bg-studio-card rounded-lg appearance-none cursor-pointer"
                />
              </div>
            </div>

            {/* Numeric input row */}
            <div className="grid grid-cols-2 gap-4 pt-1">
              <div>
                <label className="text-[11px] text-studio-muted block mb-1">Exact Start (sec)</label>
                <input
                  type="number"
                  step={0.01}
                  value={edit.trim_start}
                  onChange={(e) => updateEditState({ trim_start: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-1.5 rounded-lg bg-studio-bg border border-studio-border text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
              <div>
                <label className="text-[11px] text-studio-muted block mb-1">Exact End (sec)</label>
                <input
                  type="number"
                  step={0.01}
                  value={edit.trim_end}
                  onChange={(e) => updateEditState({ trim_end: parseFloat(e.target.value) || 0 })}
                  className="w-full px-3 py-1.5 rounded-lg bg-studio-bg border border-studio-border text-xs text-white font-mono focus:outline-none focus:border-indigo-500"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Controls Panel (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="p-6 rounded-2xl bg-studio-surface border border-studio-border space-y-6">
            {/* Sub-Tabs */}
            <div className="flex space-x-1 p-1 bg-studio-bg rounded-xl border border-studio-border">
              <button
                type="button"
                onClick={() => setActiveSubTab('layout')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
                  activeSubTab === 'layout' ? 'bg-studio-card text-white shadow-sm' : 'text-studio-muted hover:text-white'
                }`}
              >
                <Layout className="w-3.5 h-3.5" />
                <span>Layout & Crop</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveSubTab('captions')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
                  activeSubTab === 'captions' ? 'bg-studio-card text-white shadow-sm' : 'text-studio-muted hover:text-white'
                }`}
              >
                <Type className="w-3.5 h-3.5" />
                <span>Captions</span>
              </button>
              <button
                type="button"
                onClick={() => setActiveSubTab('audio')}
                className={`flex-1 py-1.5 text-xs font-semibold rounded-lg flex items-center justify-center space-x-1.5 transition-all ${
                  activeSubTab === 'audio' ? 'bg-studio-card text-white shadow-sm' : 'text-studio-muted hover:text-white'
                }`}
              >
                <Volume2 className="w-3.5 h-3.5" />
                <span>Audio</span>
              </button>
            </div>

            {/* TAB 1: Layout & Reframing */}
            {activeSubTab === 'layout' && (
              <div className="space-y-5">
                {/* Aspect Ratio */}
                <div>
                  <label className="text-xs font-semibold text-studio-muted uppercase tracking-wider block mb-2">
                    Target Social Aspect Ratio
                  </label>
                  <div className="grid grid-cols-4 gap-2">
                    {(['9:16', '1:1', '4:5', '16:9'] as const).map((ratio) => (
                      <button
                        key={ratio}
                        type="button"
                        onClick={() => updateEditState({ aspect_ratio: ratio })}
                        className={`py-2 rounded-xl text-xs font-semibold border transition-all ${
                          edit.aspect_ratio === ratio
                            ? 'bg-indigo-600 text-white border-indigo-500 shadow-md'
                            : 'bg-studio-bg border-studio-border text-studio-muted hover:text-white'
                        }`}
                      >
                        {ratio}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Streamer Layout Presets */}
                <div>
                  <label className="text-xs font-semibold text-studio-muted uppercase tracking-wider block mb-2">
                    Streamer Video Layout
                  </label>
                  <div className="space-y-2">
                    {[
                      { id: 'full_frame', label: 'Full-Frame Crop', desc: 'Direct vertical center crop' },
                      { id: 'split_facecam_gameplay', label: 'Facecam Above Gameplay', desc: 'Facecam top 35%, gameplay bottom 65%' },
                      { id: 'split_gameplay_facecam', label: 'Gameplay Above Facecam', desc: 'Gameplay top 65%, facecam bottom 35%' },
                      { id: 'blurred_background', label: 'Original 16:9 on Blurred BG', desc: 'Keeps full landscape frame uncropped' },
                      { id: 'side_by_side', label: 'Side-by-Side Dual', desc: 'Dual reaction framing' },
                    ].map((item) => (
                      <button
                        key={item.id}
                        type="button"
                        onClick={() => updateEditState({ layout_type: item.id as any })}
                        className={`w-full p-3 rounded-xl border text-left flex items-start justify-between transition-all ${
                          edit.layout_type === item.id
                            ? 'bg-indigo-500/10 border-indigo-500/50 text-white'
                            : 'bg-studio-bg border-studio-border text-studio-muted hover:border-studio-border/80 hover:text-white'
                        }`}
                      >
                        <div>
                          <div className="text-xs font-semibold">{item.label}</div>
                          <div className="text-[11px] text-studio-muted mt-0.5">{item.desc}</div>
                        </div>
                        {edit.layout_type === item.id && (
                          <Check className="w-4 h-4 text-indigo-400 shrink-0" />
                        )}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Facecam Rect Fine-Tuning */}
                {(edit.layout_type === 'split_facecam_gameplay' || edit.layout_type === 'split_gameplay_facecam') && (
                  <div className="p-4 rounded-xl bg-studio-bg border border-studio-border space-y-3">
                    <span className="text-xs font-semibold text-white block">Facecam Crop Fine-Tuning</span>
                    <div className="grid grid-cols-2 gap-3 text-xs">
                      <div>
                        <span className="text-studio-muted block mb-1">Facecam Width</span>
                        <input
                          type="range"
                          min={0.15}
                          max={0.6}
                          step={0.05}
                          value={edit.facecam_rect.w}
                          onChange={(e) =>
                            updateEditState({
                              facecam_rect: { ...edit.facecam_rect, w: parseFloat(e.target.value) },
                            })
                          }
                          className="w-full"
                        />
                      </div>
                      <div>
                        <span className="text-studio-muted block mb-1">Facecam Height</span>
                        <input
                          type="range"
                          min={0.15}
                          max={0.6}
                          step={0.05}
                          value={edit.facecam_rect.h}
                          onChange={(e) =>
                            updateEditState({
                              facecam_rect: { ...edit.facecam_rect, h: parseFloat(e.target.value) },
                            })
                          }
                          className="w-full"
                        />
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* TAB 2: Captions Styling */}
            {activeSubTab === 'captions' && (
              <div className="space-y-5">
                <div className="flex items-center justify-between p-3 rounded-xl bg-studio-bg border border-studio-border">
                  <div>
                    <span className="text-xs font-semibold text-white block">Burn-In Subtitles</span>
                    <span className="text-[11px] text-studio-muted">Render styled subtitles into exported video</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={edit.caption_enabled}
                    onChange={(e) => updateEditState({ caption_enabled: e.target.checked })}
                    className="w-4 h-4 rounded text-indigo-600 bg-studio-card border-studio-border"
                  />
                </div>

                {/* Style Presets */}
                <div>
                  <label className="text-xs font-semibold text-studio-muted uppercase tracking-wider block mb-2">
                    Caption Style Presets
                  </label>
                  <div className="grid grid-cols-2 gap-3">
                    {captionStyles.map((style) => (
                      <button
                        key={style.id}
                        type="button"
                        onClick={() => updateEditState({ caption_style_id: style.id })}
                        className={`p-3 rounded-xl border text-left transition-all ${
                          edit.caption_style_id === style.id
                            ? 'bg-indigo-500/10 border-indigo-500/50 text-white'
                            : 'bg-studio-bg border-studio-border text-studio-muted hover:border-studio-border/80 hover:text-white'
                        }`}
                      >
                        <div className="text-xs font-bold">{style.name}</div>
                        <div className="text-[10px] text-studio-muted mt-1">
                          {style.animation_style === 'karaoke' ? 'Active karaoke highlight' : 'Word-by-word highlight'}
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* TAB 3: Audio Settings */}
            {activeSubTab === 'audio' && (
              <div className="space-y-5">
                <div>
                  <div className="flex justify-between text-xs text-studio-muted mb-1">
                    <span>Source Audio Volume</span>
                    <span className="font-mono text-white">{(edit.volume_multiplier * 100).toFixed(0)}%</span>
                  </div>
                  <input
                    type="range"
                    min={0.0}
                    max={2.0}
                    step={0.1}
                    value={edit.volume_multiplier}
                    onChange={(e) => updateEditState({ volume_multiplier: parseFloat(e.target.value) })}
                    className="w-full"
                  />
                </div>

                <div className="flex items-center justify-between p-3 rounded-xl bg-studio-bg border border-studio-border">
                  <div>
                    <span className="text-xs font-semibold text-white block">Broadcast Loudness Normalization</span>
                    <span className="text-[11px] text-studio-muted">Applies FFmpeg loudnorm filter (-16 LUFS)</span>
                  </div>
                  <input
                    type="checkbox"
                    checked={edit.loudness_norm}
                    onChange={(e) => updateEditState({ loudness_norm: e.target.checked })}
                    className="w-4 h-4 rounded text-indigo-600 bg-studio-card border-studio-border"
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
