export type RightsStatus = 'owned' | 'permission_granted' | 'licensed' | 'unknown';

export interface SourceMedia {
  id: string;
  project_id: string;
  filename: string;
  file_path?: string;
  file_size: number;
  duration: number;
  width: number;
  height: number;
  fps: number;
  aspect_ratio: string;
  video_codec?: string;
  audio_codec?: string;
  audio_channels: number;
  sample_rate: number;
  is_vfr: boolean;
  rotation: number;
  thumbnail_path?: string;
  proxy_path?: string;
  created_at: string;
}

export interface Project {
  id: string;
  title: string;
  description?: string;
  source_url?: string;
  creator?: string;
  rights_status: RightsStatus;
  rights_notes?: string;
  status: 'created' | 'uploaded' | 'ingested' | 'transcribing' | 'transcribed' | 'analyzing' | 'ready' | 'failed';
  created_at: string;
  updated_at: string;
  source_media?: SourceMedia;
}

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  score?: number;
}

export interface TranscriptSegment {
  id: number;
  start: number;
  end: number;
  text: string;
  words: WordTimestamp[];
}

export interface Transcript {
  id: string;
  project_id: string;
  language: string;
  is_user_edited: boolean;
  raw_text: string;
  segments: TranscriptSegment[];
  created_at: string;
  updated_at: string;
}

export interface ClipCandidate {
  id: string;
  project_id: string;
  title: string;
  start_time: number;
  end_time: number;
  duration: number;
  highlight_score: number;
  reason?: string;
  tags: string[];
  status: 'suggested' | 'accepted' | 'rejected';
  created_at: string;
}

export interface RectNorm {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ClipEdit {
  id: string;
  clip_id: string;
  project_id: string;
  trim_start: number;
  trim_end: number;
  layout_type: 'full_frame' | 'split_facecam_gameplay' | 'split_gameplay_facecam' | 'side_by_side' | 'blurred_background' | 'custom';
  aspect_ratio: '9:16' | '1:1' | '4:5' | '16:9';
  facecam_rect: RectNorm;
  gameplay_rect: RectNorm;
  caption_style_id: string;
  caption_enabled: boolean;
  volume_multiplier: number;
  loudness_norm: boolean;
  silence_trim_enabled: boolean;
  filler_word_removal: boolean;
  version: number;
  updated_at: string;
}

export interface CaptionStyle {
  id: string;
  name: string;
  is_preset: boolean;
  font_family: string;
  font_size: number;
  primary_color: string;
  highlight_color: string;
  outline_color: string;
  outline_width: number;
  shadow_color: string;
  shadow_offset: number;
  bg_color: string;
  bg_alpha: number;
  position_v: 'top' | 'middle' | 'bottom';
  margin_v: number;
  words_per_line: number;
  max_lines: number;
  animation_style: 'none' | 'karaoke' | 'word_highlight';
}

export interface LayoutPreset {
  id: string;
  name: string;
  layout_type: string;
  aspect_ratio: string;
  facecam_rect: RectNorm;
  gameplay_rect: RectNorm;
  description?: string;
  is_system: boolean;
}

export interface Job {
  id: string;
  job_type: 'probe_and_proxy' | 'transcribe' | 'analyze_highlights' | 'export_clip';
  project_id: string;
  target_id?: string;
  status: 'queued' | 'processing' | 'completed' | 'failed' | 'canceled';
  progress: number;
  progress_stage: string;
  error_message?: string;
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface ExportArtifact {
  id: string;
  project_id: string;
  clip_id: string;
  job_id?: string;
  filename: string;
  file_path?: string;
  file_size: number;
  duration: number;
  width: number;
  height: number;
  format: string;
  has_burned_captions: boolean;
  download_url: string;
  srt_url?: string;
  vtt_url?: string;
  thumbnail_url?: string;
  ffprobe_valid: boolean;
  created_at: string;
}

export interface StorageStats {
  total_space_bytes: number;
  free_space_bytes: number;
  used_by_app_bytes: number;
  projects_count: number;
  exports_count: number;
}

export interface SystemDiagnostics {
  ffmpeg: string;
  whisper_model: string;
  whisper_device: string;
  whisper_compute_type: string;
  gpu_available: boolean;
  gpu_name: string;
  disk_free_gb: number;
  disk_total_gb: number;
  disk_warning: boolean;
  llm_enabled: boolean;
  llm_provider: string;
}
