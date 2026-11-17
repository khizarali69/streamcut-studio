import React from 'react';
import { Plus, Video, Clock, HardDrive, RefreshCw, Trash2, ArrowRight, CheckCircle2, AlertTriangle, ShieldCheck } from 'lucide-react';
import { Project, StorageStats } from '../types';

interface DashboardViewProps {
  projects: Project[];
  storageStats: StorageStats | null;
  onSelectProject: (projectId: string) => void;
  onNewProject: () => void;
  onDeleteProject: (projectId: string, e: React.MouseEvent) => void;
  onRefresh: () => void;
  isLoading: boolean;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
  projects,
  storageStats,
  onSelectProject,
  onNewProject,
  onDeleteProject,
  onRefresh,
  isLoading,
}) => {
  const formatDuration = (seconds?: number) => {
    if (!seconds) return '0:00';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const formatDate = (isoString: string) => {
    try {
      return new Date(isoString).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return isoString;
    }
  };

  const freeGb = storageStats ? (storageStats.free_space_bytes / (1024 ** 3)).toFixed(1) : '0';
  const usedAppMb = storageStats ? (storageStats.used_by_app_bytes / (1024 ** 2)).toFixed(0) : '0';

  return (
    <div className="max-w-7xl mx-auto px-6 py-8 space-y-8 animate-fadeIn">
      {/* Banner / Value Proposition */}
      <div className="p-6 rounded-2xl bg-gradient-to-r from-studio-card to-studio-surface border border-studio-border flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
        <div>
          <div className="flex items-center space-x-2 text-indigo-400 text-xs font-semibold uppercase tracking-wider mb-2">
            <ShieldCheck className="w-4 h-4" />
            <span>Autonomous Local Video Studio</span>
          </div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Turn Long-Form Media Into Viral Vertical Clips</h1>
          <p className="text-sm text-studio-muted mt-1 max-w-2xl">
            100% self-hosted with local Whisper speech-to-text, streamer facecam layouts, smart reframing, and ASS burned-in subtitles. Unlimited projects, zero cloud subscriptions, no watermarks.
          </p>
        </div>

        <div className="flex items-center space-x-3 shrink-0">
          <button
            onClick={onRefresh}
            className="p-2.5 rounded-xl border border-studio-border text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
            title="Refresh projects"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={onNewProject}
            className="px-5 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 flex items-center space-x-2 transition-all active:scale-95"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="text-xs text-studio-muted font-medium">Total Projects</div>
          <div className="text-2xl font-bold text-white mt-1">{projects.length}</div>
        </div>
        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="text-xs text-studio-muted font-medium">Completed Exports</div>
          <div className="text-2xl font-bold text-emerald-400 mt-1">{storageStats?.exports_count || 0}</div>
        </div>
        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="text-xs text-studio-muted font-medium">App Storage Used</div>
          <div className="text-2xl font-bold text-white mt-1">{usedAppMb} MB</div>
        </div>
        <div className="p-4 rounded-xl bg-studio-card border border-studio-border">
          <div className="text-xs text-studio-muted font-medium">Local Disk Free</div>
          <div className="text-2xl font-bold text-indigo-400 mt-1">{freeGb} GB</div>
        </div>
      </div>

      {/* Projects List Header */}
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-bold text-white">Recent Projects</h2>
        <span className="text-xs text-studio-muted">{projects.length} {projects.length === 1 ? 'project' : 'projects'} saved locally</span>
      </div>

      {/* Projects Grid or Empty State */}
      {projects.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border-2 border-dashed border-studio-border bg-studio-card/20 space-y-4">
          <div className="w-16 h-16 mx-auto rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
            <Video className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-lg font-semibold text-white">No projects yet</h3>
            <p className="text-sm text-studio-muted max-w-md mx-auto mt-1">
              Import a podcast, gaming stream, or video presentation to automatically transcribe, find highlight candidates, and export vertical clips.
            </p>
          </div>
          <button
            onClick={onNewProject}
            className="px-6 py-2.5 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/20 transition-all inline-flex items-center space-x-2"
          >
            <Plus className="w-4 h-4" />
            <span>Create Your First Project</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {projects.map((project) => {
            const media = project.source_media;
            const thumbUrl = media?.thumbnail_path ? media.thumbnail_path : null;

            return (
              <div
                key={project.id}
                onClick={() => onSelectProject(project.id)}
                className="group relative rounded-2xl bg-studio-surface border border-studio-border hover:border-indigo-500/50 hover:shadow-xl hover:shadow-indigo-500/5 transition-all overflow-hidden cursor-pointer flex flex-col"
              >
                {/* Poster / Thumbnail */}
                <div className="aspect-video w-full bg-studio-card relative overflow-hidden flex items-center justify-center">
                  {thumbUrl ? (
                    <img
                      src={thumbUrl}
                      alt={project.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                    />
                  ) : (
                    <Video className="w-12 h-12 text-studio-border" />
                  )}
                  {media && (
                    <div className="absolute bottom-2.5 right-2.5 px-2 py-0.5 rounded bg-black/80 backdrop-blur-md text-white text-[11px] font-mono flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-studio-muted" />
                      <span>{formatDuration(media.duration)}</span>
                    </div>
                  )}
                  <div className="absolute top-2.5 left-2.5 px-2.5 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider bg-black/70 backdrop-blur-md text-white border border-white/10">
                    {project.status}
                  </div>
                </div>

                {/* Content */}
                <div className="p-5 flex-1 flex flex-col justify-between space-y-4">
                  <div>
                    <h3 className="font-semibold text-white group-hover:text-indigo-400 transition-colors line-clamp-1">
                      {project.title}
                    </h3>
                    {project.creator && (
                      <p className="text-xs text-studio-muted mt-0.5">by {project.creator}</p>
                    )}
                    <div className="flex items-center space-x-2 mt-2">
                      <span className="text-[11px] text-studio-muted">
                        Rights: <span className="text-studio-text font-medium">{project.rights_status}</span>
                      </span>
                      <span className="text-studio-border">•</span>
                      <span className="text-[11px] text-studio-muted">{formatDate(project.created_at)}</span>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-studio-border flex items-center justify-between">
                    <span className="text-xs font-medium text-indigo-400 flex items-center space-x-1 group-hover:translate-x-0.5 transition-transform">
                      <span>Open Studio</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </span>
                    <button
                      onClick={(e) => onDeleteProject(project.id, e)}
                      className="p-1.5 rounded-lg text-studio-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                      title="Delete project"
                    >
                      <Trash2 className="w-4 h-4" />
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
