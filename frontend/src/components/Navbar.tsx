import React from 'react';
import { Scissors, HardDrive, Cpu, Plus, Layers } from 'lucide-react';
import { StorageStats, SystemDiagnostics } from '../types';

interface NavbarProps {
  currentView: 'projects' | 'queue' | 'detail';
  setCurrentView: (view: 'projects' | 'queue') => void;
  onNewProject: () => void;
  onOpenSystemInfo: () => void;
  storageStats: StorageStats | null;
  diagnostics: SystemDiagnostics | null;
}

export const Navbar: React.FC<NavbarProps> = ({
  currentView,
  setCurrentView,
  onNewProject,
  onOpenSystemInfo,
  storageStats,
  diagnostics,
}) => {
  const freeGb = storageStats ? (storageStats.free_space_bytes / (1024 ** 3)).toFixed(1) : null;
  const isDiskWarning = diagnostics?.disk_warning;

  return (
    <header className="h-16 border-b border-studio-border bg-studio-surface/80 backdrop-blur-md sticky top-0 z-50 px-6 flex items-center justify-between">
      {/* Brand */}
      <div className="flex items-center space-x-3 cursor-pointer" onClick={() => setCurrentView('projects')}>
        <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-indigo-600 to-violet-500 flex items-center justify-center shadow-lg shadow-indigo-500/20">
          <Scissors className="w-5 h-5 text-white" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-tight text-white">StreamCut</span>
            <span className="text-xs px-2 py-0.5 rounded-full font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
              Studio
            </span>
          </div>
          <p className="text-[11px] text-studio-muted font-medium">Autonomous Local AI Video Clipper</p>
        </div>
      </div>

      {/* Navigation tabs */}
      <nav className="flex items-center space-x-1 bg-studio-bg/60 p-1 rounded-xl border border-studio-border">
        <button
          onClick={() => setCurrentView('projects')}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium transition-all ${
            currentView === 'projects' || currentView === 'detail'
              ? 'bg-studio-surface text-white shadow-sm'
              : 'text-studio-muted hover:text-white'
          }`}
        >
          Projects
        </button>
        <button
          onClick={() => setCurrentView('queue')}
          className={`px-4 py-1.5 rounded-lg text-sm font-medium flex items-center space-x-1.5 transition-all ${
            currentView === 'queue'
              ? 'bg-studio-surface text-white shadow-sm'
              : 'text-studio-muted hover:text-white'
          }`}
        >
          <Layers className="w-4 h-4" />
          <span>Job Queue</span>
        </button>
      </nav>

      {/* Actions and status */}
      <div className="flex items-center space-x-4">
        {/* Storage and System Info Pills */}
        <button
          onClick={onOpenSystemInfo}
          className={`flex items-center space-x-2 text-xs px-3 py-1.5 rounded-lg border transition-all ${
            isDiskWarning
              ? 'bg-amber-500/10 border-amber-500/30 text-amber-300'
              : 'bg-studio-card border-studio-border text-studio-muted hover:text-white hover:border-studio-border/80'
          }`}
          title="Click for System & Hardware Diagnostics"
        >
          <HardDrive className="w-3.5 h-3.5" />
          <span>{freeGb ? `${freeGb} GB Free` : 'Local Storage'}</span>
          <span className="text-studio-border">|</span>
          <Cpu className="w-3.5 h-3.5" />
          <span>{diagnostics?.gpu_available ? 'GPU' : 'CPU (int8)'}</span>
        </button>

        {/* New Project Button */}
        <button
          onClick={onNewProject}
          className="flex items-center space-x-2 px-4 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/25 transition-all active:scale-95"
        >
          <Plus className="w-4 h-4" />
          <span>New Project</span>
        </button>
      </div>
    </header>
  );
};
