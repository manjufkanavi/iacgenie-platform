import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ChevronRight, Home, Download, Eye, RotateCcw, StopCircle,
  FileCode, AlertTriangle, Loader2,
  Clock, Sparkles
} from 'lucide-react';
import toast from 'react-hot-toast';

function PageBreadcrumb({ pipelineId }: { pipelineId: string }): React.ReactElement {
  return (
    <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-slate-400 mb-4" data-testid="generator-breadcrumb">
      <Home className="w-4 h-4 hover:text-orange-500 cursor-pointer" />
      <ChevronRight className="w-3 h-3" />
      <span>Pipelines</span>
      <ChevronRight className="w-3 h-3" />
      <span className="hover:text-orange-500 cursor-pointer">{pipelineId}</span>
      <ChevronRight className="w-3 h-3" />
      <span className="text-gray-900 dark:text-slate-100 font-bold">Generate</span>
    </div>
  );
}

interface CodeFile {
  path: string;
  content: string;
  language: string;
  status: 'generated' | 'generating' | 'locked' | 'error';
  warning?: string;
}

const GeneratorAgentPanel: React.FC = () => {
  const navigate = useNavigate();
  const { id } = useParams<{ id: string }>();
  const pipelineId = id || 'abc123-def456';

  const [activeFile, setActiveFile] = useState('main.tf');
  const [generationProgress, setGenerationProgress] = useState(65);
  const [isGenerating, setIsGenerating] = useState(true);

  // Dynamic files state to support real-time streaming updates and warning auto-fixes!
  const [files, setFiles] = useState<CodeFile[]>([
    {
      path: 'main.tf',
      content: `resource "aws_eks_cluster" "cluster" {
  name     = "prod-cluster"
  version  = "1.28"
  role_arn = aws_iam_role.cluster.arn

  vpc_config {
    subnet_ids         = [aws_subnet.private.*.id]
    security_group_ids = [aws_security_group.cluster.id]
  }

  tags = {
    environment = "production"
    team        = "platform"
  }
}`,
      language: 'hcl',
      status: 'generated'
    },
    {
      path: 'variables.tf',
      content: `variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-west-2"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}`,
      language: 'hcl',
      status: 'generated'
    },
    {
      path: 'outputs.tf',
      content: `output "cluster_endpoint" {
  value = aws_eks_cluster.cluster.endpoint
}`,
      language: 'hcl',
      status: 'generated',
      warning: 'Security Alert: Output variable cluster_endpoint lacks a description or access constraint.'
    },
    {
      path: 'providers.tf',
      content: `terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}`,
      language: 'hcl',
      status: 'locked'
    },
    {
      path: 'README.md',
      content: `# Infrastructure as Code - EKS

Generated automatically by Iacgenie AI Generator Agent.
`,
      language: 'markdown',
      status: 'locked'
    }
  ]);

  // Dynamic logs history list
  const [logs, setLogs] = useState<Array<{ timestamp: string; stage: string; message: string; level: 'info' | 'warning' | 'error' }>>([
    { timestamp: '10:45:00', stage: 'GENERATE', message: 'Initialized Generator Agent runtime workspace', level: 'info' },
    { timestamp: '10:45:02', stage: 'GENERATE', message: 'Parsing target EKS specification and dependencies...', level: 'info' },
    { timestamp: '10:45:05', stage: 'GENERATE', message: 'Streaming main.tf configuration blocks...', level: 'info' },
    { timestamp: '10:45:08', stage: 'VALIDATE', message: 'Syntax validator successfully compiled main.tf', level: 'info' },
    { timestamp: '10:45:10', stage: 'VALIDATE', message: 'outputs.tf contains warning: cluster_endpoint output has no description metadata', level: 'warning' },
  ]);

  // Simulate dynamic progress stream
  useEffect(() => {
    if (generationProgress >= 100) {
      setIsGenerating(false);
      return;
    }

    const timer = setTimeout(() => {
      setGenerationProgress(prev => {
        const next = prev + 5;
        if (next >= 100) {
          setIsGenerating(false);
          setLogs(l => [
            ...l,
            { timestamp: '10:45:22', stage: 'COMPLETE', message: 'All target configurations generated and validated!', level: 'info' }
          ]);
          toast.success('HCL Generation complete!');
          return 100;
        }
        return next;
      });
    }, 1500);

    return () => clearTimeout(timer);
  }, [generationProgress]);

  // Interactive warning auto-fix triggers!
  const handleAutoFix = (filePath: string) => {
    setFiles(prevFiles =>
      prevFiles.map(file => {
        if (file.path === filePath) {
          return {
            ...file,
            content: `output "cluster_endpoint" {
  description = "The public endpoint URL of the generated EKS cluster"
  value       = aws_eks_cluster.cluster.endpoint
  sensitive   = false
}`,
            warning: undefined // Warning cleared!
          };
        }
        return file;
      })
    );

    setLogs(l => [
      ...l,
      { timestamp: new Date().toLocaleTimeString(), stage: 'AUTO-FIX', message: `Applied automated warning hotfix on ${filePath}`, level: 'info' }
    ]);

    toast.success(`Automatically fixed formatting and security warnings in ${filePath}!`);
  };

  const handleDownloadZip = () => {
    toast.success('Starting ZIP download for generated Terraform workspace files...');
  };

  const handlePreviewPlan = () => {
    toast.success('Analyzing Terraform Plan dry-run on current target setup...');
    navigate(`/plan-review/${pipelineId}`);
  };

  const handleRetry = () => {
    setIsGenerating(true);
    setGenerationProgress(20);
    toast.success('Retrying generation agent loop...');
  };

  return (
    <div className="max-w-7xl mx-auto px-4 py-6" data-testid="generator-agent-panel">
      {/* Breadcrumbs */}
      <PageBreadcrumb pipelineId={pipelineId} />

      {/* Agent State Header Card */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 mb-6 border-l-4 border-green-500">
        <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
          <div className="flex items-center gap-3.5">
            <div className="w-11 h-11 bg-green-50 rounded-xl flex items-center justify-center">
              <FileCode className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h1 className="text-2xl font-black text-slate-900 dark:text-slate-100">Generator Agent - HCL Synthesizer</h1>
              <p className="text-sm font-semibold text-slate-500 dark:text-slate-400 mt-0.5">Generating clean, responsive, dry-run validateable configurations.</p>
            </div>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold flex-wrap">
            <span className="flex items-center gap-1.5">
              <span className={`w-2.5 h-2.5 rounded-full ${isGenerating ? 'bg-brand-primary animate-pulse' : 'bg-green-500'}`} />
              <span className={isGenerating ? 'text-brand-primary font-bold uppercase tracking-wider' : 'text-green-500 font-bold uppercase tracking-wider'}>
                {isGenerating ? 'Generating HCL...' : 'Complete & Ready'}
              </span>
            </span>
            <span className="text-slate-300 dark:text-slate-600">|</span>
            <span className="text-slate-500 dark:text-slate-400">
              Files: <span className="font-bold text-slate-800 dark:text-slate-200">5/5</span>
            </span>
            <span className="text-slate-300 dark:text-slate-600">|</span>
            <span className="px-2.5 py-1 bg-slate-100 dark:bg-slate-700 rounded-lg text-slate-600 dark:text-slate-300">
              Model: Claude 3.5 Sonnet
            </span>
          </div>
        </div>
      </div>

      {/* Progress tracking section */}
      <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 mb-6 border border-slate-100 dark:border-slate-600">
        <div className="flex items-center justify-between mb-3 text-sm font-bold">
          <span className="text-slate-500 dark:text-slate-400">Synthesizer Stream Progress</span>
          <span className="text-green-600 uppercase tracking-wider">{generationProgress}%</span>
        </div>
        <div className="h-3 w-full bg-slate-100 dark:bg-slate-700 rounded-full overflow-hidden shadow-inner mb-3">
          <div
            className="h-full rounded-full bg-gradient-to-r from-green-500 to-emerald-400 transition-all duration-500"
            style={{ width: `${generationProgress}%` }}
          />
        </div>
        <div className="flex items-center gap-2 text-xs font-semibold text-slate-400 dark:text-slate-500">
          <Clock className="w-3.5 h-3.5 text-brand-primary" />
          <span>Estimated synthesis remaining: {isGenerating ? '~30 seconds' : 'Done'}</span>
        </div>
      </div>

      {/* Code Editor Matrix */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-6">
        {/* Left Tree Navigator + Validation Feedbacks (2 columns) */}
        <div className="lg:col-span-2 flex flex-col gap-6">
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-slate-100 dark:border-slate-600 flex flex-col h-[520px]">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider flex items-center gap-2">
                <FileCode className="w-4 h-4 text-brand-primary" />
                HCL File Tree Workspace
              </h2>
            </div>

            {/* Tree Nav list */}
            <div className="grid grid-cols-3 sm:grid-cols-5 gap-2 pb-4 mb-4 border-b border-slate-100 dark:border-slate-600" data-testid="generator-file-tree">
              {files.map((file) => (
                <button
                  key={file.path}
                  onClick={() => setActiveFile(file.path)}
                  className={`flex flex-col items-center justify-center p-3.5 rounded-xl border transition-all ${
                    activeFile === file.path
                      ? 'bg-brand-primary/5 border-brand-primary/20 text-brand-primary font-extrabold ring-1 ring-brand-primary/20'
                      : 'border-slate-200 dark:border-slate-600 text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-700/50'
                  }`}
                  data-testid={`file-tab-${file.path.replace('.', '-')}`}
                >
                  {file.status === 'generating' ? (
                    <Loader2 className="w-5 h-5 text-brand-primary animate-spin mb-1.5" />
                  ) : file.warning ? (
                    <AlertTriangle className="w-5 h-5 text-amber-500 mb-1.5 animate-pulse" />
                  ) : (
                    <FileCode className="w-5 h-5 text-slate-400 dark:text-slate-500 mb-1.5" />
                  )}
                  <span className="text-xs truncate w-full text-center">{file.path}</span>
                </button>
              ))}
            </div>

            {/* Premium Code Viewer Block */}
            <div className="flex-1 bg-slate-900 rounded-xl p-5 font-mono text-xs overflow-auto shadow-inner text-green-400 border border-slate-850 h-[320px]">
              <pre>{files.find((f) => f.path === activeFile)?.content || '// Select a workspace file to view configuration'}</pre>
            </div>
          </div>
        </div>

        {/* Right Sidebar - Validation, Active Warnings & Auto-Fix Actions */}
        <div className="lg:col-span-1 flex flex-col gap-6">
          {/* Active warnings and auto-fix block */}
          <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-slate-100 dark:border-slate-600 flex flex-col h-[520px]">
            <h2 className="text-sm font-bold text-slate-400 dark:text-slate-500 uppercase tracking-wider mb-5 flex items-center gap-2">
              <Sparkles className="w-4 h-4 text-brand-primary" />
              Validation & Auto-Fixes
            </h2>

            {/* Check results */}
            <div className="space-y-4 flex-1 overflow-y-auto pr-1">
              {files.map((file) => (
                <div
                  key={file.path}
                  className={`p-4 rounded-xl border transition ${
                    file.warning
                      ? 'bg-amber-50/50 border-amber-200 text-amber-900'
                      : file.status === 'locked'
                      ? 'bg-slate-50 dark:bg-slate-700/50 border-slate-200 dark:border-slate-600 text-slate-400 dark:text-slate-500'
                      : 'bg-green-50/50 border-green-200 text-green-900'
                  }`}
                  data-testid={`validation-card-${file.path.replace('.', '-')}`}
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold uppercase tracking-wider">{file.path}</span>
                    {file.warning ? (
                      <span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-black uppercase">Warning</span>
                    ) : (
                      <span className="px-2 py-0.5 rounded bg-green-100 text-green-800 text-[10px] font-black uppercase">Passed</span>
                    )}
                  </div>

                  {file.warning ? (
                    <div className="mt-3">
                      <p className="text-xs font-semibold leading-relaxed mb-3">{file.warning}</p>
                      <button
                        onClick={() => handleAutoFix(file.path)}
                        className="w-full flex items-center justify-center gap-1.5 py-2 px-3 bg-amber-600 text-white rounded-lg text-xs font-bold uppercase tracking-wider hover:bg-amber-700 transition shadow"
                        data-testid={`autofix-button-${file.path.replace('.', '-')}`}
                      >
                        <Sparkles className="w-3.5 h-3.5" />
                        Auto-Fix Warning
                      </button>
                    </div>
                  ) : (
                    <p className="text-xs font-semibold mt-2">Zero warnings or errors identified.</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* Terminal Logs & Action buttons */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        {/* Terminal Logs console */}
        <div className="md:col-span-2 bg-slate-900 rounded-2xl shadow-xl p-5 font-mono text-xs text-white border border-slate-800 h-64 overflow-y-auto">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-3 text-slate-500 font-bold uppercase text-[10px] tracking-wider">
            <span>Terminal Outputs & Validator Streams</span>
            <span>gemini-engine // active</span>
          </div>
          <div className="space-y-2">
            {logs.map((log, idx) => (
              <div key={idx} className="flex items-start gap-2">
                <span className="text-slate-600 flex-shrink-0">[{log.timestamp}]</span>
                <span className={`font-extrabold flex-shrink-0 text-[10px] tracking-wider ${
                  log.level === 'warning' ? 'text-amber-500' : log.level === 'error' ? 'text-red-500' : 'text-blue-400'
                }`}>
                  [{log.stage}]
                </span>
                <span className={`font-semibold ${log.level === 'warning' ? 'text-amber-200' : 'text-slate-300'}`}>
                  {log.message}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Global Action matrix card */}
        <div className="bg-white dark:bg-slate-800 rounded-2xl shadow-lg p-6 border border-gray-100 flex flex-col justify-between h-64">
          <div>
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-2">Workspace Actions</h3>
            <p className="text-xs text-gray-500 font-medium">Download zip bundles or dry-run and inspect details.</p>
          </div>

          <div className="space-y-2.5">
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleDownloadZip}
                className="w-full flex items-center justify-center gap-1 py-2.5 px-3 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-xs font-bold hover:bg-gray-100 transition shadow-sm"
              >
                <Download className="w-4 h-4 text-brand-primary" />
                ZIP Download
              </button>
              <button
                onClick={handlePreviewPlan}
                className="w-full flex items-center justify-center gap-1 py-2.5 px-3 bg-gradient-to-r from-brand-primary to-red-500 text-white rounded-xl text-xs font-bold hover:from-brand-primary/90 hover:to-red-600 transition shadow-md"
              >
                <Eye className="w-4 h-4" />
                Preview Plan
              </button>
            </div>
            <div className="grid grid-cols-2 gap-2">
              <button
                onClick={handleRetry}
                className="w-full flex items-center justify-center gap-1 py-2.5 px-3 bg-gray-50 border border-gray-200 text-gray-700 rounded-xl text-xs font-bold hover:bg-gray-100 transition shadow-sm"
              >
                <RotateCcw className="w-4 h-4 text-brand-primary" />
                Retry Agent
              </button>
              <button
                onClick={() => {
                  setIsGenerating(false);
                  toast.success('HCL Generation aborted by developer.');
                }}
                className="w-full flex items-center justify-center gap-1 py-2.5 px-3 bg-red-50 border border-red-100 text-red-700 rounded-xl text-xs font-bold hover:bg-red-100 transition shadow-sm"
              >
                <StopCircle className="w-4 h-4" />
                Abort Loop
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export { GeneratorAgentPanel };
export default GeneratorAgentPanel;