import React, { useState, useEffect, useRef } from 'react';
import { Play, Pause, Volume2, Sparkles, FileText, Check, Edit3, Sliders, RefreshCw, AlertCircle, Info, ChevronRight } from 'lucide-react';
import { Project, Transcript, TranscriptSegment } from '../types';
import { fetchTranscript, updateTranscript, triggerTranscription, triggerAnalysis } from '../api';

interface AnalysisTabProps {
  project: Project;
  onNavigateToClips: () => void;
  onProjectUpdated: () => void;
}

export const AnalysisTab: React.FC<AnalysisTabProps> = ({ project, onNavigateToClips, onProjectUpdated }) => {
  const media = project.source_media;
  const videoRef = useRef<HTMLVideoElement>(null);
  
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [transcript, setTranscript] = useState<Transcript | null>(null);
  const [isEditingTranscript, setIsEditingTranscript] = useState(false);
  const [editedSegments, setEditedSegments] = useState<TranscriptSegment[]>([]);

  // Analysis settings
  const [minDuration, setMinDuration] = useState(15);
  const [maxDuration, setMaxDuration] = useState(60);
  const [targetCount, setTargetCount] = useState(5);
  const [contentType, setContentType] = useState('general');
  const [userInstruction, setUserInstruction] = useState('');
  
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);

  // Load transcript
  useEffect(() => {
    fetchTranscript(project.id)
      .then((t) => {
        setTranscript(t);
        setEditedSegments(t.segments);
      })
      .catch(() => {
        setTranscript(null);
      });
  }, [project.id]);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleSeek = (time: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const togglePlay = () => {
    if (videoRef.current) {
      if (isPlaying) {
        videoRef.current.pause();
        setIsPlaying(false);
      } else {
        videoRef.current.play();
        setIsPlaying(true);
      }
    }
  };

  const handleTranscribe = async () => {
    try {
      setIsTranscribing(true);
      setStatusMessage('Queuing local speech-to-text with faster-whisper...');
      await triggerTranscription(project.id);
      onProjectUpdated();
    } catch (e: any) {
      setStatusMessage(`Transcription failed: ${e.message}`);
    } finally {
      setIsTranscribing(false);
    }
  };

  const handleSaveTranscript = async () => {
    try {
      const updated = await updateTranscript(project.id, editedSegments);
      setTranscript(updated);
      setIsEditingTranscript(false);
      setStatusMessage('Transcript saved successfully!');
      setTimeout(() => setStatusMessage(null), 3000);
    } catch (e: any) {
      setStatusMessage(`Failed to save transcript: ${e.message}`);
    }
  };

  const handleRunAnalysis = async () => {
    try {
      setIsAnalyzing(true);
      setStatusMessage('Running highlight selection pipeline...');
      await triggerAnalysis(project.id, {
        min_duration: minDuration,
        max_duration: maxDuration,
        target_count: targetCount,
        content_type: contentType,
        user_instruction: userInstruction.trim() || undefined,
      });
      onProjectUpdated();
      setTimeout(() => {
        onNavigateToClips();
      }, 1500);
    } catch (e: any) {
      setStatusMessage(`Analysis failed: ${e.message}`);
      setIsAnalyzing(false);
    }
  };

  const videoUrl = media?.proxy_path || (media?.file_path ? `/storage/sources/${project.id}_${media.filename}` : '');

  return (
    <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
      {/* Left Column: Video Preview and Tech Specs (7 cols) */}
      <div className="lg:col-span-7 space-y-6">
        {/* Source Video Player */}
        <div className="rounded-2xl bg-studio-surface border border-studio-border overflow-hidden shadow-xl">
          <div className="relative aspect-video bg-black flex items-center justify-center">
            {videoUrl ? (
              <video
                ref={videoRef}
                src={videoUrl}
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setIsPlaying(false)}
                className="w-full h-full object-contain"
              />
            ) : (
              <div className="text-center p-8 text-studio-muted">No media loaded</div>
            )}

            {/* Play/Pause Overlay */}
            <button
              onClick={togglePlay}
              className="absolute inset-0 m-auto w-14 h-14 rounded-full bg-black/60 hover:bg-black/80 backdrop-blur-md border border-white/20 flex items-center justify-center text-white transition-all transform active:scale-90"
            >
              {isPlaying ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-0.5" />}
            </button>
          </div>

          {/* Player Bar */}
          <div className="p-4 bg-studio-card flex items-center justify-between text-xs text-studio-muted border-t border-studio-border">
            <span className="font-mono text-studio-text">
              {Math.floor(currentTime / 60)}:{(currentTime % 60).toFixed(1).padStart(4, '0')}
              {' / '}
              {Math.floor((media?.duration || 0) / 60)}:{((media?.duration || 0) % 60).toFixed(1).padStart(4, '0')}
            </span>
            <div className="flex items-center space-x-2">
              <span className="px-2 py-0.5 rounded bg-studio-bg border border-studio-border text-[11px]">
                {media?.width}x{media?.height}
              </span>
              <span className="px-2 py-0.5 rounded bg-studio-bg border border-studio-border text-[11px]">
                {media?.fps} FPS {media?.is_vfr ? '(VFR)' : '(CFR)'}
              </span>
              <span className="px-2 py-0.5 rounded bg-studio-bg border border-studio-border text-[11px]">
                {media?.video_codec?.toUpperCase()}
              </span>
            </div>
          </div>
        </div>

        {/* Technical Media Specs */}
        <div className="p-5 rounded-2xl bg-studio-surface border border-studio-border space-y-3">
          <div className="flex items-center space-x-2 text-xs font-semibold text-studio-muted uppercase tracking-wider">
            <Info className="w-4 h-4 text-indigo-400" />
            <span>ffprobe Stream Analysis</span>
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="p-2.5 rounded-xl bg-studio-bg border border-studio-border">
              <span className="text-studio-muted block">Duration</span>
              <span className="text-white font-mono font-medium">{media?.duration.toFixed(1)}s</span>
            </div>
            <div className="p-2.5 rounded-xl bg-studio-bg border border-studio-border">
              <span className="text-studio-muted block">Audio Codec</span>
              <span className="text-white font-medium">{media?.audio_codec || 'Silent (No Audio)'}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-studio-bg border border-studio-border">
              <span className="text-studio-muted block">Channels</span>
              <span className="text-white font-medium">{media?.audio_channels ? `${media.audio_channels} Channels` : 'None'}</span>
            </div>
            <div className="p-2.5 rounded-xl bg-studio-bg border border-studio-border">
              <span className="text-studio-muted block">File Size</span>
              <span className="text-white font-mono font-medium">{((media?.file_size || 0) / (1024 * 1024)).toFixed(1)} MB</span>
            </div>
          </div>
        </div>

        {/* Analysis Configuration */}
        <div className="p-6 rounded-2xl bg-studio-surface border border-studio-border space-y-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-xs font-semibold text-studio-muted uppercase tracking-wider">
              <Sliders className="w-4 h-4 text-indigo-400" />
              <span>Highlight Selection Settings</span>
            </div>
            <span className="text-xs text-indigo-400 font-medium">Heuristic Multi-Signal Pipeline</span>
          </div>

          {/* Duration Range Presets */}
          <div className="space-y-2">
            <label className="text-xs text-studio-muted font-medium flex justify-between">
              <span>Target Clip Duration Range</span>
              <span className="text-white font-mono font-semibold">{minDuration}s – {maxDuration}s</span>
            </label>
            <div className="flex space-x-2">
              <button
                type="button"
                onClick={() => { setMinDuration(15); setMaxDuration(30); }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                  minDuration === 15 && maxDuration === 30
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-studio-bg border-studio-border text-studio-muted hover:text-white'
                }`}
              >
                Short (15-30s)
              </button>
              <button
                type="button"
                onClick={() => { setMinDuration(30); setMaxDuration(60); }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                  minDuration === 30 && maxDuration === 60
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-studio-bg border-studio-border text-studio-muted hover:text-white'
                }`}
              >
                Medium (30-60s)
              </button>
              <button
                type="button"
                onClick={() => { setMinDuration(60); setMaxDuration(90); }}
                className={`flex-1 py-1.5 text-xs font-medium rounded-lg border transition-all ${
                  minDuration === 60 && maxDuration === 90
                    ? 'bg-indigo-600 text-white border-indigo-500'
                    : 'bg-studio-bg border-studio-border text-studio-muted hover:text-white'
                }`}
              >
                Long (60-90s)
              </button>
            </div>
          </div>

          {/* Content Type & Count */}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="text-xs text-studio-muted block mb-1.5">Content Genre</label>
              <select
                value={contentType}
                onChange={(e) => setContentType(e.target.value)}
                className="w-full px-3 py-2 rounded-xl bg-studio-bg border border-studio-border text-white text-xs focus:outline-none focus:border-indigo-500"
              >
                <option value="general">General / Mixed</option>
                <option value="gaming">Gaming & Esports</option>
                <option value="reaction">Reaction & Commentary</option>
                <option value="conversation">Conversation & Q&A</option>
                <option value="podcast">Podcast & Interview</option>
                <option value="tutorial">Tutorial & Educational</option>
              </select>
            </div>
            <div>
              <label className="text-xs text-studio-muted block mb-1.5">Target Suggestions Count</label>
              <input
                type="number"
                min={1}
                max={15}
                value={targetCount}
                onChange={(e) => setTargetCount(parseInt(e.target.value) || 5)}
                className="w-full px-3 py-2 rounded-xl bg-studio-bg border border-studio-border text-white text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>
          </div>

          {/* Optional Prompt Instruction */}
          <div className="space-y-1.5">
            <label className="text-xs text-studio-muted block">
              Custom Instruction Prompt (Optional)
            </label>
            <input
              type="text"
              value={userInstruction}
              onChange={(e) => setUserInstruction(e.target.value)}
              placeholder="e.g., 'Find funny reactions with enough context to understand the joke'"
              className="w-full px-4 py-2 rounded-xl bg-studio-bg border border-studio-border text-white text-xs focus:outline-none focus:border-indigo-500"
            />
          </div>

          {/* Action Button */}
          <div className="pt-2">
            <button
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
              className="w-full py-3 rounded-xl font-semibold text-sm bg-gradient-to-r from-indigo-600 to-violet-600 hover:from-indigo-500 hover:to-violet-500 text-white shadow-lg shadow-indigo-600/25 flex items-center justify-center space-x-2 transition-all active:scale-[0.99] disabled:opacity-50"
            >
              <Sparkles className="w-4 h-4" />
              <span>{isAnalyzing ? 'Analyzing Highlights...' : 'Generate Short Clips'}</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Right Column: Transcript & Word Timestamps (5 cols) */}
      <div className="lg:col-span-5 space-y-6">
        <div className="p-6 rounded-2xl bg-studio-surface border border-studio-border h-[calc(100vh-140px)] flex flex-col justify-between">
          <div className="flex items-center justify-between pb-4 border-b border-studio-border">
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4 text-indigo-400" />
              <h3 className="font-semibold text-white text-sm">Transcript & Word Timestamps</h3>
            </div>
            {transcript && (
              <div className="flex items-center space-x-2">
                {isEditingTranscript ? (
                  <button
                    onClick={handleSaveTranscript}
                    className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white flex items-center space-x-1"
                  >
                    <Check className="w-3.5 h-3.5" />
                    <span>Save</span>
                  </button>
                ) : (
                  <button
                    onClick={() => setIsEditingTranscript(true)}
                    className="p-1.5 rounded-lg text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
                    title="Edit transcript wording"
                  >
                    <Edit3 className="w-3.5 h-3.5" />
                  </button>
                )}
              </div>
            )}
          </div>

          {/* Transcript Content Area */}
          <div className="flex-1 overflow-y-auto py-4 space-y-4 pr-1">
            {!transcript ? (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-4 text-studio-muted">
                <FileText className="w-12 h-12 text-studio-border" />
                <div>
                  <h4 className="font-semibold text-white">No transcript generated</h4>
                  <p className="text-xs text-studio-muted mt-1 max-w-xs">
                    Run faster-whisper locally to extract speech with word-level precision timestamps.
                  </p>
                </div>
                <button
                  onClick={handleTranscribe}
                  disabled={isTranscribing}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md transition-all active:scale-95"
                >
                  {isTranscribing ? 'Transcribing...' : 'Run Whisper Speech-to-Text'}
                </button>
              </div>
            ) : isEditingTranscript ? (
              <div className="space-y-3">
                {editedSegments.map((seg, idx) => (
                  <div key={seg.id} className="p-3 rounded-xl bg-studio-bg border border-studio-border space-y-1.5">
                    <div className="text-[11px] font-mono text-studio-muted">
                      {seg.start.toFixed(1)}s – {seg.end.toFixed(1)}s
                    </div>
                    <textarea
                      value={seg.text}
                      onChange={(e) => {
                        const next = [...editedSegments];
                        next[idx].text = e.target.value;
                        setEditedSegments(next);
                      }}
                      className="w-full p-2 text-xs rounded-lg bg-studio-card border border-studio-border text-white focus:outline-none focus:border-indigo-500"
                      rows={2}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <div className="space-y-4">
                {transcript.segments.map((seg) => {
                  const isActive = currentTime >= seg.start && currentTime <= seg.end;
                  return (
                    <div
                      key={seg.id}
                      onClick={() => handleSeek(seg.start)}
                      className={`p-3.5 rounded-xl border transition-all cursor-pointer ${
                        isActive
                          ? 'bg-indigo-500/10 border-indigo-500/40 shadow-sm'
                          : 'bg-studio-bg/60 border-studio-border/60 hover:border-studio-border hover:bg-studio-bg'
                      }`}
                    >
                      <div className="flex items-center justify-between text-[11px] font-mono text-studio-muted mb-1.5">
                        <span className={isActive ? 'text-indigo-400 font-semibold' : ''}>
                          {seg.start.toFixed(1)}s – {seg.end.toFixed(1)}s
                        </span>
                        {isActive && (
                          <span className="w-2 h-2 rounded-full bg-indigo-500 animate-pulse" />
                        )}
                      </div>
                      <p className="text-xs text-studio-text leading-relaxed">
                        {seg.words && seg.words.length > 0 ? (
                          seg.words.map((w, wIdx) => {
                            const isWordActive = currentTime >= w.start && currentTime <= w.end;
                            return (
                              <span
                                key={wIdx}
                                className={`mr-1 px-1 py-0.5 rounded transition-colors ${
                                  isWordActive
                                    ? 'bg-yellow-400 text-black font-semibold'
                                    : 'hover:bg-studio-card'
                                }`}
                              >
                                {w.word}
                              </span>
                            );
                          })
                        ) : (
                          seg.text
                        )}
                      </p>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Status Bar */}
          {statusMessage && (
            <div className="p-3 mt-2 rounded-xl bg-studio-bg border border-studio-border text-xs text-indigo-400 flex items-center space-x-2">
              <Info className="w-4 h-4 shrink-0" />
              <span>{statusMessage}</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
