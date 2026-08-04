export type AIModelProvider = 'Google' | 'OpenAI' | 'Anthropic' | 'Mistral' | 'Meta' | 'Cohere' | 'OpenRouter' | 'Ollama';

export interface AIModelInfo {
  id: string;
  name: string;
  provider: AIModelProvider;
  icon: React.ReactNode;
  description: string;
  defaultModel: string;
  defaultBaseUrl: string;
}

export enum CloudProvider {
  AWS = 'aws',
  GCP = 'gcp',
  AZURE = 'azure',
}

export enum OutputType {
  OPENTOFU = 'opentofu',
  DOCKER = 'docker',
  KUBERNETES = 'kubernetes',
}

export interface GeneratedFile {
  name: string;
  language: string;
  content: string;
}

export type GeneratedCode = GeneratedFile[];

// Types for the async generation flow
export type GenerationStatus = 'pending' | 'running' | 'completed' | 'failed';

export interface ValidationStepLog {
  stage: string;
  status: 'running' | 'success' | 'error' | 'retrying';
  message: string;
  timestamp: string;
}

export interface GenerationStartResponse {
    job_id: string;
    session_id?: string;
}

export interface GenerationStatusResponse {
    job_id: string;
    status: GenerationStatus;
    logs: ValidationStepLog[];
    code: GeneratedCode | null;
}

// Expanded View type for all pages
export type View =
  | 'landing' | 'signin' | 'signup' | 'forgot-password' | 'reset-password'
  | 'dashboard' | 'generator' | 'deployments' | 'settings'
  | 'developer' | 'billing' | 'audit-log'
  | 'docs' | 'api-docs' | 'about' | 'privacy' | 'terms' | 'contact' | 'aup'
  | 'human-review' | 'usage-analytics'
  | 'team-members'
  // Pipeline agentic loop views
  | 'pipeline-dashboard' | 'pipeline-detail' | 'clarify-agent' | 'generator-agent'
  | 'static-analysis' | 'plan-review' | 'apply-review' | 'escalation-handler'
  | 'session-manager' | 'workspace-manager' | 'agent-configuration';

// Pipeline detail view tabs (for PipelineDetailView tabbed interface)
export type PipelineTab = 'overview' | 'infrastructure' | 'diff' | 'timeline' | 'observability';

// Run type for unified pipeline/generation list
export type RunType = 'pipeline' | 'generation';

// Types for Dashboard
export type JobStatus = 'Completed' | 'Failed' | 'In Progress';
export type ProjectStatus = 'Active' | 'Archived' | 'Paused';

export interface GenerationJob {
    id: string;
    timestamp: string;
    status: JobStatus;
    provider: CloudProvider;
    output: OutputType;
    prompt: string;
}

// Types for Deployments Page
export type DeploymentStatus = 'Success' | 'Failed' | 'Running';

export interface Deployment {
    id: string;
    projectName: string;
    type: OutputType;
    provider: CloudProvider;
    status: DeploymentStatus;
    createdAt: string; // ISO 8601 string for sorting
    timestamp: string; // User-friendly string e.g., "4 hours ago"
}

export interface DeploymentLog {
    plan: string;
    apply: string;
    output?: string;
}

// Types for Settings Page
export type UserRole = 'Owner' | 'Admin' | 'Editor' | 'Viewer';

export interface TeamMember {
    id: string;
    name: string;
    email: string;
    avatarUrl: string;
    role: UserRole;
}

export interface AccordionItem {
    id:string;
    title: string;
    subtitle: string;
    icon: React.ReactNode;
    content: React.ReactNode;
}

// Types for Developer Settings Page
export interface ApiKey {
    id: string;
    name: string;
    tokenPreview: string; // e.g., "sk_...1234"
    createdAt: string;
    lastUsed: string | null;
}

// Types for Billing Page
export type Plan = 'Free' | 'Pro';

export interface Invoice {
    id: string;
    date: string;
    amount: number;
    status: 'Paid' | 'Pending' | 'Failed';
}

// Types for Audit Log Page
export interface AuditLogEvent {
    id:string;
    actor: {
        name: string;
        email: string;
    };
    action: string;
    timestamp: string;
    ipAddress: string;
}

// Type for the new Log Console - now aligned with backend logs
export type LogEntry = ValidationStepLog;

// Types for Generation History Management
export interface Generation {
  id: string;
  projectId: string;
  prompt: string;
  modelId: string;
  provider: CloudProvider;
  status: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
  files: GeneratedFile[];
  logs: ValidationStepLog[];
  createdAt: string; // ISO 8601 string
  completedAt?: string; // ISO 8601 string, optional
  stateHistory: StateTransition[];
}

export interface StateTransition {
  fromState: string;
  toState: string;
  timestamp: string; // ISO 8601 string
  duration?: number; // in seconds, optional
  eventDescription: string;
}

export interface GenerationWithMetadata extends Generation {
  iteration?: number;
  estimatedTimeRemaining?: number; // in seconds, optional
}

export interface GenerationListResponse {
  generations: Generation[];
  pagination: {
    page: number;
    limit: number;
    totalItems: number;
    totalPages: number;
  };
}

export interface GenerationFilter {
  status?: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
  dateFrom?: string; // ISO 8601 string
  dateTo?: string; // ISO 8601 string
  modelId?: string;
  provider?: CloudProvider;
  searchQuery?: string;
}

export interface GenerationRetryRequest {
  modelId?: string; // Optional override of model
}

export interface GenerationStateHistory {
  id: string;
  stateHistory: StateTransition[];
}

// Types for Clarification Flow
export type ClarifyResponseStatus = 'questions' | 'coding' | 'failed' | 'review';

export interface ClarifyAnswerResponse {
  status: ClarifyResponseStatus;
  questions?: string[];
  message?: string;
  options?: any[];
  refined_spec?: Record<string, unknown>;
  error?: string;
}

export interface GenerationEstimatedTimeRemaining {
  currentState: string;
  currentIteration?: number;
  maxIterations?: number;
  estimatedTimeRemaining: number; // in seconds
  confidenceInterval: {
    low: number;
    high: number;
  };
  historicalAverageForSimilarPrompt?: number; // in seconds, optional
}

export interface LLMCompletionResponse {
  id: string;
  object: string;
  created: number;
  model: string;
  choices: Array<{
    index: number;
    text: string;
    finish_reason: string | null;
  }>;
  usage: {
    prompt_tokens: number;
    completion_tokens: number;
    total_tokens: number;
  };
  model_used: string;
  total_cost: number;
  cached: boolean;
  latency_ms_ms?: number;
  failover_from?: string;
  failover_to?: string;
}

// Types for Generation History Page
export interface GenerationHistoryPageState {
  generations: Generation[];
  filteredGenerations: Generation[];
  isLoading: boolean;
  error: string | null;

  // Filters
  statusFilter?: 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
  dateFrom: string | null;
  dateTo: string | null;
  modelFilter: string | 'all';
  providerFilter: CloudProvider | 'all';
  searchQuery: string;

  // Pagination
  currentPage: number;
  itemsPerPage: number;
  totalItems: number;

  // Selection
  selectedGenerations: Set<string>;

  // Detail view
  selectedGenerationId: string | null;
}

// Types for StatusBadge component
export type StatusVariant = 'success' | 'failed' | 'in-progress' | 'pending' | 'neutral';

export type GenerationStatusBadgeType = 'COMPLETED' | 'FAILED' | 'IN_PROGRESS' | 'HUMAN_REVIEW';
export type DeploymentStatusBadgeType = 'success' | 'failed' | 'in-progress' | 'pending-approval';

export interface StatusBadgeProps {
  status: string;
  variant?: StatusVariant;
  showIcon?: boolean;
  className?: string;
  ariaLabel?: string;
}

export interface GenerationStatusBadgeProps {
  status: GenerationStatusBadgeType;
  showIcon?: boolean;
  className?: string;
}

export interface DeploymentStatusBadgeProps {
  status: DeploymentStatusBadgeType;
  showIcon?: boolean;
  className?: string;
}

// ============================================================
// Pipeline Agentic Loop Types (Task 1.2)
// ============================================================

export type PipelinePhase =
  | 'clarify' | 'generate' | 'format' | 'static_analysis'
  | 'init' | 'validate' | 'plan_review' | 'plan'
  | 'apply_review' | 'apply' | 'escalate' | 'complete';

export type PipelineStatus = 'running' | 'paused' | 'completed' | 'failed' | 'escalated';

export type PhaseStatus = 'success' | 'running' | 'pending' | 'failed' | 'escalated';

export type AgentStatus = 'idle' | 'thinking' | 'executing' | 'waiting-approval' | 'done' | 'error';

export type LogLevel = 'info' | 'warning' | 'error';

export interface PipelineSession {
  id: string;
  name: string;
  phase: PipelinePhase;
  status: PipelineStatus;
  currentPhaseProgress: number; // 0-100
  startTime: string;
  elapsedSeconds: number;
  retryCount: number;
  errorCount: number;
  workspaceId?: string;
}

export interface PhaseHistoryEntry {
  phase: PipelinePhase;
  status: 'success' | 'running' | 'pending' | 'failed' | 'escalated';
  duration?: number; // seconds
  startedAt: string;
  completedAt?: string;
  details?: string;
}

export interface PipelineLogEntry {
  timestamp: string;
  phase: PipelinePhase;
  message: string;
  level: LogLevel;
}

export interface PipelineMetrics {
  phase_metrics: Record<string, { avg_duration: number; p95_duration: number; error_rate: number }>;
  agent_metrics: Record<string, { total_runs: number; avg_duration: number; success_rate: number }>;
  pipeline_metrics: { total_pipelines: number; avg_duration: number; success_rate: number };
}

export interface CreatePipelineConfig {
  name: string;
  description?: string;
  workspace_id: string;
  user_request: string;
  deploymentMode?: string;
}

export interface PipelineListItem {
  id: string;
  name: string;
  status: PipelineStatus;
  current_phase: PipelinePhase;
  created_at: string;
  updated_at: string;
}

export interface ListPipelinesResponse {
  pipelines: PipelineListItem[];
  totalItems: number;
  limit: number;
  offset: number;
}

export interface PipelineFilters {
  status?: PipelineStatus;
  phase?: PipelinePhase;
  searchQuery?: string;
  dateFrom?: string;
  dateTo?: string;
  limit?: number;
  offset?: number;
}

export interface PipelineUpdate {
  type: 'phase_transition' | 'progress_update' | 'log_entry' | 'error' | 'heartbeat';
  pipelineId: string;
  timestamp: string;
  data: Record<string, unknown>;
}

// ============================================================
// Simulation & Cost Estimation Types (Module 5)
// ============================================================

export type DeploymentMode = 'aws' | 'localstack' | 'offline';

export type CostMetric = 'compute' | 'storage' | 'database' | 'api';

export interface MetricItem {
  label: string;
  value: string | number;
  realCost?: string;
  simulated: boolean;
}

export interface CostMetricData {
  label: string;
  icon: string;
  items: MetricItem[];
  estimatedCost: string;
}

export interface CostEstimationData {
  metrics: Record<CostMetric, CostMetricData>;
  totalRealCost: number;
  totalSimulatedCost: number;
  savings: number;
  savingsPercent: number;
  lastUpdated: string; // ISO timestamp string
}

// ============================================================
// Module 7: Monaco Workspace Types
// ============================================================

export interface EditorTab {
  id: string;
  file: GeneratedFile;
  isDirty: boolean;
  isSelected: boolean;
  isClosed: boolean;
}

export interface EditorViewState {
  line: number;
  column: number;
  selectionStart?: number;
  selectionEnd?: number;
}

export interface CodeActionState {
  canFormat: boolean;
  formatStatus: 'idle' | 'formatting' | 'formatted' | 'error';
  validationIssues: ValidationIssue[];
  isValidationRunning: boolean;
}

export interface ValidationIssue {
  severity: 'error' | 'warning' | 'info';
  message: string;
  line: number;
  column: number;
}

