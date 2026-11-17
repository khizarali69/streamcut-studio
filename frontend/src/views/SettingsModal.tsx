import React from 'react';
import { HardDrive, Cpu, X, ShieldCheck, AlertCircle, Info, ExternalLink } from 'lucide-react';
import { SystemDiagnostics, StorageStats } from '../types';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
  diagnostics: SystemDiagnostics | null;
  storageStats: StorageStats | null;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({
  isOpen,
  onClose,
  diagnostics,
  storageStats,
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div className="bg-studio-surface border border-studio-border rounded-2xl w-full max-w-xl max-h-[90vh] overflow-y-auto shadow-2xl">
        {/* Header */}
        <div className="p-6 border-b border-studio-border flex items-center justify-between">
          <div className="flex items-center space-x-2.5">
            <Cpu className="w-5 h-5 text-indigo-400" />
            <h2 className="text-lg font-bold text-white">System & Hardware Diagnostics</h2>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Local Compute Principles Disclosure */}
          <div className="p-4 rounded-xl bg-studio-bg border border-studio-border space-y-2">
            <div className="flex items-center space-x-2 text-xs font-semibold text-emerald-400 uppercase tracking-wider">
              <ShieldCheck className="w-4 h-4" />
              <span>Self-Hosted & Private Architecture</span>
            </div>
            <p className="text-xs text-studio-muted leading-relaxed">
              StreamCut Studio operates entirely on your local machine. Source videos, audio tracks, and transcripts never leave your hardware. No monthly subscription or API key is required.
            </p>
            <div className="p-3 rounded-lg bg-studio-card border border-studio-border/60 text-[11px] text-studio-muted">
              <span className="text-white font-medium">Important note:</span> While there are no cloud subscription fees, running heavy video encoding and Whisper inference incurs local CPU/GPU compute power and disk utilization.
            </div>
          </div>

          {/* Diagnostics Grid */}
          <div className="space-y-3">
            <h3 className="text-xs font-semibold text-studio-muted uppercase tracking-wider">Engine Status</h3>
            <div className="grid grid-cols-2 gap-3 text-xs">
              <div className="p-3 rounded-xl bg-studio-bg border border-studio-border">
                <span className="text-studio-muted block">FFmpeg & libass</span>
                <span className="text-white font-medium font-mono text-[11px] block mt-1 line-clamp-1">
                  {diagnostics?.ffmpeg || 'Active'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-studio-bg border border-studio-border">
                <span className="text-studio-muted block">Whisper Model</span>
                <span className="text-white font-medium block mt-1">
                  {diagnostics?.whisper_model} ({diagnostics?.whisper_compute_type})
                </span>
              </div>
              <div className="p-3 rounded-xl bg-studio-bg border border-studio-border">
                <span className="text-studio-muted block">Compute Device</span>
                <span className="text-white font-medium block mt-1">
                  {diagnostics?.gpu_available ? diagnostics.gpu_name : 'CPU Multithreaded (int8)'}
                </span>
              </div>
              <div className="p-3 rounded-xl bg-studio-bg border border-studio-border">
                <span className="text-studio-muted block">Disk Free Space</span>
                <span className="text-indigo-400 font-mono font-medium block mt-1">
                  {diagnostics?.disk_free_gb} GB / {diagnostics?.disk_total_gb} GB
                </span>
              </div>
            </div>
          </div>

          {/* Disk Warning if low */}
          {diagnostics?.disk_warning && (
            <div className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 text-xs flex items-start space-x-3">
              <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block">Low Disk Space Warning</span>
                <span>You have less than 10GB of free disk space remaining. Processing long 4K videos may require additional scratch storage.</span>
              </div>
            </div>
          )}

          {/* Optional Paid Integration Disclosure */}
          <div className="p-4 rounded-xl bg-studio-bg border border-studio-border space-y-2">
            <div className="flex items-center space-x-1.5 text-xs font-semibold text-studio-muted uppercase tracking-wider">
              <Info className="w-4 h-4 text-indigo-400" />
              <span>Optional External LLM Providers</span>
            </div>
            <p className="text-xs text-studio-muted leading-relaxed">
              Paid AI services (like OpenAI API or Anthropic) are completely disabled by default. If enabled in configuration, only text transcripts (never raw video files) are transmitted to the configured endpoint.
            </p>
          </div>

          <div className="pt-2 flex justify-end">
            <button
              onClick={onClose}
              className="px-5 py-2 rounded-xl text-xs font-semibold bg-studio-card border border-studio-border text-white hover:bg-studio-border/50 transition-colors"
            >
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
