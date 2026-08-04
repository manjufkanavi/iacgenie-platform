import { useEffect, useRef, useCallback, useState } from 'react';
import { usePipelineStore } from './store/usePipelineStore';
import { workflowService } from '../services/workflowService';
import type { PipelinePhase, ValidationStepLog, LogLevel } from './types';

export type PipelineState = 'IDLE' | 'PENDING' | 'PLANNING' | 'GENERATING' | 'VALIDATING' | 'APPLYING' | 'COMPLETED' | 'FAILED' | 'HUMAN_REVIEW' | 'CLARIFY';


interface WebSocketEvent {
  type: string;
  session_id: string;
  data: Record<string, unknown>;
  timestamp: string;
}

// removed HumanReviewEvent

export interface UsePipelineWebSocketReturn {
  status: string;
  pipelineState: PipelineState;
  rawStatus: string;  // The raw backend status string (e.g. 'CLARIFY', 'ESCALATE')
  logs: ValidationStepLog[];
  setLogs: React.Dispatch<React.SetStateAction<ValidationStepLog[]>>;
  connected: boolean;
  isHumanReview: boolean;
  humanReviewReason: string | null;
  clarifyQuestions: string[];
  setClarifyQuestions: React.Dispatch<React.SetStateAction<string[]>>;
  clarifyOptions: any[];
  setClarifyOptions: React.Dispatch<React.SetStateAction<any[]>>;
  refinedSpec: string | null;
  setRefinedSpec: React.Dispatch<React.SetStateAction<string | null>>;
  subscribe: (phase: PipelinePhase) => void;
  unsubscribe: (phase: PipelinePhase) => void;
  generatedCode: any;
  error: string | null;
}

export function usePipelineWebSocket(pipelineId: string | null): UsePipelineWebSocketReturn {
  const wsRef = useRef<WebSocket | null>(null);
  const storeLogs = usePipelineStore((s) => s.pipelineLogs);
  const [logs, setLogs] = useState<ValidationStepLog[]>([]);
  
  useEffect(() => {
    if (storeLogs) {
      setLogs(storeLogs.map(log => ({
        stage: log.phase,
        status: log.level === 'error' ? 'error' : log.level === 'warning' ? 'retrying' : 'success',
        message: log.message,
        timestamp: log.timestamp
      } as ValidationStepLog)));
    } else {
      setLogs([]);
    }
  }, [storeLogs]);

  const [connected, setConnected] = useState(false);
  const [isHumanReview, setIsHumanReview] = useState(false);
  const [humanReviewReason, setHumanReviewReason] = useState<string | null>(null);
  const [pipelineStatus, setPipelineStatus] = useState<string>('pending');
  const [pipelineState, setPipelineState] = useState<PipelineState>('IDLE');
  const [generatedCode, setGeneratedCode] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [clarifyQuestions, setClarifyQuestions] = useState<string[]>([]);
  const [clarifyOptions, setClarifyOptions] = useState<any[]>([]);
  const [refinedSpec, setRefinedSpec] = useState<string | null>(null);
  const lastEventTimeRef = useRef(Date.now());
  const reconciliationTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const transitionPhase = usePipelineStore((s) => s.transitionPhase);
  const addLogEntry = usePipelineStore((s) => s.addLogEntry);
  const setConnectionState = usePipelineStore((s) => s.setConnectionState);
  const updateLatency = usePipelineStore((s) => s.updateLatency);
  const incrementEventsReceived = usePipelineStore((s) => s.incrementEventsReceived);
  const incrementReconnects = usePipelineStore((s) => s.incrementReconnects);
  const clearConnectionMetrics = usePipelineStore((s) => s.clearConnectionMetrics);

  const token = localStorage.getItem('iacgenie_token');

  const reconnectAttemptsRef = useRef(0);
  const maxReconnectAttempts = 5;
  const pingIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPingTimeRef = useRef<number | null>(null);
  const isReconnectingRef = useRef(false);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const syncMissedLogs = useCallback(async (_sessionId: string) => {
    try {
      // Logs are now streamed via WebSocket events; no separate logs endpoint exists
      // Fetch current state for any status-based reconciliation
      const logs = await workflowService.getSessionLogs(_sessionId);
      console.log(`[WS] Synced missed logs:`, logs);
    } catch (err) {
      console.error('[WS] Failed to sync state:', err);
    }
  }, []);

  const handleEvent = useCallback((event: WebSocketEvent) => {
    incrementEventsReceived();
    lastEventTimeRef.current = Date.now();
    // Clear any pending reconciliation since we just received an event
    if (reconciliationTimerRef.current) {
      clearTimeout(reconciliationTimerRef.current);
      reconciliationTimerRef.current = null;
    }
    const { type, data } = event;

    // Latency ping response
    if (type === 'pong') {
      if (lastPingTimeRef.current !== null) {
        updateLatency(Math.round(performance.now() - lastPingTimeRef.current));
        lastPingTimeRef.current = null;
      }
      return;
    }

    // Phase transition
    if (type === 'phase_transition') {
      const rawToState = data.to_state as string;
      if (rawToState) {
        const toState = rawToState.toUpperCase();
        setPipelineState(toState as PipelineState);
        if (toState === 'COMPLETED') {
          setTimeout(() => {
            setPipelineStatus((currentStatus) => {
              if (currentStatus !== 'completed' && currentStatus !== 'failed') {
                console.log('[WS] Timeout waiting for session_complete, forcing completed status to trigger polling fallback.');
                return 'completed';
              }
              return currentStatus;
            });
          }, 2000);
        } else if (toState === 'FAILED') {
          setTimeout(() => {
            setPipelineStatus((currentStatus) => {
              if (currentStatus !== 'completed' && currentStatus !== 'failed') {
                console.log('[WS] Timeout waiting for session_failed, forcing failed status.');
                return 'failed';
              }
              return currentStatus;
            });
          }, 2000);
        } else {
          setPipelineStatus('running');
        }
        
        const phaseMap: Record<string, string> = {
          CLARIFY: 'clarify',
          GENERATING: 'generate',
          FORMATTING: 'format',
          STATIC_ANALYSIS: 'static_analysis',
          INITIALIZING: 'init',
          VALIDATING: 'validate',
          PLAN_REVIEW: 'plan_review',
          PLANNING: 'plan',
          APPLY_REVIEW: 'apply_review',
          APPLYING: 'apply',
          GIT_PUSH: 'complete',
          CI_TRIGGER: 'complete',
          CI_MONITOR: 'complete',
          ESCALATE: 'escalate',
          COMPLETED: 'complete',
          FAILED: 'complete',
          HUMAN_REVIEW: 'plan_review',
        };
        const phase = (phaseMap[toState] || 'generate') as PipelinePhase;
        const phaseStatus =
          toState === 'COMPLETED' ? 'success' :
          toState === 'FAILED' ? 'failed' :
          toState === 'ESCALATE' ? 'escalated' :
          'running';
        transitionPhase(phase, phaseStatus as any);
      }
      return;
    }

    // Agent start
    if (type === 'agent_start') {
      const agentName = data.agent as string;
      if (agentName) {
        addLogEntry({
          phase: 'generate',
          message: `Agent "${agentName}" started`,
          level: 'info',
        });
      }
      return;
    }

    // Agent complete
    if (type === 'agent_complete') {
      const agentName = data.agent as string;
      const success = data.success as boolean;
      if (agentName) {
        addLogEntry({
          phase: 'generate',
          message: `Agent "${agentName}" ${success ? 'completed' : 'failed'}`,
          level: success ? 'info' : 'error',
        });
      }
      return;
    }

    // Agent error
    if (type === 'agent_error') {
      const agentName = data.agent as string;
      const error = data.error as string;
      addLogEntry({
        phase: 'generate',
        message: `Agent "${agentName}" error: ${error}`,
        level: 'error',
      });
      return;
    }

    // Session complete
    if (type === 'session_complete') {
      const status = data.status as string;
      if (status === 'success' || !status) {
        addLogEntry({
          phase: 'complete',
          message: 'Pipeline completed successfully',
          level: 'info',
        });
        setPipelineStatus('completed');
        setPipelineState('COMPLETED');
        if (data.files) {
          console.log('[WS] session_complete: received', (data.files as any[]).length, 'files via WebSocket', data.files);
          setGeneratedCode(data.files as any);
        } else {
          console.log('[WS] session_complete: no files in event payload');
        }
      }
      return;
    }

    // Session failed
    if (type === 'session_failed') {
      const errorStr = data.error as string;
      addLogEntry({
        phase: 'complete',
        message: errorStr || 'Pipeline failed',
        level: 'error',
      });
      setError(errorStr || 'Pipeline failed');
      setPipelineStatus('failed');
      setPipelineState('FAILED');
      return;
    }

    // Human review requested
    if (type === 'human_review_requested') {
      const reason = data.reason as string;
      const spec = data.refined_spec as string;
      setIsHumanReview(true);
      setHumanReviewReason(reason || 'Human review required');
      if (spec) setRefinedSpec(spec);
      addLogEntry({
        phase: 'plan_review',
        message: `Human review requested: ${reason}`,
        level: 'warning',
      });
      setPipelineStatus('human_review');
      return;
    }

    // Clarify question (real-time questions from backend)
    if (type === 'clarify_question') {
      const questions = data.questions as string[];
      const options = (data.options as any[]) || [];
      
      if (questions && questions.length > 0) {
        setClarifyQuestions(questions);
        setClarifyOptions(options);
        addLogEntry({
          phase: 'clarify',
          message: `Clarification requested: ${questions[0]}`,
          level: 'info',
        });
      } else {
        setClarifyQuestions([]);
        setClarifyOptions([]);
        addLogEntry({
          phase: 'clarify',
          message: 'Clarification questions cleared.',
          level: 'info',
        });
      }
      return;
    }

    // Clarify answer submitted by user
    if (type === 'clarify_answer') {
      addLogEntry({
        phase: 'clarify',
        message: 'Clarification answer received. Re-analyzing...',
        level: 'info',
      });
      return;
    }

    // Clarify complete (proceeding to generation)
    if (type === 'clarify_complete') {
      const hasSpec = data.has_refined_spec as boolean;
      if (hasSpec) {
        addLogEntry({
          phase: 'clarify',
          message: 'Clarification complete. Refinement spec generated. Proceeding to generation.',
          level: 'info',
        });
      }
      setClarifyQuestions([]);
      return;
    }

    // Heartbeat
    if (type === 'heartbeat') {
      return;
    }

    // Session info (from session alive check)
    if (type === 'session_info') {
      const active = data.active as boolean;
      const status = data.status as string;
      if (!active) {
        addLogEntry({
          phase: 'generate',
          message: status ? `Session is not actively running (status: ${status})` : 'Session is not actively running',
          level: 'info',
        });
        if (status === 'completed') {
          setPipelineStatus('completed');
          setPipelineState('COMPLETED');
          transitionPhase('complete', 'success');
        } else if (status === 'failed') {
          setPipelineStatus('failed');
          setPipelineState('FAILED');
          transitionPhase('complete', 'failed');
          setError(data.message as string || 'Session is not running');
        }
      }
      return;
    }

    // Legacy event types for backward compatibility
    if (type === 'log_entry') {
      addLogEntry({
        phase: (data.phase as PipelinePhase) || 'generate',
        message: (data.message as string) || '',
        level: (data.level as LogLevel) || 'info',
      });
      return;
    }

    if (type === 'progress_update') {
      const progress = data.progress as number;
      const phase = data.phase as PipelinePhase;
      if (phase && typeof progress === 'number') {
        usePipelineStore.getState().updatePhaseProgress(phase, progress);
      }
      return;
    }

    if (type === 'error') {
      setError((data.message as string) || 'Pipeline error');
      return;
    }
  }, [incrementEventsReceived, addLogEntry, transitionPhase, updateLatency, setError, setPipelineStatus]);

  const connect = useCallback((sessionId: string) => {
    if (!sessionId || !token) return;

    const base = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
    const wsProtocol = base.startsWith('https') ? 'wss' : 'ws';
    const host = base.replace(/^https?:\/\//, '');
    const wsUrl = `${wsProtocol}://${host}/api/workflow/${sessionId}/ws?token=${token}`;

    console.log(`[WS] Connecting to ${wsUrl}`);

    if (isReconnectingRef.current) {
      setConnectionState('reconnecting');
    } else {
      setConnectionState('connecting');
    }

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('[WS] Connected');
      setConnected(true);
      setConnectionState('connected');
      isReconnectingRef.current = false;
      reconnectAttemptsRef.current = 0;
      syncMissedLogs(sessionId);

      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
          lastPingTimeRef.current = performance.now();
          ws.send(JSON.stringify({ command: 'ping' }));
        }
      }, 10000);
    };

    ws.onclose = (event: CloseEvent) => {
      console.log(`[WS] Disconnected (code: ${event.code})`);
      setConnected(false);
      setPipelineStatus('pending');
      setIsHumanReview(false);
      setHumanReviewReason(null);

      if (pingIntervalRef.current) {
        clearInterval(pingIntervalRef.current);
        pingIntervalRef.current = null;
      }

      if (event.wasClean) {
        setConnectionState('disconnected');
        isReconnectingRef.current = false;
        reconnectAttemptsRef.current = 0;
        // Reconcile with DB if no events received recently
        if (pipelineId) {
          const elapsed = Date.now() - lastEventTimeRef.current;
          if (elapsed > 30000) {
            reconciliationTimerRef.current = setTimeout(async () => {
              try {
                const job = await workflowService.getGenerationJob(pipelineId);
                const status = (job as any)?.data?.status || (job as any)?.status || 'unknown';
                setPipelineStatus(status === 'completed' ? 'completed' : status === 'failed' ? 'failed' : 'pending');
                if (status === 'failed') setError('Disconnected — job may have failed');
              } catch (pollErr) {
                console.error('[WS] Reconciliation poll failed:', pollErr);
              }
            }, 5000);
          }
        }
      } else if (reconnectAttemptsRef.current < maxReconnectAttempts) {
        isReconnectingRef.current = true;
        incrementReconnects();
        setConnectionState('reconnecting');

        const backoffDelay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 30000);
        console.log(`[WS] Reconnecting in ${backoffDelay}ms (${reconnectAttemptsRef.current + 1}/${maxReconnectAttempts})`);

        reconnectAttemptsRef.current++;
        reconnectTimerRef.current = setTimeout(() => {
          connect(sessionId);
        }, backoffDelay);
      } else {
        console.error('[WS] Reconnection exhausted');
        setConnectionState('error', 'Reconnection failed after 5 attempts');
        isReconnectingRef.current = false;
      }
    };

    ws.onerror = () => {
      console.error('[WS] Connection error');
      setConnected(false);
      setConnectionState('error', 'WebSocket error');
    };

    ws.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent(data as WebSocketEvent);
      } catch (err) {
        console.error('[WS] Failed to parse message:', err);
      }
    };
  }, [token, syncMissedLogs, setConnectionState, updateLatency, incrementEventsReceived, incrementReconnects, handleEvent]);

  useEffect(() => {
    if (pipelineId) {
      clearConnectionMetrics();
      setPipelineStatus('pending');
      reconnectAttemptsRef.current = 0;
      isReconnectingRef.current = false;
      connect(pipelineId);
    } else {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Normal Closure');
        wsRef.current = null;
      }
      setConnected(false);
      setPipelineStatus('pending');
      setIsHumanReview(false);
      setHumanReviewReason(null);
      setConnectionState('disconnected');
    }

    return () => {
      if (wsRef.current) {
        wsRef.current.close(1000, 'Cleanup Hook');
      }
      if (pingIntervalRef.current) clearInterval(pingIntervalRef.current);
      if (reconnectTimerRef.current) clearTimeout(reconnectTimerRef.current);
      if (reconciliationTimerRef.current) clearTimeout(reconciliationTimerRef.current);
    };
  }, [pipelineId, connect, clearConnectionMetrics, setConnectionState]);

  const subscribeToPhase = useCallback((phase: PipelinePhase) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'subscribe', phase }));
    }
  }, []);

  const unsubscribeFromPhase = useCallback((phase: PipelinePhase) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ command: 'unsubscribe', phase }));
    }
  }, []);

  return {
    status: pipelineStatus,
    pipelineState,
    rawStatus: pipelineState,
    logs,
    setLogs,
    connected,
    isHumanReview,
    humanReviewReason,
    clarifyQuestions,
    setClarifyQuestions,
    clarifyOptions,
    setClarifyOptions,
    refinedSpec,
    setRefinedSpec,
    subscribe: subscribeToPhase,
    unsubscribe: unsubscribeFromPhase,
    generatedCode,
    error,
  };
}
