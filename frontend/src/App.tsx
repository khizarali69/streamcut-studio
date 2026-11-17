import React, { useState, useEffect } from 'react';
import { Project, StorageStats, SystemDiagnostics } from './types';
import { fetchProjects, deleteProject, fetchStorageStats, fetchSystemDiagnostics } from './api';
import { Navbar } from './components/Navbar';
import { DashboardView } from './views/DashboardView';
import { ProjectDetailView } from './views/ProjectDetailView';
import { JobsQueueView } from './views/JobsQueueView';
import { ImportModal } from './views/ImportModal';
import { SettingsModal } from './views/SettingsModal';

export const App: React.FC = () => {
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<'projects' | 'queue' | 'detail'>('projects');
  
  const [isImportModalOpen, setIsImportModalOpen] = useState(false);
  const [isSettingsModalOpen, setIsSettingsModalOpen] = useState(false);
  
  const [storageStats, setStorageStats] = useState<StorageStats | null>(null);
  const [diagnostics, setDiagnostics] = useState<SystemDiagnostics | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const loadData = () => {
    setIsLoading(true);
    Promise.all([
      fetchProjects(),
      fetchStorageStats().catch(() => null),
      fetchSystemDiagnostics().catch(() => null),
    ])
      .then(([projs, stats, diag]) => {
        setProjects(projs);
        setStorageStats(stats);
        setDiagnostics(diag);
      })
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(() => {
      fetchStorageStats().then(setStorageStats).catch(() => {});
      if (currentView === 'projects') {
        fetchProjects().then(setProjects).catch(() => {});
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [currentView]);

  const handleSelectProject = (id: string) => {
    setSelectedProjectId(id);
    setCurrentView('detail');
  };

  const handleDeleteProject = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (window.confirm('Delete this project and its temporary media files?')) {
      await deleteProject(id);
      loadData();
      if (selectedProjectId === id) {
        setSelectedProjectId(null);
        setCurrentView('projects');
      }
    }
  };

  const handleProjectCreated = (newId: string) => {
    loadData();
    setSelectedProjectId(newId);
    setCurrentView('detail');
  };

  return (
    <div className="min-h-screen bg-studio-bg text-studio-text flex flex-col">
      {/* Top Navigation */}
      <Navbar
        currentView={currentView}
        setCurrentView={(view) => {
          setCurrentView(view);
          if (view === 'projects') setSelectedProjectId(null);
        }}
        onNewProject={() => setIsImportModalOpen(true)}
        onOpenSystemInfo={() => setIsSettingsModalOpen(true)}
        storageStats={storageStats}
        diagnostics={diagnostics}
      />

      {/* Main View Router */}
      <main className="flex-1">
        {currentView === 'projects' && (
          <DashboardView
            projects={projects}
            storageStats={storageStats}
            onSelectProject={handleSelectProject}
            onNewProject={() => setIsImportModalOpen(true)}
            onDeleteProject={handleDeleteProject}
            onRefresh={loadData}
            isLoading={isLoading}
          />
        )}

        {currentView === 'detail' && selectedProjectId && (
          <ProjectDetailView
            projectId={selectedProjectId}
            onBack={() => {
              setSelectedProjectId(null);
              setCurrentView('projects');
              loadData();
            }}
          />
        )}

        {currentView === 'queue' && <JobsQueueView />}
      </main>

      {/* Modals */}
      <ImportModal
        isOpen={isImportModalOpen}
        onClose={() => setIsImportModalOpen(false)}
        onProjectCreated={handleProjectCreated}
      />

      <SettingsModal
        isOpen={isSettingsModalOpen}
        onClose={() => setIsSettingsModalOpen(false)}
        diagnostics={diagnostics}
        storageStats={storageStats}
      />
    </div>
  );
};

export default App;
