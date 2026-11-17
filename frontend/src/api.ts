import {
  Project, SourceMedia, Transcript, ClipCandidate, ClipEdit,
  CaptionStyle, LayoutPreset, Job, ExportArtifact, StorageStats, SystemDiagnostics
} from './types';

const BASE_URL = ''; // Relative path proxy through Vite

export async function fetchProjects(): Promise<Project[]> {
  const res = await fetch(`${BASE_URL}/api/projects`);
  if (!res.ok) throw new Error('Failed to load projects');
  return res.json();
}

export async function createProject(data: {
  title: string;
  description?: string;
  source_url?: string;
  creator?: string;
  rights_status: string;
  rights_notes?: string;
}): Promise<Project> {
  const res = await fetch(`${BASE_URL}/api/projects`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to create project');
  return res.json();
}

export async function fetchProject(id: string): Promise<Project> {
  const res = await fetch(`${BASE_URL}/api/projects/${id}`);
  if (!res.ok) throw new Error('Failed to load project details');
  return res.json();
}

export async function deleteProject(id: string): Promise<void> {
  const res = await fetch(`${BASE_URL}/api/projects/${id}`, { method: 'DELETE' });
  if (!res.ok) throw new Error('Failed to delete project');
}

export async function uploadMedia(
  projectId: string,
  file: File,
  onProgress?: (pct: number) => void
): Promise<SourceMedia> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);

    xhr.upload.addEventListener('progress', (e) => {
      if (e.lengthComputable && onProgress) {
        onProgress(Math.round((e.loaded / e.total) * 100));
      }
    });

    xhr.addEventListener('load', () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        resolve(JSON.parse(xhr.responseText));
      } else {
        try {
          const err = JSON.parse(xhr.responseText);
          reject(new Error(err.detail || 'Upload failed'));
        } catch {
          reject(new Error(`Upload failed with HTTP ${xhr.status}`));
        }
      }
    });

    xhr.addEventListener('error', () => reject(new Error('Network error during upload')));
    xhr.open('POST', `${BASE_URL}/api/projects/${projectId}/media/upload`);
    xhr.send(formData);
  });
}

export async function importMediaFromUrl(projectId: string, sourceUrl: string): Promise<SourceMedia> {
  const formData = new FormData();
  formData.append('source_url', sourceUrl);
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/media/url-import`, {
    method: 'POST',
    body: formData,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: 'URL import failed' }));
    throw new Error(err.detail);
  }
  return res.json();
}

export async function fetchTranscript(projectId: string): Promise<Transcript> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/transcript`);
  if (!res.ok) throw new Error('Transcript not ready');
  return res.json();
}

export async function updateTranscript(projectId: string, segments: any[]): Promise<Transcript> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/transcript`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ segments }),
  });
  if (!res.ok) throw new Error('Failed to update transcript');
  return res.json();
}

export async function triggerTranscription(projectId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/transcript/transcribe`, {
    method: 'POST',
  });
  if (!res.ok) throw new Error('Failed to enqueue transcription');
  return res.json();
}

export async function triggerAnalysis(projectId: string, data: {
  min_duration: number;
  max_duration: number;
  target_count: number;
  content_type: string;
  user_instruction?: string;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/clips/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to trigger analysis');
  return res.json();
}

export async function fetchClips(projectId: string): Promise<ClipCandidate[]> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/clips`);
  if (!res.ok) throw new Error('Failed to load candidate clips');
  return res.json();
}

export async function fetchClipEdit(projectId: string, clipId: string): Promise<ClipEdit> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/clips/${clipId}/edit`);
  if (!res.ok) throw new Error('Failed to load clip edit parameters');
  return res.json();
}

export async function updateClipEdit(projectId: string, clipId: string, data: Partial<ClipEdit>): Promise<ClipEdit> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/clips/${clipId}/edit`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error('Failed to update clip edit');
  return res.json();
}

export async function updateClipMetadata(projectId: string, clipId: string, data: {
  title?: string;
  highlight_score?: number;
  status_val?: string;
}): Promise<any> {
  const url = new URL(`${BASE_URL}/api/projects/${projectId}/clips/${clipId}`, window.location.origin);
  if (data.title !== undefined) url.searchParams.append('title', data.title);
  if (data.highlight_score !== undefined) url.searchParams.append('highlight_score', data.highlight_score.toString());
  if (data.status_val !== undefined) url.searchParams.append('status_val', data.status_val);

  const res = await fetch(url.toString(), { method: 'PATCH' });
  if (!res.ok) throw new Error('Failed to update clip metadata');
  return res.json();
}

export async function exportClip(clipId: string, options: {
  resolution?: string;
  quality?: string;
  burn_captions?: boolean;
}): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/clips/${clipId}/export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(options),
  });
  if (!res.ok) throw new Error('Failed to start export');
  return res.json();
}

export async function batchExportClips(projectId: string, clipIds: string[]): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/batch-export`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(clipIds),
  });
  if (!res.ok) throw new Error('Failed to enqueue batch export');
  return res.json();
}

export async function fetchProjectExports(projectId: string): Promise<ExportArtifact[]> {
  const res = await fetch(`${BASE_URL}/api/projects/${projectId}/exports`);
  if (!res.ok) throw new Error('Failed to load project exports');
  return res.json();
}

export async function fetchJobs(projectId?: string): Promise<Job[]> {
  const url = projectId ? `${BASE_URL}/api/jobs?project_id=${projectId}` : `${BASE_URL}/api/jobs`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to load jobs');
  return res.json();
}

export async function cancelJob(jobId: string): Promise<any> {
  const res = await fetch(`${BASE_URL}/api/jobs/${jobId}/cancel`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to cancel job');
  return res.json();
}

export async function retryJob(jobId: string): Promise<Job> {
  const res = await fetch(`${BASE_URL}/api/jobs/${jobId}/retry`, { method: 'POST' });
  if (!res.ok) throw new Error('Failed to retry job');
  return res.json();
}

export async function fetchCaptionStyles(): Promise<CaptionStyle[]> {
  const res = await fetch(`${BASE_URL}/api/settings/caption-styles`);
  if (!res.ok) throw new Error('Failed to load caption styles');
  return res.json();
}

export async function fetchLayoutPresets(): Promise<LayoutPreset[]> {
  const res = await fetch(`${BASE_URL}/api/settings/layout-presets`);
  if (!res.ok) throw new Error('Failed to load layout presets');
  return res.json();
}

export async function fetchStorageStats(): Promise<StorageStats> {
  const res = await fetch(`${BASE_URL}/api/projects/storage/stats`);
  if (!res.ok) throw new Error('Failed to load storage stats');
  return res.json();
}

export async function fetchSystemDiagnostics(): Promise<SystemDiagnostics> {
  const res = await fetch(`${BASE_URL}/api/settings/system`);
  if (!res.ok) throw new Error('Failed to load system diagnostics');
  return res.json();
}
