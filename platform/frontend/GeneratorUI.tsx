import React, { useState, useCallback, useEffect } from 'react';
import { CloudProvider, GeneratedCode, GeneratedFile, LogEntry, GenerationStatus, ValidationStepLog, PipelinePhase, PhaseStatus } from '../types';
import { startGeneration, pollGenerationStatus, downloadProject, submitClarifyAnswer } from '../services/geminiService';
import Button from './ui/Button';
import Card from './ui/Card';
import { AVAILABLE_MODELS } from '../constants';
import { useAppStore } from '../store/useAppStore';
import { useProjectStore } from '../store/useProjectStore';
import toast from 'react-hot-toast';
import { getAuthHeaders } from '../services/authHeaders';
import { usePipelineWebSocket } from '../hooks/usePipelineWebSocket';
import PromptCanvas from './pipeline/PromptCanvas';
import MonacoWorkspacePanel from './ui/MonacoWorkspacePanel';
import AiChatPromptBar from './ui/AiChatPromptBar';
import PipelineRail, { RailPhaseState } from './pipeline/PipelineRail';
import ConversationalClarifyAgent from './pipeline/ConversationalClarifyAgent';
import InlineReviewPanel from './pipeline/InlineReviewPanel';
import UnifiedAgentLog from './pipeline/UnifiedAgentLog';
import { motion, AnimatePresence } from 'framer-motion';
import { workflowService } from '../services/workflowService';



const GeneratorUI: React.FC = () => {
  const { generatorConfig, setGeneratorConfig, modelConfigs, lastGenerationMetadata } = useAppStore();
  const { currentProjectId } = useProjectStore();
  const { model, provider } = generatorConfig;

  const [prompt, setPrompt] = useState<string>('Deploy an EKS cluster with Redis and install OpenLiteSpeed with Helm and cert-manager in us-west-2');
  
  const [generationStatus, setGenerationStatus] = useState<GenerationStatus>('pending');
  const [validationLogs, setValidationLogs] = useState<ValidationStepLog[]>([]);
  const [generatedCode, setGeneratedCode] = useState<GeneratedCode | null>(null);
  const [_error, setError] = useState<string | null>(null);
  const [lastCompletedJobId, setLastCompletedJobId] = useState<string | null>(null);
  const [generationElapsedMs, setGenerationElapsedMs] = useState(0);
  const [jobId, setJobId] = useState<string | null>(null);
  const [_isLogConsoleOpen, setIsLogConsoleOpen] = useState(false);
  const [_loadingConfigs, setLoadingConfigs] = useState(false);

  const [selectedFile, setSelectedFile] = useState<GeneratedFile | null>(null);

  const [gitRepos, setGitRepos] = useState<any[]>([]);
  const [loadingGitRepos, setLoadingGitRepos] = useState(false);
  const [promptValue, setPromptValue] = useState('');

  const addLog = useCallback((newLog: Omit<LogEntry, 'timestamp'>) => {
    const timestamp = new Date().toISOString();
    setValidationLogs(prev => [...prev, { ...newLog, timestamp }]);
  }, []);

  // Use the reactive usePipelineWebSocket hook
  const {
    status: wsStatus,
    rawStatus: wsRawStatus,
    logs: wsLogs,
    connected: wsConnected,
    clarifyQuestions: wsClarifyQuestions,
    clarifyOptions: wsClarifyOptions,
    setClarifyQuestions: setWsClarifyQuestions,
    refinedSpec,
    generatedCode: wsGeneratedCode,
  } = usePipelineWebSocket(jobId);

  // Track phase history for DAG visualization
  const [phaseHistory, setPhaseHistory] = useState<Array<{phase: string; status: PhaseStatus; startedAt?: string; duration?: number}>>([]);
  // Maps WebSocket state strings to PipelinePhase enum values
  const wsToPipelinePhase: Record<string, PipelinePhase> = {
    'CLARIFY': 'clarify',
    'GENERATING': 'generate',
    'FORMATTING': 'format',
    'STATIC_ANALYSIS': 'static_analysis',
    'INITIALIZING': 'init',
    'VALIDATING': 'validate',
    'PLAN_REVIEW': 'plan_review',
    'PLANNING': 'plan',
    'APPLY_REVIEW': 'apply_review',
    'APPLYING': 'apply',
    'GIT_PUSH': 'complete',
    'CI_TRIGGER': 'complete',
    'CI_MONITOR': 'complete',
    'ESCALATE': 'escalate',
    'COMPLETED': 'complete',
    'FAILED': 'complete',
    'HUMAN_REVIEW': 'plan_review',
  };
  const [currentPhase, setCurrentPhase] = useState<PipelinePhase | null>(null);
  const [phaseStartTimes, setPhaseStartTimes] = useState<Record<string, number>>({});

  // Interrupt modal state
  const [interruptModalOpen, setInterruptModalOpen] = useState(false);
  const [loadingApproval, setLoadingApproval] = useState(false);

  // Clarification UI state
  const [clarifyQuestions, setClarifyQuestions] = useState<string[]>([]);
  const [, setClarifyAnswers] = useState<string[]>([]);
  const [submittingClarification, setSubmittingClarification] = useState(false);
  const [clarifyRound, setClarifyRound] = useState(0);

  // Sync WebSocket clarify questions into local state (real-time override)
  useEffect(() => {
    if (wsClarifyQuestions && wsClarifyQuestions.length > 0) {
      setClarifyQuestions(wsClarifyQuestions);
      // Reset answers when new questions arrive from WebSocket
      setClarifyAnswers(new Array(wsClarifyQuestions.length).fill(''));
      setClarifyRound((r) => r + 1);
    } else if (wsClarifyQuestions && wsClarifyQuestions.length === 0) {
      // Clear local state when clarification completes
      setClarifyQuestions([]);
    }
  }, [wsClarifyQuestions, setWsClarifyQuestions]);

  // Sync pipeline store for DAG / interrupt modal (shared with PipelineDetailView patterns)
  useEffect(() => {
    if (!jobId || wsStatus === 'pending') return;

    const state = wsStatus as string;

    const pipelinePhase = wsToPipelinePhase[state] || state.toLowerCase();

    // Track phase transitions for DAG nodes
    if (pipelinePhase !== currentPhase) {
      // Finalize previous phase if it was running
      if (currentPhase && phaseStartTimes[currentPhase]) {
        setPhaseHistory(prev => {
          const idx = prev.findIndex(p => p.phase === currentPhase && p.status === 'running');
          if (idx >= 0) {
            const updated = [...prev];
            const entry = { ...updated[idx], status: 'success' as PhaseStatus, duration: Date.now() - (phaseStartTimes[currentPhase] || Date.now()) };
            updated[idx] = entry;
            return updated;
          }
          return prev;
        });
      }
      // Start new phase
      setCurrentPhase(pipelinePhase as PipelinePhase);
      setPhaseStartTimes(prev => ({ ...prev, [pipelinePhase]: Date.now() }));
      setPhaseHistory(prev => {
        const exists = prev.find(p => p.phase === pipelinePhase);
        if (!exists) {
          return [...prev, { phase: pipelinePhase, status: 'running' as PhaseStatus, startedAt: new Date().toISOString() }];
        }
        return prev;
      });
    }

    // Complete phase on session_complete or session_failed
    if (state === 'completed' || state === 'failed') {
      if (currentPhase && phaseStartTimes[currentPhase]) {
        setPhaseHistory(prev => {
          const idx = prev.findIndex(p => p.phase === currentPhase && p.status === 'running');
          if (idx >= 0) {
            const updated = [...prev];
            updated[idx] = {
              ...updated[idx],
              status: state === 'failed' ? ('failed' as PhaseStatus) : ('success' as PhaseStatus),
              duration: Date.now() - (phaseStartTimes[currentPhase] || Date.now()),
            };
            return updated;
          }
          return prev;
        });
      }
    }

    // Clear on job done
    if ((state === 'completed' || state === 'failed') && jobId) {
      setTimeout(() => { setCurrentPhase(null); setPhaseStartTimes({}); }, 5000);
    }
  }, [wsStatus, jobId, currentPhase, phaseStartTimes, wsToPipelinePhase]);

  // Auto-trigger interrupt modal on human review or escalate
  useEffect(() => {
    // Check if this is a clarification question versus a final plan review
    const isClarification = wsClarifyQuestions && wsClarifyQuestions.length > 0;
    
    if (wsRawStatus === 'HUMAN_REVIEW') {
      if (!isClarification) {
        setInterruptModalOpen(true);
      }
    } else if (wsStatus === 'completed' && validationLogs.some(l => l.message.toLowerCase().includes('human review'))) {
      setInterruptModalOpen(true);
    }
  }, [wsStatus, wsRawStatus, validationLogs, wsClarifyQuestions]);

  // Log WebSocket connection state transitions
  useEffect(() => {
    if (!jobId) return;
    if (wsConnected) {
      addLog({ stage: 'generate', status: 'success', message: 'Real-time WebSocket event channel connected successfully.' });
    } else {
      addLog({ stage: 'generate', status: 'running', message: 'Waiting for WebSocket event channel to connect...' });
    }
  }, [wsConnected, jobId, addLog]);

  // Watchdog timeout to detect if pipeline is stuck without phase transitions
  useEffect(() => {
    if (!jobId) return;
    
    const timeoutId = setTimeout(async () => {
      // If we are still pending / haven't received any phase transition after 15s
      if (wsRawStatus === 'IDLE' || wsRawStatus === 'PENDING' || !wsRawStatus) {
        try {
          const status = await pollGenerationStatus(jobId);
          if (status.status === 'running') {
            addLog({ stage: 'generate', status: 'running', message: 'Generation job is queued in Celery worker — awaiting first event...' });
          } else if (status.status === 'failed') {
            addLog({ stage: 'generate', status: 'error', message: `Generation job failed: ${(status as any).message || 'Unknown error'}` });
          } else {
            addLog({
              stage: 'generate',
              status: 'running',
              message: 'Diagnostic: The generation job is queued, but no phase transition events have been received. Checking celery worker and redis status...'
            });
          }
        } catch (pollErr) {
          addLog({
            stage: 'generate',
            status: 'running',
            message: 'Diagnostic: The generation job is queued, but no phase transition events have been received. Polling failed — worker may not have consumed yet.'
          });
        }
      }
    }, 15000);
    
    return () => clearTimeout(timeoutId);
  }, [jobId, wsRawStatus, addLog]);

  // Fetch clarification questions when status transitions to CLARIFY or HUMAN_REVIEW
  useEffect(() => {
    if ((wsRawStatus !== 'CLARIFY' && wsRawStatus !== 'HUMAN_REVIEW') || !jobId) return;

    const fetchQuestions = async () => {
      try {
        const statusResponse = await pollGenerationStatus(jobId);
        // Look for clarification questions in logs or a dedicated field
        const clarifyLogs = statusResponse.logs.filter(
          (l) => l.stage === 'clarify' && l.message.includes('Question')
        );
        if (clarifyLogs.length > 0) {
          const questions = clarifyLogs.map((l) =>
            l.message.replace(/^Question\s*\d*[:\-]?\s*/i, '')
          );
          if (questions.length > 0) {
            setClarifyQuestions(questions);
            setClarifyAnswers(new Array(questions.length).fill(''));
            setClarifyRound((r) => r + 1);
            addLog({ stage: 'clarify', status: 'running', message: `Clarification needed: ${questions.length} question${questions.length > 1 ? 's' : ''} for you to answer.` });
            return;
          }
        }
        // Fallback: try to extract questions from any clarify-stage logs
        const allClarifyLogs = statusResponse.logs.filter((l) => l.stage === 'clarify');
        if (allClarifyLogs.length > 0) {
          const questions: string[] = [];
          for (const log of allClarifyLogs) {
            const match = log.message.match(/Question\s*\d*[:\-]?\s*(.+)$/i);
            if (match) questions.push(match[1].trim());
          }
          if (questions.length > 0) {
            setClarifyQuestions(questions);
            setClarifyAnswers(new Array(questions.length).fill(''));
            setClarifyRound((r) => r + 1);
            addLog({ stage: 'clarify', status: 'running', message: `Clarification needed: ${questions.length} question${questions.length > 1 ? 's' : ''} for you to answer.` });
            return;
          }
        }
      } catch (err) {
        console.error('Failed to fetch clarification questions:', err);
      }
    };

    fetchQuestions();
  }, [wsRawStatus, jobId, addLog]);

  // Handle clarification submission
  const handleClarifySubmit = async (message: string, selectedOptionValue?: string) => {
    if (!jobId || clarifyQuestions.length === 0) return;

    if (!message.trim() && !selectedOptionValue) {
      toast.error(`Please provide an answer before submitting.`);
      return;
    }

    setSubmittingClarification(true);
    try {
      const response = await submitClarifyAnswer(jobId, message.trim(), selectedOptionValue);

      if (response.status === 'questions') {
        const newQuestions = response.questions || (response.message ? [response.message] : []);
        if (newQuestions.length > 0) {
          // More questions — update the form (append to history happens inside ConversationalClarifyAgent)
          setClarifyQuestions(prev => [...prev, ...newQuestions]);
          // Note: we don't need to manually set options here as it will come from the WebSocket event,
          // but the backend API response might also include them. The WS will trigger a state update.
          addLog({ stage: 'clarify', status: 'running', message: `Round ${clarifyRound + 1}: Received AI response.` });
          toast(`Round ${clarifyRound + 1}: New question received.`);
        }

      } else if (response.status === 'review' || response.status === 'coding') {
        // Clarification complete — awaiting human review (or proceeding to generation)
        addLog({ stage: 'clarify', status: 'success', message: 'Clarification complete. Review the plan below and approve to proceed.' });
        toast.success('Clarification complete! Please review the infrastructure plan.');
        // Clear clarification state so the ConversationalClarifyAgent disappears
        // and the InlineReviewPanel can appear via the human_review_requested WS event.
        setClarifyQuestions([]);
        setClarifyAnswers([]);
      } else {
        addLog({ stage: 'clarify', status: 'error', message: 'Unexpected response from clarification service.' });
        toast.error('Unexpected response. Please try again.');
      }
    } catch (err: any) {
      console.error('Failed to submit clarification answer:', err);
      toast.error(`Clarification submission failed: ${err.message}`);
      addLog({ stage: 'clarify', status: 'error', message: `Clarification submission failed: ${err.message}` });
    } finally {
      setSubmittingClarification(false);
    }
  };

  // Handle clarification cancel (skip clarification, let job continue)
  const handleClarifyCancel = async () => {
    if (!jobId) return;
    try {
      await workflowService.approvePhase(jobId);
      addLog({ stage: 'clarify', status: 'success', message: 'Clarification skipped. Resuming generation...' });
      toast.success('Clarification skipped. Generation in progress...');
      setClarifyQuestions([]);
      setClarifyAnswers([]);
    } catch (err: any) {
      toast.error(`Failed to skip clarification: ${err.message}`);
    }
  };

  // Synchronize WebSocket logs and status to component state
  useEffect(() => {
    if (jobId && wsLogs.length > 0) {
      setValidationLogs(wsLogs);
    }
  }, [wsLogs, jobId]);

  useEffect(() => {
    if (jobId && wsStatus !== 'pending') {
      setGenerationStatus(wsStatus as any);
    }
  }, [wsStatus, jobId]);

  // Track elapsed time during active generation
  useEffect(() => {
    if (!jobId || generationStatus !== 'running') {
      setGenerationElapsedMs(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => {
      setGenerationElapsedMs(Date.now() - start);
    }, 500);
    return () => clearInterval(id);
  }, [jobId, generationStatus]);

  // Handle successful job completion and retrieve generated files
  useEffect(() => {
    if (!jobId || wsStatus !== 'completed') return;

    const fetchCompletedCode = async () => {
      // Use WebSocket-delivered code as primary source (already has file content)
      if (wsGeneratedCode && Array.isArray(wsGeneratedCode) && wsGeneratedCode.length > 0) {
        console.log('[GeneratorUI] Using code from WebSocket session_complete event:', wsGeneratedCode.length, 'files');
        setGeneratedCode(wsGeneratedCode);
        setGenerationStatus('completed');

        const readmeFile = wsGeneratedCode.find(file => file.name.toLowerCase().includes('readme.md'));
        setSelectedFile(readmeFile || wsGeneratedCode[0] || null);
        addLog({ stage: 'finalize', status: 'success', message: `✅ All files generated successfully (${wsGeneratedCode.length} files). Ready for deployment or download.` });
        setLastCompletedJobId(jobId);
        setJobId(null);
        return;
      }
      console.log('[GeneratorUI] WebSocket has no files, falling back to status endpoint polling...');

      // Fallback: poll the status endpoint for generated code with retries
      const maxRetries = 5;
      const delayMs = 1500;
      for (let attempt = 1; attempt <= maxRetries; attempt++) {
        try {
          addLog({ stage: 'finalize', status: 'running', message: `Fetching generated code files via status endpoint (attempt ${attempt}/${maxRetries})...` });
          const statusResponse = await pollGenerationStatus(jobId);
          if (statusResponse.code && statusResponse.code.length > 0) {
            console.log('[GeneratorUI] Received code from status endpoint:', statusResponse.code.length, 'files');
            setGeneratedCode(statusResponse.code);
            setGenerationStatus('completed');

            if (lastGenerationMetadata?.failoverFrom && lastGenerationMetadata?.failoverTo) {
              toast(
                `Model switched from ${lastGenerationMetadata.failoverFrom} → ${lastGenerationMetadata.failoverTo} due to primary model failure`,
                { duration: 6000, icon: '🔄', style: { background: '#f59e0b' } }
              );
            }

            const readmeFile = statusResponse.code.find(file => file.name.toLowerCase().includes('readme.md'));
            setSelectedFile(readmeFile || statusResponse.code[0] || null);
            addLog({ stage: 'finalize', status: 'success', message: `✅ All files generated successfully (${statusResponse.code.length} files). Ready for deployment or download.` });
            setLastCompletedJobId(jobId);
            setJobId(null);
            return;
          }
          console.warn(`[GeneratorUI] Attempt ${attempt} returned no code files. Job status: ${statusResponse.status}`);
        } catch (pollError: any) {
          console.error('[GeneratorUI] Attempt', attempt, 'failed:', pollError);
        }
        if (attempt < maxRetries) {
          await new Promise(resolve => setTimeout(resolve, delayMs));
        }
      }

      console.error('[GeneratorUI] Status endpoint returned no code files after all retries');
      setError("Generation completed but no code was returned.");
      setGenerationStatus('failed');
      setJobId(null);
    };

    fetchCompletedCode();
  }, [wsStatus, jobId, addLog, wsGeneratedCode, lastGenerationMetadata]);

  // Handle failed generation jobs
  useEffect(() => {
    if (!jobId || wsStatus !== 'failed') return;

    const handleFailedJob = async () => {
      try {
        const statusResponse = await pollGenerationStatus(jobId);
        const lastLog = statusResponse.logs[statusResponse.logs.length - 1];
        const errorMessage = lastLog?.message || 'Generation failed with an unknown error.';
        setError(errorMessage);
      } catch (pollError) {
        setError('Generation failed.');
      } finally {
        setGenerationStatus('failed');
        setJobId(null);
      }
    };

    handleFailedJob();
  }, [wsStatus, jobId]);

  // Fetch Git Repositories configurations for validation
  useEffect(() => {
    const fetchGitRepos = async () => {
      if (!currentProjectId) return;
      setLoadingGitRepos(true);
      try {
        const token = localStorage.getItem('iacgenie_token');
        const res = await fetch(`/api/git-repositories/${currentProjectId}`, {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        });
        if (res.ok) {
          const data = await res.json();
          const repos = data.repositories || data.result || [];
          setGitRepos(repos);
        }
      } catch (err) {
        console.error('Failed to load git repositories:', err);
      } finally {
        setLoadingGitRepos(false);
      }
    };
    fetchGitRepos();
  }, [currentProjectId]);

  const handleGenerate = useCallback(async (iterationPrompt?: string, baseJobId?: string) => {
    console.log("Generate Infrastructure button clicked. Starting generation process...");
    setGenerationStatus('running');
    setError(null);
    setGeneratedCode(null);
    setSelectedFile(null);
    setValidationLogs([]);
    setIsLogConsoleOpen(true);

    const activePrompt = iterationPrompt || prompt;
    const modelName = AVAILABLE_MODELS.find(m => m.id === model)?.name || 'AI model';
    addLog({ stage: 'generate', status: 'running', message: `Queueing generation job for ${modelName}...` });

    try {
      const projectId = currentProjectId || 'default-project';
      const selectedCfg = modelConfigs.find(cfg => (cfg.model_name || (cfg as any).model) === model);
      const modelConfigId = selectedCfg ? selectedCfg.id : undefined;
      const { job_id } = await startGeneration(activePrompt, model, provider, projectId, baseJobId, modelConfigId);
      setJobId(job_id);
      addLog({ stage: 'generate', status: 'success', message: `Job queued successfully with ID: ${job_id}` });
    } catch (err: any) {
      console.error("Failed to start generation job:", err);
      const errorMessage = err.message || 'An unexpected error occurred.';
      setError(errorMessage);
      setGenerationStatus('failed');
      addLog({ stage: 'error', status: 'error', message: errorMessage });
      setJobId(null);
    }
  }, [prompt, model, provider, currentProjectId, addLog]);

  const handleIterate = useCallback((iterationPrompt: string) => {
    const activeJobId = jobId || lastCompletedJobId;
    if (!activeJobId) {
      toast.error('No base job available to iterate upon.');
      return;
    }
    handleGenerate(iterationPrompt, activeJobId);
  }, [jobId, lastCompletedJobId, handleGenerate]);

  const handleDownloadZip = useCallback(async () => {
    const activeJobId = jobId || lastCompletedJobId;
    if (!activeJobId) {
      toast.error('No job active or completed for download.');
      return;
    }
    
    try {
      addLog({stage: 'finalize', status: 'running', message: 'Preparing ZIP file for download...'});
      
      await downloadProject(activeJobId);
      
      addLog({stage: 'finalize', status: 'success', message: 'Project ZIP file downloaded successfully.'});
      toast.success('Project ZIP downloaded successfully!');
    } catch (err: any) {
      addLog({stage: 'error', status: 'error', message: `Failed to download ZIP: ${err.message}`});
      toast.error(`Failed to download ZIP: ${err.message}`);
    }
  }, [jobId, lastCompletedJobId, addLog]);

  // Action: Approval Resumption (human review approve)
  const handleApproveResumption = async () => {
    if (!jobId) return;
    setLoadingApproval(true);
    try {
      await workflowService.approvePhase(jobId);
      toast.success('Generation approved. Resuming pipeline...');
      setInterruptModalOpen(false);
      // Reset the UI to show the generating progress state
      setGenerationStatus('running');
      setGeneratedCode(null);
      setSelectedFile(null);
      setError(null);
      // Reset phase tracking for the generation phase
      setPhaseHistory(prev => [
        ...prev.map(p => p.status === 'running' ? { ...p, status: 'success' as PhaseStatus } : p),
        { phase: 'generate', status: 'running' as PhaseStatus, startedAt: new Date().toISOString() },
      ]);
      setCurrentPhase('generate' as PipelinePhase);
      setPhaseStartTimes(prev => ({ ...prev, generate: Date.now() }));
      addLog({ stage: 'generate', status: 'running', message: 'Plan approved. Code generation starting...' });
    } catch (err: any) {
      toast.error('Approval failed: ' + (err.message || 'Server error'));
    } finally {
      setLoadingApproval(false);
    }
  };

  // Action: Abort Pipeline
  const handleAbortResumption = async () => {
    if (!jobId) return;
    try {
      await workflowService.abortSession(jobId);
      toast.success('Pipeline execution aborted.');
      setInterruptModalOpen(false);
      setGenerationStatus('failed');
      setJobId(null);
    } catch (err: any) {
      toast.error('Abort failed: ' + (err.message || 'Server error'));
    }
  };





  // Fetch model configs for the current project
  useEffect(() => {
    const fetchConfigs = async () => {
      if (!currentProjectId) return;
      
      setLoadingConfigs(true);
      try {
        const headers = getAuthHeaders();
        const res = await fetch(`/api/model-configs/${currentProjectId}`, {
          headers
        });
        if (res.ok) {
          const data = await res.json();
          const configs = data.configs || [];
          if (configs.length > 0) {
            const firstCfg = configs[0];
            const mName = firstCfg?.model_name || firstCfg?.model || firstCfg?.id || '';
            setGeneratorConfig({ model: mName });
            useAppStore.setState({ modelConfigs: configs });
          } else {
            // Pre-select Ollama Llama 3 (Local) as default since no config exists
            setGeneratorConfig({ model: 'ollama-llama3', provider: 'Ollama' as any });
            useAppStore.setState({ modelConfigs: [] });
          }
        } else {
          // Fallback: Pre-select Ollama Llama 3 (Local)
          setGeneratorConfig({ model: 'ollama-llama3', provider: 'Ollama' as any });
          useAppStore.setState({ modelConfigs: [] });
        }
      } catch (error) {
        console.log('No model configuration found for project, falling back to Ollama');
        setGeneratorConfig({ model: 'ollama-llama3', provider: 'Ollama' as any });
        useAppStore.setState({ modelConfigs: [] });
      }
      setLoadingConfigs(false);
    };
    fetchConfigs();
  }, [currentProjectId, setGeneratorConfig]);

  const isLoading = generationStatus === 'running';
  
  // Validate if the model selection is local or if we have a custom configuration
  const isLocalModel = model && model.startsWith('ollama-');
  const configuredModel = modelConfigs.length > 0 ? modelConfigs[0] : null;
  const canGenerate = !!configuredModel || isLocalModel;

  if (!currentProjectId) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Generator</h1>
          <p className="mt-1 text-gray-600">No project selected.</p>
        </div>
        <div className="p-6 border-brand-primary/20 bg-brand-primary/5 rounded-lg text-center">
          <h4 className="font-semibold text-brand-primary mb-2">No Project Selected</h4>
          <p className="text-sm text-brand-primary/80 mb-4">Please create a new project or select an existing one to use the generator.</p>
          <Button 
            variant="primary" 
            size="sm"
            onClick={() => useAppStore.getState().navigate('settings')}
          >
            Go to Project Settings
          </Button>
        </div>
      </div>
    );
  }

  const pipelinePhaseOrder: PipelinePhase[] = [
    'clarify', 'generate', 'format', 'static_analysis', 'init', 'validate',
    'plan_review', 'plan', 'apply_review', 'apply', 'escalate', 'complete',
  ];

  const railPhaseStates = React.useMemo(() => {
    const states: Record<string, RailPhaseState> = {};
    phaseHistory.forEach(p => {
      if (p.status === 'success' || p.status === ('completed' as any)) states[p.phase] = 'completed';
      else if (p.status === 'failed') states[p.phase] = 'failed';
      else if (p.status === 'running') states[p.phase] = 'active';
      else states[p.phase] = 'pending';
    });
    if (wsRawStatus === 'CLARIFY' || wsRawStatus === 'HUMAN_REVIEW') {
      if (currentPhase) states[currentPhase] = 'needs_input';
    }
    return states;
  }, [phaseHistory, wsRawStatus, currentPhase]);

  return (
    <div className="space-y-6 pb-32 relative">
      {/* Floating Live Update Connection Indicator */}
      {jobId && (
        <div className="absolute top-4 right-4 z-50 flex items-center space-x-2 bg-white/90 backdrop-blur px-3.5 py-2 rounded-full border border-gray-200/80 shadow-md transition-all duration-300 animate-fadeIn hover:shadow-lg">
          <span className="relative flex h-2.5 w-2.5">
            {wsConnected ? (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                {/* Latency ring — grows with elapsed time */}
                <svg
                  className="absolute -inset-[2px] w-[calc(100%+8px)] h-[calc(100%+8px)]"
                  viewBox="0 0 24 24"
                >
                  <circle
                    cx="12" cy="12" r="10"
                    fill="none"
                    stroke={generationElapsedMs > 15000 ? '#f59e0b' : '#10b981'}
                    strokeWidth="1.5"
                    strokeDasharray={`${Math.min((generationElapsedMs % 30000) / 300, 62.83)} 62.83`}
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-500"></span>
              </>
            ) : (
              <>
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber-400 opacity-75"></span>
                <svg
                  className="absolute -inset-[2px] w-[calc(100%+8px)] h-[calc(100%+8px)]"
                  viewBox="0 0 24 24"
                >
                  <circle
                    cx="12" cy="12" r="10"
                    fill="none"
                    stroke="#f59e0b"
                    strokeWidth="1.5"
                    strokeDasharray={`${Math.min((generationElapsedMs % 30000) / 300, 62.83)} 62.83`}
                    className="transition-all duration-500"
                  />
                </svg>
                <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber-500"></span>
              </>
            )}
          </span>
          <span className="text-[10px] font-extrabold text-gray-700 tracking-wider uppercase">
            {wsConnected ? 'Live Updates' : 'Reconnecting...'}
          </span>
          <span className="text-[10px] font-mono text-gray-500 tabular-nums">
            {Math.floor(generationElapsedMs / 60000)}:{String(Math.floor((generationElapsedMs % 60000) / 1000)).padStart(2, '0')}
          </span>
        </div>
      )}

       <div className="text-center mt-8 mb-6">
        <h1 className="text-4xl font-bold text-gray-900 tracking-tight">Design your infrastructure</h1>
        <p className="mt-2 text-lg text-gray-600">Start with a detailed prompt to generate reliable IaC instantly.</p>
      </div>

      {/* Git Repository Configuration Alert Banner */}
      {!loadingGitRepos && gitRepos.length === 0 && (
        <Card className="max-w-4xl mx-auto p-6 border-blue-200 bg-blue-50/50 hover:bg-blue-50/70 transition-all duration-300 rounded-2xl shadow-sm border animate-fadeIn">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-start space-x-3">
              <div className="flex-shrink-0 mt-0.5">
                <div className="w-10 h-10 bg-gradient-to-r from-blue-500 to-indigo-600 rounded-xl flex items-center justify-center text-white shadow-md shadow-blue-500/20 text-lg">
                  🐱
                </div>
              </div>
              <div>
                <h4 className="font-bold text-blue-900">Git Repository Integration Recommended</h4>
                <p className="text-sm text-blue-700 mt-0.5 leading-relaxed">
                  No active Git repository is configured for this project. Connect your GitHub repository to enable automated versioning, peer reviews, and secure code sync.
                </p>
              </div>
            </div>
            <Button 
              variant="primary" 
              size="sm"
              onClick={() => {
                window.location.hash = 'git';
                useAppStore.getState().navigate('settings');
              }}
              className="bg-indigo-600 hover:bg-indigo-700 text-white font-semibold shadow-md shrink-0 self-end sm:self-center"
            >
              Configure Git Integration
            </Button>
          </div>
        </Card>
      )}

      {/* Model Configuration Status Warning - Bypassed for local Ollama development */}
      {!canGenerate && (
        <Card className="max-w-4xl mx-auto p-6 border-brand-primary/20 bg-brand-primary/5 animate-fadeIn rounded-2xl">
          <div className="flex items-center space-x-3">
            <div className="flex-shrink-0">
              <div className="w-10 h-10 bg-brand-primary rounded-xl flex items-center justify-center text-white shadow-md shadow-brand-primary/20 text-lg">
                ⚠️
              </div>
            </div>
            <div className="flex-1">
              <h4 className="font-bold text-brand-primary">Model Configuration Required</h4>
              <p className="text-sm text-brand-primary/80 mt-0.5">You need to configure an AI model in Project Settings, or select a local Ollama model to generate infrastructure.</p>
            </div>
            <Button 
              variant="secondary" 
              size="sm"
              onClick={() => {
                window.location.hash = 'model-config';
                useAppStore.getState().navigate('settings');
              }}
              className="border-brand-primary/30 hover:bg-brand-primary/10 text-brand-primary font-semibold"
            >
              Configure Model
            </Button>
          </div>
        </Card>
      )}

      {generationStatus === 'pending' || generationStatus === 'failed' ? (
        <PromptCanvas
          prompt={prompt}
          setPrompt={setPrompt}
          model={model}
          setModel={(val) => {
            const selectedCfg = modelConfigs.find(cfg => (cfg.model_name || (cfg as any).model) === val);
            if (selectedCfg) {
              setGeneratorConfig({ model: val, provider: selectedCfg.provider as any });
            } else if (val === 'ollama-llama3' || val === 'ollama-mixtral') {
              setGeneratorConfig({ model: val, provider: 'Ollama' as any });
            } else {
              setGeneratorConfig({ model: val });
            }
          }}
          provider={provider}
          setProvider={(val) => setGeneratorConfig({ provider: val as CloudProvider })}
          onSubmit={() => {
            if (!canGenerate) {
              toast.error('Please configure a model in Project Settings or select a local Ollama model before generating.');
              return;
            }
            handleGenerate();
          }}
          isLoading={isLoading}
          modelOptions={[
            ...modelConfigs.map(cfg => {
              const mName = cfg.model_name || (cfg as any).model;
              return { value: mName, label: `${mName} (${cfg.provider})` };
            }),
            { value: 'ollama-llama3', label: 'Ollama Llama 3 (Local)' },
            { value: 'ollama-mixtral', label: 'Ollama Mixtral (Local)' }
          ]}
          providerOptions={[
            { value: CloudProvider.AWS, label: 'AWS' },
            { value: CloudProvider.GCP, label: 'Google Cloud' },
            { value: CloudProvider.AZURE, label: 'Azure' }
          ]}
        />
      ) : (
        <div className="flex justify-center mb-8">
          <PromptCanvas
            prompt={prompt}
            setPrompt={setPrompt}
            model={model}
            setModel={() => {}}
            provider={provider}
            setProvider={() => {}}
            onSubmit={() => {}}
            isLoading={isLoading}
            modelOptions={[]}
            providerOptions={[]}
            isCompact={true}
          />
        </div>
      )}

      {/* AnimatePresence Block for PipelineRail */}
      <AnimatePresence>
        {(isLoading || generationStatus === 'failed' || generationStatus === 'completed') && phaseHistory.length > 0 && (
          <motion.div
            layout
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="w-full max-w-6xl mx-auto"
          >
            <PipelineRail
              phases={pipelinePhaseOrder}
              currentPhase={currentPhase}
              phaseStates={railPhaseStates}
            />
          </motion.div>
        )}
      </AnimatePresence>

      <div className="w-full max-w-6xl mx-auto flex flex-col space-y-6 relative">
        <AnimatePresence>
          {/* Clarification UI */}
          {(wsRawStatus === 'CLARIFY' || (wsRawStatus === 'HUMAN_REVIEW' && clarifyQuestions.length > 0)) && clarifyQuestions.length > 0 && (
            <ConversationalClarifyAgent
              key="clarify"
              questions={clarifyQuestions}
              options={wsClarifyOptions}
              onSubmit={handleClarifySubmit}
              onCancel={handleClarifyCancel}
              isLoading={submittingClarification}
            />
          )}

          {/* Human Review UI */}
          {wsRawStatus === 'HUMAN_REVIEW' && clarifyQuestions.length === 0 && interruptModalOpen && (
            <InlineReviewPanel
              key="review"
              onApprove={handleApproveResumption}
              onAbort={handleAbortResumption}
              isLoading={loadingApproval}
              refinedSpec={refinedSpec}
            />
          )}
        </AnimatePresence>

        <AnimatePresence>
          {/* Monaco Editor Workspace */}
          {((isLoading && currentPhase !== 'clarify') || generationStatus === 'failed' || generationStatus === 'completed') && (
            <motion.div
              layout
              key="workspace"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="h-[65vh] w-full overflow-hidden rounded-2xl border border-slate-200 dark:border-slate-800 shadow-xl bg-slate-50 dark:bg-[#0d1117] flex flex-col"
            >
              {generatedCode && generatedCode.length > 0 ? (
                <MonacoWorkspacePanel
                  files={generatedCode}
                  selectedFile={selectedFile}
                  onFileSelect={setSelectedFile}
                  workspaceId={jobId || lastCompletedJobId || undefined}
                  onAddLog={addLog}
                  onFixWithAi={(_, errorLog) => {
                    setPromptValue(`Fix the OpenTofu validation error in ${selectedFile?.name || 'active file'}: \n\n${errorLog}`);
                  }}
                  gitRepos={gitRepos}
                />
              ) : (generationStatus === 'failed' || (generationStatus === 'completed' && (!generatedCode || generatedCode.length === 0))) ? (
                <div className="flex-1 flex flex-col items-center justify-center text-slate-400 p-8 text-center">
                  <div className="w-16 h-16 bg-red-500/10 text-red-500 rounded-full flex items-center justify-center mb-4">
                    <svg className="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                    </svg>
                  </div>
                  <p className="text-lg font-medium text-slate-800 dark:text-slate-200">Generation Failed</p>
                  <p className="text-sm mt-2 max-w-md text-slate-500">The AI model failed to generate valid code or encountered an error. Please check the reasoning stream below for details and try iterating.</p>
                </div>
              ) : (
                <div className="flex-1 flex flex-col items-center justify-center p-8 bg-slate-50 dark:bg-[#0d1117] relative overflow-hidden">
                  <div className="absolute inset-0 pointer-events-none bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-5 dark:opacity-10 mix-blend-overlay"></div>
                  
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ duration: 0.5 }}
                    className="w-full max-w-xl z-10 flex flex-col items-center"
                  >
                    <div className="relative mb-8">
                      <div className="w-20 h-20 bg-blue-500/10 rounded-2xl flex items-center justify-center mb-2 animate-pulse shadow-[0_0_30px_rgba(59,130,246,0.3)]">
                        <svg className="w-10 h-10 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                        </svg>
                      </div>
                      <div className="absolute -bottom-1 -right-1 w-6 h-6 bg-brand-primary rounded-full flex items-center justify-center border-2 border-white dark:border-[#0d1117]">
                        <div className="w-3 h-3 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                      </div>
                    </div>
                    
                    <h3 className="text-2xl font-bold text-slate-800 dark:text-white mb-3 text-center tracking-tight">
                      Generating Infrastructure Code
                    </h3>
                    
                    <p className="text-slate-500 dark:text-slate-400 text-center mb-8 max-w-md">
                      Our AI agents are analyzing your requirements and synthesizing industry-standard Terraform modules. This typically takes 30-60 seconds.
                    </p>
                    
                    <div className="w-full relative">
                      <div className="flex justify-between text-xs font-medium text-slate-500 dark:text-slate-400 mb-2 px-1">
                        <span>Initialization</span>
                        <span className="text-blue-500 font-semibold animate-pulse">Synthesis</span>
                        <span>Validation</span>
                      </div>
                      <div className="h-3 w-full bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden shadow-inner relative">
                        <motion.div
                          className="absolute top-0 bottom-0 left-0 bg-gradient-to-r from-blue-600 via-brand-primary to-purple-500"
                          initial={{ width: '0%' }}
                          animate={{ width: '85%' }}
                          transition={{ duration: 45, ease: "easeOut" }}
                        >
                          <div className="absolute inset-0 bg-white/20 w-full" style={{ backgroundImage: 'linear-gradient(45deg,rgba(255,255,255,.15) 25%,transparent 25%,transparent 50%,rgba(255,255,255,.15) 50%,rgba(255,255,255,.15) 75%,transparent 75%,transparent)', backgroundSize: '1rem 1rem', animation: 'progress-stripes 1s linear infinite' }}></div>
                        </motion.div>
                      </div>
                    </div>
                  </motion.div>
                </div>
              )}
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {/* AI Chat Prompt Bar */}
          {((isLoading && currentPhase !== 'clarify') || generationStatus === 'failed' || generationStatus === 'completed') && generatedCode && generatedCode.length > 0 && (
            <motion.div
              layout
              key="ai-prompt-bar"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full"
            >
              <AiChatPromptBar
                value={promptValue}
                onChange={setPromptValue}
                onSubmit={(prompt) => {
                  handleIterate(prompt);
                  setPromptValue('');
                }}
                isDisabled={generationStatus === 'running' || isLoading}
                isLoading={isLoading}
              />
            </motion.div>
          )}

          {/* Unified Agent Log */}
          {((isLoading && currentPhase !== 'clarify') || generationStatus === 'failed' || generationStatus === 'completed') && (
            <motion.div
              layout
              key="agent-log"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full"
            >
              <UnifiedAgentLog
                logs={validationLogs.map((log) => ({
                  timestamp: log.timestamp || new Date().toISOString(),
                  stage: log.stage,
                  status: log.status,
                  message: log.message,
                }))}
                isExpanded={!(generatedCode && generatedCode.length > 0) || generationStatus === 'failed'}
              />
            </motion.div>
          )}

          {/* Success banner + metadata */}
          {generationStatus === 'completed' && generatedCode && (
            <motion.div
              layout
              key="success-banner"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="w-full"
            >
              <div className="mt-6 flex items-center justify-between p-4 bg-gradient-to-r from-emerald-500/10 to-teal-500/10 border border-emerald-500/20 rounded-2xl">
                <div className="flex items-center gap-4">
                  <div className="w-10 h-10 bg-emerald-500 text-white rounded-full flex items-center justify-center shadow-lg shadow-emerald-500/30">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  </div>
                  <div>
                    <h3 className="text-base font-bold text-slate-900 dark:text-white">Generation Complete</h3>
                    <p className="text-sm text-slate-600 dark:text-slate-400">
                      {generatedCode.length} file{generatedCode.length !== 1 ? 's' : ''} generated • {provider} • {lastGenerationMetadata?.modelUsed || model}
                      {lastGenerationMetadata?.totalTokens !== undefined && lastGenerationMetadata.totalTokens > 0 && (
                        <span> • {lastGenerationMetadata.totalTokens.toLocaleString()} tokens</span>
                      )}
                      {lastGenerationMetadata?.latencyMs !== undefined && lastGenerationMetadata.latencyMs > 0 && (
                        <span> • {(lastGenerationMetadata.latencyMs / 1000).toFixed(1)}s</span>
                      )}
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button variant="secondary" size="sm" onClick={handleDownloadZip}>
                    Download ZIP
                  </Button>
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => useAppStore.getState().navigate('deployments')}
                    className="bg-emerald-600 hover:bg-emerald-700 text-white border-none"
                  >
                    Deploy Now
                  </Button>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
};

export default GeneratorUI;