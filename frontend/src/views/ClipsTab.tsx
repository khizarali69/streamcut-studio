import React, { useState, useRef } from 'react';
import { Play, Pause, Edit, Download, CheckSquare, Square, Trash2, Sparkles, Clock, Tag, AlertCircle } from 'lucide-react';
import { Project, ClipCandidate } from '../types';
import { updateClipMetadata, exportClip, batchExportClips } from '../api';

interface ClipsTabProps {
  project: Project;
  clips: ClipCandidate[];
  onSelectClipForEdit: (clipId: string) => void;
  onClipsChanged: () => void;
  onNavigateToExports: () => void;
}

export const ClipsTab: React.FC<ClipsTabProps> = ({
  project,
  clips,
  onSelectClipForEdit,
  onClipsChanged,
  onNavigateToExports,
}) => {
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [playingClipId, setPlayingClipId] = useState<string | null>(null);
  const [statusMsg, setStatusMsg] = useState<string | null>(null);
  const videoRefs = useRef<{ [key: string]: HTMLVideoElement | null }>({});

  const media = project.source_media;
  const videoUrl = media?.proxy_path || (media?.file_path ? `/storage/sources/${project.id}_${media.filename}` : '');

  const toggleSelect = (id: string) => {
    setSelectedIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  const selectAll = () => {
    if (selectedIds.length === clips.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(clips.map((c) => c.id));
    }
  };

  const handlePlayClip = (clip: ClipCandidate) => {
    const video = videoRefs.current[clip.id];
    if (!video) return;

    if (playingClipId === clip.id) {
      video.pause();
      setPlayingClipId(null);
    } else {
      // Pause other videos
      Object.values(videoRefs.current).forEach((v) => v?.pause());
      video.currentTime = clip.start_time;
      video.play();
      setPlayingClipId(clip.id);
    }
  };

  const handleQuickExport = async (clipId: string) => {
    try {
      setStatusMsg('Starting export job...');
      await exportClip(clipId, { resolution: '1080p', quality: 'high', burn_captions: true });
      setStatusMsg('Export enqueued! Navigating to Export Queue...');
      setTimeout(() => {
        onNavigateToExports();
      }, 1000);
    } catch (err: any) {
      setStatusMsg(`Export failed: ${err.message}`);
    }
  };

  const handleBatchExport = async () => {
    if (selectedIds.length === 0) return;
    try {
      setStatusMsg(`Enqueuing ${selectedIds.length} batch exports...`);
      await batchExportClips(project.id, selectedIds);
      setStatusMsg('Batch exports enqueued!');
      setTimeout(() => {
        onNavigateToExports();
      }, 1000);
    } catch (err: any) {
      setStatusMsg(`Batch export failed: ${err.message}`);
    }
  };

  const handleUpdateScore = async (clip: ClipCandidate, newScore: number) => {
    await updateClipMetadata(project.id, clip.id, { highlight_score: newScore });
    onClipsChanged();
  };

  return (
    <div className="space-y-6">
      {/* Action Bar */}
      <div className="p-4 rounded-2xl bg-studio-surface border border-studio-border flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-3">
          <button
            onClick={selectAll}
            className="flex items-center space-x-2 text-xs font-semibold px-3 py-1.5 rounded-lg border border-studio-border text-studio-muted hover:text-white transition-colors"
          >
            {selectedIds.length === clips.length && clips.length > 0 ? (
              <CheckSquare className="w-4 h-4 text-indigo-400" />
            ) : (
              <Square className="w-4 h-4" />
            )}
            <span>Select All ({clips.length})</span>
          </button>
          {selectedIds.length > 0 && (
            <span className="text-xs text-indigo-400 font-medium">
              {selectedIds.length} clips selected
            </span>
          )}
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={handleBatchExport}
            disabled={selectedIds.length === 0}
            className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white shadow-md flex items-center space-x-1.5 transition-all"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Batch Export ({selectedIds.length})</span>
          </button>
        </div>
      </div>

      {statusMsg && (
        <div className="p-3 rounded-xl bg-studio-card border border-studio-border text-xs text-indigo-400 flex items-center space-x-2">
          <Sparkles className="w-4 h-4" />
          <span>{statusMsg}</span>
        </div>
      )}

      {/* Clip Cards Grid */}
      {clips.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border-2 border-dashed border-studio-border bg-studio-card/20 space-y-3">
          <Sparkles className="w-10 h-10 text-studio-muted mx-auto" />
          <h3 className="font-semibold text-white">No candidate clips generated yet</h3>
          <p className="text-xs text-studio-muted max-w-sm mx-auto">
            Head to the Analysis tab to run the speech & highlight detection pipeline on your source video.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {clips.map((clip) => {
            const isSelected = selectedIds.includes(clip.id);
            const isPlaying = playingClipId === clip.id;

            return (
              <div
                key={clip.id}
                className={`rounded-2xl bg-studio-surface border transition-all overflow-hidden flex flex-col justify-between ${
                  isSelected ? 'border-indigo-500 ring-1 ring-indigo-500/50' : 'border-studio-border'
                }`}
              >
                {/* Video Preview */}
                <div className="aspect-video bg-black relative overflow-hidden group">
                  <video
                    ref={(el) => (videoRefs.current[clip.id] = el)}
                    src={videoUrl}
                    onTimeUpdate={(e) => {
                      const v = e.currentTarget;
                      if (v.currentTime >= clip.end_time) {
                        v.pause();
                        v.currentTime = clip.start_time;
                        setPlayingClipId(null);
                      }
                    }}
                    className="w-full h-full object-contain"
                  />

                  {/* Play Button */}
                  <button
                    onClick={() => handlePlayClip(clip)}
                    className="absolute inset-0 m-auto w-12 h-12 rounded-full bg-black/60 hover:bg-black/80 backdrop-blur-md border border-white/20 flex items-center justify-center text-white transition-all transform active:scale-90"
                  >
                    {isPlaying ? <Pause className="w-5 h-5" /> : <Play className="w-5 h-5 ml-0.5" />}
                  </button>

                  {/* Selection Checkbox */}
                  <button
                    onClick={() => toggleSelect(clip.id)}
                    className="absolute top-2.5 left-2.5 p-1 rounded-lg bg-black/60 backdrop-blur-md border border-white/10 text-white"
                  >
                    {isSelected ? (
                      <CheckSquare className="w-4 h-4 text-indigo-400" />
                    ) : (
                      <Square className="w-4 h-4 text-studio-muted" />
                    )}
                  </button>

                  {/* Highlight Score Pill */}
                  <div className="absolute top-2.5 right-2.5 px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-600/90 backdrop-blur-md text-white border border-indigo-400/30">
                    {clip.highlight_score.toFixed(0)} Score
                  </div>

                  {/* Duration Badge */}
                  <div className="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded bg-black/80 text-[11px] font-mono text-white flex items-center space-x-1">
                    <Clock className="w-3 h-3 text-studio-muted" />
                    <span>{clip.duration.toFixed(1)}s</span>
                  </div>
                </div>

                {/* Content */}
                <div className="p-5 space-y-3 flex-1 flex flex-col justify-between">
                  <div className="space-y-2">
                    <h4 className="font-semibold text-white text-sm line-clamp-1">{clip.title}</h4>
                    <div className="flex items-center text-[11px] font-mono text-studio-muted space-x-2">
                      <span>{clip.start_time.toFixed(1)}s</span>
                      <span>→</span>
                      <span>{clip.end_time.toFixed(1)}s</span>
                    </div>
                    {clip.reason && (
                      <p className="text-xs text-studio-muted leading-relaxed line-clamp-2">
                        {clip.reason}
                      </p>
                    )}
                  </div>

                  {/* Footer Actions */}
                  <div className="pt-3 border-t border-studio-border flex items-center justify-between">
                    <button
                      onClick={() => onSelectClipForEdit(clip.id)}
                      className="px-3 py-1.5 rounded-lg text-xs font-semibold bg-studio-card border border-studio-border text-white hover:border-indigo-500/50 flex items-center space-x-1.5 transition-colors"
                    >
                      <Edit className="w-3.5 h-3.5 text-indigo-400" />
                      <span>Edit & Reframe</span>
                    </button>

                    <button
                      onClick={() => handleQuickExport(clip.id)}
                      className="p-1.5 rounded-lg text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
                      title="Quick Export Clip"
                    >
                      <Download className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
