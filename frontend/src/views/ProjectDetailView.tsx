import React, { useState, useEffect } from 'react';
import { ArrowLeft, Video, Sparkles, Scissors, Download, RefreshCw } from 'lucide-react';
import { Project, ClipCandidate } from '../types';
import { fetchProject, fetchClips } from '../api';
import { AnalysisTab } from './AnalysisTab';
import { ClipsTab } from './ClipsTab';
import { EditorTab } from './EditorTab';
import { ExportsTab } from './ExportsTab';

interface ProjectDetailViewProps {
  projectId: string;
  onBack: () => void;
}

export const ProjectDetailView: React.FC<ProjectDetailViewProps> = ({ projectId, onBack }) => {
  const [project, setProject] = useState<Project | null>(null);
  const [clips, setClips] = useState<ClipCandidate[]>([]);
  const [activeTab, setActiveTab] = useState<'analysis' | 'clips' | 'editor' | 'exports'>('analysis');
  const [activeClipId, setActiveClipId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const loadData = () => {
    setIsLoading(true);
    Promise.all([fetchProject(projectId), fetchClips(projectId).catch(() => [])])
      .then(([projData, clipsData]) => {
        setProject(projData);
        setClips(clipsData);
        if (clipsData.length > 0 && !activeClipId) {
          setActiveClipId(clipsData[0].id);
        }
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadData();
    // Poll project status if actively processing
    const interval = setInterval(() => {
      fetchProject(projectId).then((p) => {
        setProject(p);
        if (p.status === 'ready' || p.status === 'transcribed') {
          fetchClips(projectId).then(setClips).catch(() => {});
        }
      });
    }, 4000);
    return () => clearInterval(interval);
  }, [projectId]);

  if (!project) {
    return (
      <div className="max-w-7xl mx-auto px-6 py-12 text-center text-studio-muted">
        Loading project workspace...
      </div>
    );
  }

  return (
    <div className="max-w-7xl mx-auto px-6 py-6 space-y-6 animate-fadeIn">
      {/* Back and Project Header */}
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center space-x-4">
          <button
            onClick={onBack}
            className="p-2.5 rounded-xl border border-studio-border text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
            title="Back to Dashboard"
          >
            <ArrowLeft className="w-5 h-5" />
          </button>
          <div>
            <div className="flex items-center space-x-2">
              <h1 className="text-xl font-bold text-white tracking-tight">{project.title}</h1>
              <span className="text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                {project.status}
              </span>
            </div>
            {project.creator && (
              <p className="text-xs text-studio-muted mt-0.5">Creator: {project.creator} • Rights: {project.rights_status}</p>
            )}
          </div>
        </div>

        {/* Workspace Mode Tabs */}
        <div className="flex items-center space-x-1 p-1 bg-studio-surface rounded-xl border border-studio-border">
          <button
            onClick={() => setActiveTab('analysis')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'analysis'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-studio-muted hover:text-white'
            }`}
          >
            <Video className="w-3.5 h-3.5" />
            <span>Analysis & Script</span>
          </button>

          <button
            onClick={() => setActiveTab('clips')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'clips'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-studio-muted hover:text-white'
            }`}
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Candidate Clips ({clips.length})</span>
          </button>

          <button
            onClick={() => {
              if (clips.length > 0 && !activeClipId) setActiveClipId(clips[0].id);
              setActiveTab('editor');
            }}
            disabled={clips.length === 0}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all disabled:opacity-40 ${
              activeTab === 'editor'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-studio-muted hover:text-white'
            }`}
          >
            <Scissors className="w-3.5 h-3.5" />
            <span>Clip Editor</span>
          </button>

          <button
            onClick={() => setActiveTab('exports')}
            className={`px-3.5 py-1.5 rounded-lg text-xs font-semibold flex items-center space-x-1.5 transition-all ${
              activeTab === 'exports'
                ? 'bg-indigo-600 text-white shadow-sm'
                : 'text-studio-muted hover:text-white'
            }`}
          >
            <Download className="w-3.5 h-3.5" />
            <span>Exports</span>
          </button>
        </div>
      </div>

      {/* Tab Panels */}
      {activeTab === 'analysis' && (
        <AnalysisTab
          project={project}
          onNavigateToClips={() => {
            fetchClips(projectId).then(setClips);
            setActiveTab('clips');
          }}
          onProjectUpdated={loadData}
        />
      )}

      {activeTab === 'clips' && (
        <ClipsTab
          project={project}
          clips={clips}
          onSelectClipForEdit={(cid) => {
            setActiveClipId(cid);
            setActiveTab('editor');
          }}
          onClipsChanged={() => fetchClips(projectId).then(setClips)}
          onNavigateToExports={() => setActiveTab('exports')}
        />
      )}

      {activeTab === 'editor' && activeClipId && (
        <EditorTab
          project={project}
          clipId={activeClipId}
          onNavigateToExports={() => setActiveTab('exports')}
        />
      )}

      {activeTab === 'exports' && <ExportsTab project={project} />}
    </div>
  );
};
