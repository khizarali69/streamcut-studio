import React, { useState, useEffect } from 'react';
import { Download, FileVideo, CheckCircle2, Archive, RefreshCw, FileText } from 'lucide-react';
import { Project, ExportArtifact } from '../types';
import { fetchProjectExports } from '../api';

interface ExportsTabProps {
  project: Project;
}

export const ExportsTab: React.FC<ExportsTabProps> = ({ project }) => {
  const [exports, setExports] = useState<ExportArtifact[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadExports = () => {
    setIsLoading(true);
    fetchProjectExports(project.id)
      .then(setExports)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadExports();
  }, [project.id]);

  return (
    <div className="space-y-6">
      {/* Header and Download All ZIP */}
      <div className="p-4 rounded-2xl bg-studio-surface border border-studio-border flex items-center justify-between">
        <div>
          <h3 className="font-bold text-white text-base">Completed Video Exports</h3>
          <p className="text-xs text-studio-muted">
            Rendered, ffprobe-validated MP4 files with burned-in subtitles and optional SRT/VTT sidecars.
          </p>
        </div>

        <div className="flex items-center space-x-3">
          <button
            onClick={loadExports}
            className="p-2 rounded-xl border border-studio-border text-studio-muted hover:text-white transition-colors"
            title="Refresh exports"
          >
            <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>

          {exports.length > 0 && (
            <a
              href={`/api/projects/${project.id}/exports/zip`}
              download
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-md flex items-center space-x-1.5 transition-all"
            >
              <Archive className="w-3.5 h-3.5" />
              <span>Download All as ZIP</span>
            </a>
          )}
        </div>
      </div>

      {/* Exports List */}
      {exports.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border-2 border-dashed border-studio-border bg-studio-card/20 space-y-3">
          <FileVideo className="w-10 h-10 text-studio-muted mx-auto" />
          <h4 className="font-semibold text-white">No completed exports yet</h4>
          <p className="text-xs text-studio-muted max-w-sm mx-auto">
            Render a clip from the Candidate Clips tab or Clip Editor to produce final social-ready MP4 files.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {exports.map((exp) => (
            <div
              key={exp.id}
              className="rounded-2xl bg-studio-surface border border-studio-border overflow-hidden flex flex-col justify-between shadow-lg"
            >
              {/* Video Player */}
              <div className="aspect-video bg-black relative flex items-center justify-center">
                <video
                  src={exp.download_url}
                  controls
                  className="w-full h-full object-contain"
                />
              </div>

              {/* Metadata */}
              <div className="p-5 space-y-3 flex-1 flex flex-col justify-between">
                <div>
                  <h4 className="font-semibold text-white text-sm line-clamp-1">{exp.filename}</h4>
                  <div className="flex items-center space-x-2 text-xs text-studio-muted mt-1">
                    <span>{exp.width}x{exp.height}</span>
                    <span>•</span>
                    <span>{exp.duration.toFixed(1)}s</span>
                    <span>•</span>
                    <span>{(exp.file_size / (1024 * 1024)).toFixed(1)} MB</span>
                  </div>
                  {exp.ffprobe_valid && (
                    <div className="flex items-center space-x-1 text-[11px] text-emerald-400 font-medium mt-2">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>ffprobe Validated & Playable</span>
                    </div>
                  )}
                </div>

                {/* Downloads */}
                <div className="pt-3 border-t border-studio-border flex items-center justify-between gap-2">
                  <a
                    href={exp.download_url}
                    download={exp.filename}
                    className="flex-1 py-2 px-3 rounded-xl text-xs font-semibold bg-indigo-600 hover:bg-indigo-500 text-white flex items-center justify-center space-x-1.5 transition-colors"
                  >
                    <Download className="w-3.5 h-3.5" />
                    <span>Download MP4</span>
                  </a>

                  {exp.srt_url && (
                    <a
                      href={exp.srt_url}
                      download
                      className="p-2 rounded-xl bg-studio-card border border-studio-border text-studio-muted hover:text-white transition-colors"
                      title="Download SRT"
                    >
                      <FileText className="w-4 h-4" />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
