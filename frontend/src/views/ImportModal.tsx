import React, { useState, useRef } from 'react';
import { Upload, Link as LinkIcon, AlertCircle, FileVideo, ShieldAlert, CheckCircle2, X } from 'lucide-react';
import { createProject, uploadMedia, importMediaFromUrl } from '../api';
import { RightsStatus } from '../types';

interface ImportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onProjectCreated: (projectId: string) => void;
}

export const ImportModal: React.FC<ImportModalProps> = ({ isOpen, onClose, onProjectCreated }) => {
  if (!isOpen) return null;

  const [activeTab, setActiveTab] = useState<'upload' | 'url'>('upload');
  const [title, setTitle] = useState('');
  const [creator, setCreator] = useState('');
  const [sourceUrl, setSourceUrl] = useState('');
  const [rightsStatus, setRightsStatus] = useState<RightsStatus>('owned');
  const [rightsNotes, setRightsNotes] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      setSelectedFile(file);
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setSelectedFile(file);
      if (!title) {
        setTitle(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMsg(null);

    if (!title.trim()) {
      setErrorMsg('Please specify a project title');
      return;
    }

    if (activeTab === 'upload' && !selectedFile) {
      setErrorMsg('Please select a video file to upload');
      return;
    }

    if (activeTab === 'url' && !sourceUrl.trim()) {
      setErrorMsg('Please provide a direct media URL');
      return;
    }

    try {
      setIsSubmitting(true);
      // 1. Create project
      const project = await createProject({
        title: title.trim(),
        creator: creator.trim() || undefined,
        source_url: activeTab === 'url' ? sourceUrl.trim() : undefined,
        rights_status: rightsStatus,
        rights_notes: rightsNotes.trim() || undefined,
      });

      // 2. Upload file or import URL
      if (activeTab === 'upload' && selectedFile) {
        await uploadMedia(project.id, selectedFile, (pct) => setUploadProgress(pct));
      } else if (activeTab === 'url') {
        await importMediaFromUrl(project.id, sourceUrl.trim());
      }

      onProjectCreated(project.id);
      onClose();
    } catch (err: any) {
      setErrorMsg(err.message || 'Failed to import video');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-studio-surface border border-studio-border rounded-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-studio-border flex items-center justify-between">
          <div>
            <h2 className="text-xl font-bold text-white">Import Source Media</h2>
            <p className="text-xs text-studio-muted mt-1">
              Import long-form videos to autonomously analyze, transcribe, and generate vertical short clips.
            </p>
          </div>
          <button
            onClick={onClose}
            disabled={isSubmitting}
            className="p-2 text-studio-muted hover:text-white rounded-lg hover:bg-studio-card transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-6">
          {errorMsg && (
            <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/20 text-red-400 text-sm flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <span>{errorMsg}</span>
            </div>
          )}

          {/* Import Method Tabs */}
          <div className="flex space-x-2 p-1 bg-studio-bg rounded-xl border border-studio-border">
            <button
              type="button"
              onClick={() => setActiveTab('upload')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg flex items-center justify-center space-x-2 transition-all ${
                activeTab === 'upload' ? 'bg-studio-card text-white shadow-sm' : 'text-studio-muted hover:text-white'
              }`}
            >
              <Upload className="w-4 h-4" />
              <span>File Upload</span>
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('url')}
              className={`flex-1 py-2 text-sm font-medium rounded-lg flex items-center justify-center space-x-2 transition-all ${
                activeTab === 'url' ? 'bg-studio-card text-white shadow-sm' : 'text-studio-muted hover:text-white'
              }`}
            >
              <LinkIcon className="w-4 h-4" />
              <span>Direct URL</span>
            </button>
          </div>

          {/* Upload Zone */}
          {activeTab === 'upload' ? (
            <div>
              <div
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={() => fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-all ${
                  isDragging
                    ? 'border-indigo-500 bg-indigo-500/10'
                    : selectedFile
                    ? 'border-emerald-500/50 bg-emerald-500/5'
                    : 'border-studio-border hover:border-studio-border/80 bg-studio-card/40'
                }`}
              >
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileSelect}
                  accept=".mp4,.mov,.mkv,.webm,.avi,.m4v"
                  className="hidden"
                />
                {selectedFile ? (
                  <div className="flex flex-col items-center space-y-2">
                    <FileVideo className="w-10 h-10 text-emerald-400" />
                    <span className="font-medium text-white">{selectedFile.name}</span>
                    <span className="text-xs text-studio-muted">
                      {(selectedFile.size / (1024 * 1024)).toFixed(1)} MB • Click to replace
                    </span>
                  </div>
                ) : (
                  <div className="flex flex-col items-center space-y-2">
                    <Upload className="w-10 h-10 text-studio-muted" />
                    <span className="text-sm font-medium text-white">Drag & drop video file here, or click to browse</span>
                    <span className="text-xs text-studio-muted">Supports MP4, MOV, MKV, WebM up to 4GB</span>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <label className="text-xs font-semibold text-studio-muted uppercase tracking-wider">
                Direct Video Stream URL
              </label>
              <input
                type="url"
                value={sourceUrl}
                onChange={(e) => setSourceUrl(e.target.value)}
                placeholder="https://example.com/videos/gameplay-stream.mp4"
                className="w-full px-4 py-2.5 rounded-xl bg-studio-bg border border-studio-border text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <p className="text-[11px] text-studio-muted flex items-center space-x-1">
                <span>Requires authorized direct public media streams. Internal IPs and DRM bypass are blocked.</span>
              </p>
            </div>
          )}

          {/* Metadata Fields */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-studio-muted uppercase tracking-wider mb-1.5">
                Project Title *
              </label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Elden Ring Boss Fight Reaction"
                required
                className="w-full px-4 py-2.5 rounded-xl bg-studio-bg border border-studio-border text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
            <div>
              <label className="block text-xs font-semibold text-studio-muted uppercase tracking-wider mb-1.5">
                Creator / Streamer
              </label>
              <input
                type="text"
                value={creator}
                onChange={(e) => setCreator(e.target.value)}
                placeholder="e.g., Original Author / Channel"
                className="w-full px-4 py-2.5 rounded-xl bg-studio-bg border border-studio-border text-white text-sm focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>
          </div>

          {/* Rights & Licensing Disclosure */}
          <div className="p-4 rounded-xl bg-studio-bg border border-studio-border space-y-3">
            <div className="flex items-center space-x-2 text-xs font-semibold text-studio-muted uppercase tracking-wider">
              <ShieldAlert className="w-4 h-4 text-indigo-400" />
              <span>Content Rights & Compliance</span>
            </div>

            <div>
              <label className="block text-xs text-studio-muted mb-1">Your Rights Status</label>
              <select
                value={rightsStatus}
                onChange={(e) => setRightsStatus(e.target.value as RightsStatus)}
                className="w-full px-3 py-2 rounded-lg bg-studio-card border border-studio-border text-white text-sm focus:outline-none focus:border-indigo-500"
              >
                <option value="owned">Owned (Original self-created content)</option>
                <option value="permission_granted">Permission Granted (Explicit consent from creator)</option>
                <option value="licensed">Licensed (Commercial or Creative Commons license)</option>
                <option value="unknown">Unknown (Private analysis only)</option>
              </select>
            </div>

            <div>
              <input
                type="text"
                value={rightsNotes}
                onChange={(e) => setRightsNotes(e.target.value)}
                placeholder="Optional licensing notes or source attribution details..."
                className="w-full px-3 py-2 rounded-lg bg-studio-card border border-studio-border text-white text-xs focus:outline-none focus:border-indigo-500"
              />
            </div>

            <p className="text-[11px] text-studio-muted leading-relaxed">
              Notice: Exported short clips do not become copyright-free. StreamCut Studio does not guarantee viral performance. Use permitted media only.
            </p>
          </div>

          {/* Upload Progress */}
          {isSubmitting && (
            <div className="space-y-2">
              <div className="flex justify-between text-xs text-studio-muted">
                <span>{uploadProgress < 100 ? 'Uploading media...' : 'Processing video & extracting metadata...'}</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-2 bg-studio-bg rounded-full overflow-hidden border border-studio-border">
                <div
                  className="h-full bg-indigo-500 transition-all duration-300"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {/* Footer Actions */}
          <div className="pt-2 flex justify-end space-x-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="px-4 py-2 rounded-xl text-sm font-medium text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="px-6 py-2 rounded-xl text-sm font-semibold bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white shadow-lg shadow-indigo-600/25 transition-all"
            >
              {isSubmitting ? 'Importing...' : 'Create Project'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
