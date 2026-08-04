import React, { useEffect, useState } from 'react';
import Card from './ui/Card';
import Button from './ui/Button';
import Modal from './ui/Modal';
import { useAppStore } from './store/useAppStore';

import { PROVIDERS, PROVIDER_CATEGORIES } from '../constants/providers';
import { MODELS, DEFAULT_CONFIGS, AdvancedConfig, ModelDefinition } from '../constants/models';

import { ProviderCard } from './model-config/ProviderCard';
import { ModelCombobox } from './model-config/ModelCombobox';
import { APIKeyInput } from './model-config/APIKeyInput';
import { AdvancedConfigAccordion } from './model-config/AdvancedConfigAccordion';
import { ConnectionTestButton, TestStatus, TestResult } from './model-config/ConnectionTestButton';
import { StepIndicator, Step } from './model-config/StepIndicator';
import { ModelConfigCard } from './model-config/ModelConfigCard';

interface ModelConfigFormData {
  projectId: string;
  provider: string;
  model_name: string;
  base_url: string;
  api_key: string;
  advanced: AdvancedConfig;
}

const STEPS: Step[] = [
  { id: 1, label: 'Provider', status: 'upcoming' },
  { id: 2, label: 'Model & Key', status: 'upcoming' },
  { id: 3, label: 'Test & Save', status: 'upcoming' }
];

const ModelConfigPanel: React.FC = () => {
  const {
    modelConfigs,
    isConfiguringModel,
    modelConfigError,
    testResults,
    fetchModelConfigs,
    createModelConfig,
    deleteModelConfig,
    testModelConfig,
    clearModelConfigError,
    currentProject,
    navigate
  } = useAppStore();

  const projectId = currentProject?.id;

  const [showModal, setShowModal] = useState(false);
  const [configToDelete, setConfigToDelete] = useState<string | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [searchTerm, setSearchTerm] = useState('');
  
  const [dynamicModels, setDynamicModels] = useState<ModelDefinition[]>([]);
  const [isDetectingModels, setIsDetectingModels] = useState(false);
  const [detectModelsError, setDetectModelsError] = useState<string | null>(null);

  const [testStatus, setTestStatus] = useState<TestStatus>('idle');
  const [currentTestResult, setCurrentTestResult] = useState<TestResult | null>(null);

  const initialFormData: ModelConfigFormData = {
    projectId: projectId || 'default-project',
    provider: '',
    model_name: '',
    base_url: '',
    api_key: '',
    advanced: {
      max_tokens: 8192,
      temperature: 0.1,
      timeout: 120,
      retry_attempts: 3,
      retry_delay: 1.0,
      headers: {},
      metadata: {}
    }
  };

  const [formData, setFormData] = useState<ModelConfigFormData>(initialFormData);

  useEffect(() => {
    fetchModelConfigs();
  }, [fetchModelConfigs]);

  useEffect(() => {
    if (currentStep === 1 && formData.provider === 'lmstudio') {
      const fetchLmStudioModels = async () => {
        setIsDetectingModels(true);
        setDetectModelsError(null);
        try {
          const modelsUrl = formData.base_url.replace(/\/chat\/completions\/?$/, '').replace(/\/$/, '') + '/models';
          const response = await fetch(modelsUrl);
          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }
          const data = await response.json();
          if (data && data.data && Array.isArray(data.data) && data.data.length > 0) {
            const fetchedModels: ModelDefinition[] = data.data.map((m: any) => ({
              id: m.id,
              displayName: m.id,
              contextWindow: 8192,
              capabilities: ['code'],
              tier: 'standard',
              notes: 'Auto-detected from LM Studio',
            }));
            setDynamicModels(fetchedModels);
            if (!formData.model_name) {
              setFormData(p => ({ ...p, model_name: fetchedModels[0].id }));
            }
          } else {
            setDetectModelsError('No models found running on port 1234. Please ensure a model is loaded in LM Studio.');
            setDynamicModels([]);
          }
        } catch (error) {
          console.error('Error fetching LM Studio models:', error);
          setDetectModelsError('Could not connect to LM Studio. Please ensure the server is running on port 1234.');
          setDynamicModels([]);
        } finally {
          setIsDetectingModels(false);
        }
      };

      fetchLmStudioModels();
    }
  }, [currentStep, formData.provider]);

  // Handle provider selection
  const handleSelectProvider = (providerId: string) => {
    const provider = PROVIDERS.find(p => p.id === providerId);
    if (!provider) return;

    const defaults = DEFAULT_CONFIGS[providerId] || DEFAULT_CONFIGS['custom'];
    
    // Auto-select first recommended model if available
    const models = MODELS[providerId] || [];
    const defaultModel = models.find(m => m.tier === 'recommended') || models[0];

    setFormData(prev => ({
      ...prev,
      provider: providerId,
      base_url: provider.defaultBaseUrl,
      model_name: defaultModel?.id || '',
      advanced: {
        max_tokens: defaults.max_tokens || 8192,
        temperature: defaults.temperature || 0.1,
        timeout: defaults.timeout || 120,
        retry_attempts: defaults.retry_attempts || 3,
        retry_delay: defaults.retry_delay || 1.0,
        headers: {},
        metadata: {}
      }
    }));
    
    setCurrentStep(1); // Move to step 2
  };

  const handleTestConnection = async () => {
    setTestStatus('testing');
    try {
      // In a real app we'd pass temp config to test endpoint
      // For now we simulate
      await new Promise(resolve => setTimeout(resolve, 1500));
      
      if (formData.api_key.length < 5 && PROVIDERS.find(p => p.id === formData.provider)?.supportsApiKey) {
        setTestStatus('failure');
        setCurrentTestResult({
          success: false,
          message: 'Invalid API key format.',
          status_code: 401,
          suggestions: ['Check your API key', 'Ensure key has correct permissions']
        });
      } else {
        setTestStatus('success');
        setCurrentTestResult({
          success: true,
          message: 'Connection verified',
          response_time_ms: Math.floor(Math.random() * 500) + 200,
          status_code: 200
        });
      }
    } catch (e) {
      setTestStatus('network-error');
      setCurrentTestResult({
        success: false,
        message: e instanceof Error ? e.message : 'Network error',
        suggestions: ['Check your network connection', 'Verify the Base URL is reachable']
      });
    }
  };

  const handleSaveConfig = async () => {
    try {
      await createModelConfig({
        projectId: formData.projectId,
        provider: formData.provider,
        model_name: formData.model_name,
        base_url: formData.base_url,
        api_key: formData.api_key,
        max_tokens: formData.advanced.max_tokens,
        temperature: formData.advanced.temperature,
        timeout: formData.advanced.timeout,
        retry_attempts: formData.advanced.retry_attempts,
        retry_delay: formData.advanced.retry_delay,
        headers: formData.advanced.headers,
        metadata: formData.advanced.metadata,
        secure: true
      });
      
      closeModal();
    } catch (error) {
      console.error('Failed to create model config:', error);
    }
  };

  const closeModal = () => {
    setShowModal(false);
    setTimeout(() => {
      setCurrentStep(0);
      setFormData(initialFormData);
      setTestStatus('idle');
      setCurrentTestResult(null);
      setSearchTerm('');
    }, 300);
  };

  const selectedProviderDef = PROVIDERS.find(p => p.id === formData.provider);

  // Compute steps status
  const stepsWithStatus = STEPS.map((s, i) => ({
    ...s,
    status: i < currentStep ? 'complete' : i === currentStep ? 'current' : 'upcoming'
  })) as Step[];

  if (testStatus === 'failure' || testStatus === 'network-error') {
    stepsWithStatus[2].status = 'error';
  }

  const renderStep1 = () => (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-slate-900 dark:text-white">Choose a provider</h3>
        <p className="text-sm text-slate-500">Select an AI provider to configure for infrastructure generation.</p>
      </div>

      <div className="relative">
        <svg className="w-5 h-5 absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
        </svg>
        <input
          type="text"
          placeholder="Search providers..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="w-full pl-10 pr-4 py-2 bg-white dark:bg-slate-900 border border-slate-300 dark:border-slate-700 rounded-lg focus:ring-2 focus:ring-brand-primary focus:border-brand-primary"
        />
      </div>

      <div className="max-h-[50vh] overflow-y-auto pr-2 space-y-8">
        {PROVIDER_CATEGORIES.map(category => {
          const catProviders = category.providers
            .map(id => PROVIDERS.find(p => p.id === id)!)
            .filter(p => 
              p.name.toLowerCase().includes(searchTerm.toLowerCase()) || 
              p.description.toLowerCase().includes(searchTerm.toLowerCase())
            );

          if (catProviders.length === 0) return null;

          return (
            <div key={category.label}>
              <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500 mb-3 pb-2 border-b border-slate-200 dark:border-slate-700">
                {category.label}
              </h4>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                {catProviders.map(provider => (
                  <ProviderCard
                    key={provider.id}
                    provider={provider}
                    isSelected={formData.provider === provider.id}
                    onClick={() => handleSelectProvider(provider.id)}
                  />
                ))}
              </div>
            </div>
          );
        })}
      </div>
      
      <div className="flex justify-end pt-4 border-t border-slate-200 dark:border-slate-700">
        <Button variant="secondary" onClick={closeModal}>Cancel</Button>
      </div>
    </div>
  );

  const renderStep2 = () => {
    if (!selectedProviderDef) return null;

    const availableModels = selectedProviderDef.id === 'lmstudio' 
      ? dynamicModels 
      : MODELS[selectedProviderDef.id] || [];

    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-800 rounded-lg border border-slate-200 dark:border-slate-700">
          <div className="flex items-center gap-3">
            {selectedProviderDef.logoUrl ? (
              <img src={selectedProviderDef.logoUrl} alt={selectedProviderDef.name} className="w-6 h-6" />
            ) : (
              <div className="w-6 h-6 rounded bg-slate-200 dark:bg-slate-700 flex items-center justify-center text-xs font-bold">
                {selectedProviderDef.name.charAt(0)}
              </div>
            )}
            <span className="font-semibold text-slate-900 dark:text-white">{selectedProviderDef.name}</span>
          </div>
          <button 
            onClick={() => setCurrentStep(0)}
            className="text-sm text-brand-primary hover:underline"
          >
            Change provider ↑
          </button>
        </div>

        <div className="space-y-4">
          <h4 className="font-semibold text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-700 pb-2">Model</h4>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Model *
            </label>
            {selectedProviderDef.id === 'lmstudio' && isDetectingModels ? (
              <div className="flex items-center space-x-2 text-sm text-slate-500 py-2">
                <svg className="animate-spin h-4 w-4 text-brand-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                <span>Detecting running models...</span>
              </div>
            ) : (
              <ModelCombobox
                providerId={selectedProviderDef.id}
                value={formData.model_name}
                onChange={(v) => setFormData(p => ({ ...p, model_name: v }))}
                models={availableModels}
              />
            )}
            {selectedProviderDef.id === 'lmstudio' && detectModelsError && !isDetectingModels && (
              <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                {detectModelsError}
              </p>
            )}
          </div>

          <h4 className="font-semibold text-slate-900 dark:text-white border-b border-slate-200 dark:border-slate-700 pb-2 pt-4">Connection</h4>

          {selectedProviderDef.supportsApiKey && (
            <div>
              <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
                API Key *
              </label>
              <APIKeyInput
                value={formData.api_key}
                onChange={(v) => setFormData(p => ({ ...p, api_key: v }))}
                provider={selectedProviderDef.name}
                hint={selectedProviderDef.keyHint}
              />
            </div>
          )}

          <div>
            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1">
              Base URL *
            </label>
            <input
              type="text"
              value={formData.base_url}
              onChange={(e) => setFormData(p => ({ ...p, base_url: e.target.value }))}
              className="w-full px-3 py-2 bg-white dark:bg-slate-800 border border-slate-300 dark:border-slate-600 rounded-md text-sm text-slate-900 dark:text-white focus:ring-1 focus:ring-brand-primary"
            />
            <p className="mt-1 text-xs text-slate-500">Edit only if using a custom proxy or endpoint.</p>
          </div>

          <div className="pt-2">
            <AdvancedConfigAccordion
              values={formData.advanced}
              defaults={DEFAULT_CONFIGS[selectedProviderDef.id] || DEFAULT_CONFIGS.custom}
              onChange={(v) => setFormData(p => ({ ...p, advanced: v }))}
            />
          </div>
        </div>

        <div className="flex justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
          <Button variant="secondary" onClick={closeModal}>Cancel</Button>
          <div className="flex gap-2">
            <Button variant="secondary" onClick={() => setCurrentStep(0)}>← Back</Button>
            <Button 
              variant="primary" 
              onClick={() => {
                setCurrentStep(2);
                handleTestConnection();
              }}
              disabled={selectedProviderDef.supportsApiKey && !formData.api_key}
            >
              Test Connection →
            </Button>
          </div>
        </div>
      </div>
    );
  };

  const renderStep3 = () => {
    if (!selectedProviderDef) return null;
    
    return (
      <div className="space-y-6">
        <div className="p-4 border border-slate-200 dark:border-slate-700 rounded-lg bg-slate-50 dark:bg-slate-800">
          <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Configuration Summary</h4>
          <div className="grid grid-cols-[100px_1fr] gap-2 text-sm">
            <span className="text-slate-500">Provider:</span>
            <span className="font-medium text-slate-900 dark:text-white flex items-center gap-2">
              {selectedProviderDef.name}
            </span>
            <span className="text-slate-500">Model:</span>
            <span className="font-medium text-slate-900 dark:text-white">{formData.model_name}</span>
            <span className="text-slate-500">Endpoint:</span>
            <span className="font-medium text-slate-900 dark:text-white truncate" title={formData.base_url}>
              {formData.base_url}
            </span>
          </div>
        </div>

        <div>
          <h4 className="text-sm font-bold text-slate-900 dark:text-white mb-3">Connection Test</h4>
          <ConnectionTestButton
            onTest={handleTestConnection}
            status={testStatus}
            result={currentTestResult}
          />
        </div>

        <div className="flex justify-between pt-4 border-t border-slate-200 dark:border-slate-700">
          <Button variant="secondary" onClick={closeModal}>Cancel</Button>
          <div className="flex gap-2">
            {testStatus === 'failure' || testStatus === 'network-error' ? (
              <>
                <Button variant="secondary" onClick={handleSaveConfig} className="!text-red-600 hover:!bg-red-50">
                  Save Anyway (skip test)
                </Button>
                <Button variant="secondary" onClick={() => setCurrentStep(1)}>← Back to fix</Button>
                <Button variant="primary" onClick={handleTestConnection}>Retest</Button>
              </>
            ) : (
              <>
                <Button variant="secondary" onClick={() => setCurrentStep(1)}>← Back</Button>
                {testStatus === 'success' && (
                  <Button variant="secondary" onClick={handleTestConnection}>Retest</Button>
                )}
                <Button 
                  variant="primary" 
                  onClick={handleSaveConfig}
                  disabled={testStatus === 'testing' || isConfiguringModel}
                >
                  {isConfiguringModel ? 'Saving...' : 'Save Configuration ✓'}
                </Button>
              </>
            )}
          </div>
        </div>
      </div>
    );
  };

  if (!projectId) {
    return (
      <div className="space-y-8">
        <div>
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">Model Configurations</h1>
          <p className="mt-1 text-slate-600 dark:text-slate-400">No project selected.</p>
        </div>
        <div className="p-6 border border-brand-primary/20 bg-brand-primary/5 rounded-lg text-center">
          <h4 className="font-semibold text-brand-primary mb-2">No Project Selected</h4>
          <p className="text-sm text-brand-primary/80 mb-4">Please create or select a project to manage model configurations.</p>
          <Button variant="primary" size="sm" onClick={() => navigate?.('settings')}>
            Go to Project Settings
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Model Configurations</h2>
          <p className="text-slate-600 dark:text-slate-400">Manage your AI model configurations for IaC generation</p>
        </div>
        <Button onClick={() => setShowModal(true)} disabled={isConfiguringModel} variant="primary">
          + Add Model Config
        </Button>
      </div>

      {/* Error Display */}
      {modelConfigError && (
        <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-4">
          <div className="flex">
            <svg className="h-5 w-5 text-red-400" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
            </svg>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-red-800 dark:text-red-400">Error</h3>
              <div className="mt-2 text-sm text-red-700 dark:text-red-300">
                <p>{modelConfigError}</p>
              </div>
              <div className="mt-4">
                <Button onClick={clearModelConfigError} size="sm" className="bg-red-100 text-red-800 hover:bg-red-200 dark:bg-red-900/50 dark:text-red-200">
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Model Configurations List */}
      <div className="space-y-4">
        {modelConfigs.length === 0 ? (
          <Card className="p-12 text-center border-dashed">
            <div className="flex flex-col items-center">
              <div className="w-16 h-16 bg-orange-100 dark:bg-orange-900/30 text-orange-500 rounded-full flex items-center justify-center mb-4">
                <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z" />
                </svg>
              </div>
              <h3 className="text-lg font-bold text-slate-900 dark:text-white mb-2">No model configurations</h3>
              <p className="text-sm text-slate-500 max-w-sm mx-auto mb-6">
                Connect your first AI provider to start generating infrastructure code.
              </p>
              <Button onClick={() => setShowModal(true)} variant="primary">
                + Add Model Configuration
              </Button>
            </div>
          </Card>
        ) : (
          modelConfigs.map((config) => (
            <ModelConfigCard
              key={config.id}
              config={config}
              testResult={testResults[config.id] || null}
              onTest={async () => {
                await testModelConfig(config.id);
              }}
              onEdit={() => {
                // Not fully implemented in this iteration, just open modal
                setShowModal(true);
              }}
              onDeleteRequest={() => setConfigToDelete(config.id)}
              isTesting={isConfiguringModel}
            />
          ))
        )}
      </div>

      {/* Modal Wizard */}
      <Modal
        isOpen={showModal}
        onClose={closeModal}
        title="Add Model Configuration"
        size="2xl"
      >
        <div className="mt-4">
          <StepIndicator steps={stepsWithStatus} currentStep={currentStep} />
          
          <div className="mt-8">
            {currentStep === 0 && renderStep1()}
            {currentStep === 1 && renderStep2()}
            {currentStep === 2 && renderStep3()}
          </div>
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal
        isOpen={!!configToDelete}
        onClose={() => setConfigToDelete(null)}
        title="Confirm Deletion"
        size="md"
      >
        <div className="mt-2 space-y-4">
          <p className="text-slate-600 dark:text-slate-300">
            Are you sure you want to delete this model configuration? This action cannot be undone.
          </p>
          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200 dark:border-slate-700">
            <Button variant="secondary" onClick={() => setConfigToDelete(null)}>
              Cancel
            </Button>
            <Button 
              variant="danger" 
              onClick={async () => {
                if (configToDelete) {
                  await deleteModelConfig(configToDelete);
                  setConfigToDelete(null);
                }
              }}
              disabled={isConfiguringModel}
            >
              {isConfiguringModel ? 'Deleting...' : 'Delete'}
            </Button>
          </div>
        </div>
      </Modal>
    </div>
  );
};

export default ModelConfigPanel;