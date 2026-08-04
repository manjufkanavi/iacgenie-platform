/**
 * IacGenie Platform Constants
 */
export const AVAILABLE_MODELS = [
  { id: 'gemini-2.5-flash', name: 'Gemini 2.5 Flash', provider: 'google' },
  { id: 'gemini-2.5-pro', name: 'Gemini 2.5 Pro', provider: 'google' },
  { id: 'claude-sonnet-4', name: 'Claude Sonnet 4', provider: 'anthropic' },
  { id: 'claude-opus-4', name: 'Claude Opus 4', provider: 'anthropic' },
  { id: 'gpt-4o', name: 'GPT-4o', provider: 'openai' },
  { id: 'mistral-large', name: 'Mistral Large', provider: 'mistral' },
];

export const DEFAULT_MODEL = 'gemini-2.5-flash';

export const API_BASE_PATH = '/api';

export const DEPLOYMENT_TARGETS = ['aws', 'gcp', 'azure', 'kubernetes', 'docker', 'terraform'];

export const PROJECT_STATUS = {
  DRAFT: 'draft',
  GENERATING: 'generating',
  READY: 'ready',
  ERROR: 'error',
  DEPLOYING: 'deploying',
  DEPLOYED: 'deployed',
} as const;

// Re-export ICONS for components that import from constants
export * from './icons';
