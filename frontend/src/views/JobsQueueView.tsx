import React, { useState, useEffect } from 'react';
import { Layers, RefreshCw, XCircle, RotateCcw, CheckCircle2, Clock, AlertTriangle } from 'lucide-react';
import { Job } from '../types';
import { fetchJobs, cancelJob, retryJob } from '../api';

export const JobsQueueView: React.FC = () => {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const loadJobs = () => {
    setIsLoading(true);
    fetchJobs()
      .then(setJobs)
      .finally(() => setIsLoading(false));
  };

  useEffect(() => {
    loadJobs();
    const interval = setInterval(loadJobs, 2500);
    return () => clearInterval(interval);
  }, []);

  const handleCancel = async (jobId: string) => {
    await cancelJob(jobId);
    loadJobs();
  };

  const handleRetry = async (jobId: string) => {
    await retryJob(jobId);
    loadJobs();
  };

  return (
    <div className="max-w-5xl mx-auto px-6 py-8 space-y-6 animate-fadeIn">
      {/* Header */}
      <div className="p-6 rounded-2xl bg-studio-surface border border-studio-border flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-xl bg-indigo-500/10 border border-indigo-500/20 text-indigo-400">
            <Layers className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-white tracking-tight">Background Processing Queue</h1>
            <p className="text-xs text-studio-muted">
              Durable SQLite queue managing media probes, Whisper speech-to-text, and FFmpeg video rendering.
            </p>
          </div>
        </div>

        <button
          onClick={loadJobs}
          className="p-2.5 rounded-xl border border-studio-border text-studio-muted hover:text-white hover:bg-studio-card transition-colors"
          title="Refresh Queue"
        >
          <RefreshCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {/* Jobs List */}
      {jobs.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border-2 border-dashed border-studio-border bg-studio-card/20 text-studio-muted">
          No background jobs in queue.
        </div>
      ) : (
        <div className="space-y-4">
          {jobs.map((job) => {
            const isProcessing = job.status === 'processing';
            const isQueued = job.status === 'queued';
            const isFailed = job.status === 'failed';
            const isCompleted = job.status === 'completed';
            const isCanceled = job.status === 'canceled';

            return (
              <div
                key={job.id}
                className="p-5 rounded-2xl bg-studio-surface border border-studio-border space-y-3 shadow-md"
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <span
                      className={`w-2.5 h-2.5 rounded-full ${
                        isProcessing
                          ? 'bg-indigo-400 animate-ping'
                          : isQueued
                          ? 'bg-amber-400'
                          : isCompleted
                          ? 'bg-emerald-400'
                          : 'bg-red-400'
                      }`}
                    />
                    <div>
                      <h3 className="font-semibold text-white text-sm">
                        {job.job_type.replace(/_/g, ' ').toUpperCase()}
                      </h3>
                      <p className="text-xs text-studio-muted mt-0.5">
                        Job ID: <span className="font-mono">{job.id.slice(0, 8)}</span> • Project: {job.project_id.slice(0, 8)}
                      </p>
                    </div>
                  </div>

                  {/* Actions & Status */}
                  <div className="flex items-center space-x-3">
                    <span
                      className={`text-xs px-2.5 py-0.5 rounded-full font-semibold uppercase tracking-wider ${
                        isProcessing
                          ? 'bg-indigo-500/10 text-indigo-400 border border-indigo-500/30'
                          : isCompleted
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                          : isFailed
                          ? 'bg-red-500/10 text-red-400 border border-red-500/30'
                          : 'bg-studio-bg text-studio-muted border border-studio-border'
                      }`}
                    >
                      {job.status}
                    </span>

                    {(isProcessing || isQueued) && (
                      <button
                        onClick={() => handleCancel(job.id)}
                        className="p-1.5 rounded-lg text-studio-muted hover:text-red-400 hover:bg-red-500/10 transition-colors"
                        title="Cancel Job"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
                    )}

                    {(isFailed || isCanceled) && (
                      <button
                        onClick={() => handleRetry(job.id)}
                        className="px-3 py-1 rounded-lg text-xs font-semibold bg-studio-card border border-studio-border text-white hover:border-indigo-500/50 flex items-center space-x-1.5 transition-colors"
                        title="Retry Job"
                      >
                        <RotateCcw className="w-3.5 h-3.5 text-indigo-400" />
                        <span>Retry</span>
                      </button>
                    )}
                  </div>
                </div>

                {/* Progress bar and stage info */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs text-studio-muted">
                    <span>{job.progress_stage || 'Processing...'}</span>
                    <span className="font-mono text-white">{job.progress.toFixed(0)}%</span>
                  </div>
                  <div className="w-full h-1.5 bg-studio-bg rounded-full overflow-hidden border border-studio-border">
                    <div
                      className={`h-full transition-all duration-300 ${
                        isFailed ? 'bg-red-500' : isCompleted ? 'bg-emerald-500' : 'bg-indigo-500'
                      }`}
                      style={{ width: `${Math.max(5, job.progress)}%` }}
                    />
                  </div>
                </div>

                {job.error_message && (
                  <div className="p-3 rounded-xl bg-red-500/10 border border-red-500/20 text-xs text-red-400 flex items-start space-x-2">
                    <AlertTriangle className="w-4 h-4 shrink-0 mt-0.5" />
                    <span>{job.error_message}</span>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
};
