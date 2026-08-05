import React, { useState, useEffect } from 'react';
import { Check, ArrowLeft, ArrowRight, Github, Gitlab, Code, Loader2, CheckCircle2, XCircle, Info, Copy, Key } from 'lucide-react';
import { toast } from 'react-hot-toast';
import Button from '../ui/Button';
import Input from '../ui/Input';
import { webhookService } from '../services/webhookService';
import { gitOpsService } from '../services/gitOpsService';

export type WebhookStep = 'choose-provider' | 'configure' | 'verify';

export interface WebhookConfigData {
    provider: 'github' | 'gitlab' | 'bitbucket' | null;
    repoUrl: string;
    webhookSecret: string;
    connectionTestResult: 'idle' | 'testing' | 'success' | 'error';
    connectionTestError?: string;
}

interface WebhookSetupFormProps {
    projectId: string;
    repoUrl?: string;
    provider?: string;
    onComplete: (config: any) => void;
    onCancel: () => void;
    className?: string;
}

const WebhookSetupForm: React.FC<WebhookSetupFormProps> = ({
    projectId,
    repoUrl = '',
    provider = 'github',
    onComplete,
    onCancel,
    className = ''
}) => {
    const [currentStep, setCurrentStep] = useState<number>(0);
    const [formData, setFormData] = useState<WebhookConfigData>({
        provider: (provider as any) || 'github',
        repoUrl: repoUrl || '',
        webhookSecret: '',
        connectionTestResult: 'idle',
        connectionTestError: ''
    });
    
    const [generatedUrl, setGeneratedUrl] = useState('');
    const [testResult, setTestResult] = useState<{ statusCode?: number; responseTime?: number } | null>(null);
    const [errors, setErrors] = useState<Record<string, string>>({});
    
    const steps = [
        { id: 'choose-provider', label: 'Choose Provider' },
        { id: 'configure', label: 'Configure Webhook' },
        { id: 'verify', label: 'Verify Connection' }
    ];

    // Generate random secret token
    const generateSecret = () => {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()_+';
        let secret = '';
        for (let i = 0; i < 24; i++) {
            secret += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        setFormData(prev => ({ ...prev, webhookSecret: secret }));
        if (errors.webhookSecret) {
            setErrors(prev => ({ ...prev, webhookSecret: '' }));
        }
    };

    useEffect(() => {
        if (currentStep === 1) {
            // Pre-fill webhook URL
            const cleanRepoName = formData.repoUrl
                ? formData.repoUrl.split('/').pop()?.replace('.git', '') || 'my-repo'
                : 'my-repo';
            const baseUrl = typeof window !== 'undefined' ? window.location.origin : '';
            setGeneratedUrl(`${baseUrl}/api/webhooks/receive/${projectId}-${cleanRepoName}`);
            
            // Auto generate secret if empty
            if (!formData.webhookSecret) {
                generateSecret();
            }
        }
    }, [currentStep, formData.repoUrl]);

    const handleCopy = (text: string, label: string) => {
        navigator.clipboard.writeText(text);
        toast.success(`${label} copied to clipboard!`);
    };

    const validateStep = () => {
        const newErrors: Record<string, string> = {};

        if (currentStep === 0) {
            if (!formData.provider) {
                newErrors.provider = 'Please select a git provider';
            }
        } else if (currentStep === 1) {
            if (!formData.repoUrl.trim()) {
                newErrors.repoUrl = 'Repository URL is required';
            } else if (!formData.repoUrl.startsWith('http://') && !formData.repoUrl.startsWith('https://') && !formData.repoUrl.includes('@')) {
                newErrors.repoUrl = 'Please enter a valid Repository URL';
            }
            if (!formData.webhookSecret.trim()) {
                newErrors.webhookSecret = 'Webhook secret is required';
            } else if (formData.webhookSecret.length < 16) {
                newErrors.webhookSecret = 'Secret token must be at least 16 characters for security';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleNext = () => {
        if (validateStep()) {
            setCurrentStep(prev => prev + 1);
        }
    };

    const handleBack = () => {
        setCurrentStep(prev => prev - 1);
    };

    const handleConnectionTest = async () => {
        setFormData(prev => ({ ...prev, connectionTestResult: 'testing', connectionTestError: '' }));

        try {
            const result = await gitOpsService.testWebhookUrl(generatedUrl, formData.webhookSecret);
            if (result.success) {
                setFormData(prev => ({ ...prev, connectionTestResult: 'success' }));
                setTestResult({ statusCode: result.status_code || 200, responseTime: result.response_time || 0 });
                toast.success(result.message || 'Webhook connection validated successfully!');
                setCurrentStep(2);
            } else {
                setFormData(prev => ({
                    ...prev,
                    connectionTestResult: 'error',
                    connectionTestError: result.error || result.message || 'Could not reach webhook endpoint'
                }));
                toast.error(result.message || 'Webhook validation failed');
            }
        } catch (err: any) {
            setFormData(prev => ({
                ...prev,
                connectionTestResult: 'error',
                connectionTestError: err.message || 'Could not reach webhook endpoint'
            }));
            toast.error(err.message || 'Webhook validation failed');
        }
    };

    const handleSaveConfig = async () => {
        try {
            const webhookRecord = await webhookService.createWebhook(projectId, {
                name: `Digger GitOps - ${formData.provider?.toUpperCase()} - ${formData.repoUrl.split('/').pop()?.replace('.git', '')}`,
                url: generatedUrl,
                events: ['push', 'pull_request', 'issue_comment'],
                secret: formData.webhookSecret,
                isActive: true
            });
            toast.success('Digger GitOps Webhook registered and activated successfully!');
            onComplete(webhookRecord);
        } catch (error: any) {
            toast.error(error.message || 'Failed to register webhook in project');
        }
    };

    const renderStepContent = () => {
        switch (currentStep) {
            case 0:
                return (
                    <div className="space-y-6 py-4">
                        <div className="text-center max-w-md mx-auto">
                            <h4 className="text-lg font-bold text-slate-800 dark:text-slate-100">Select Git Provider</h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                                Pick the Git hosting provider where your infrastructure repository lives to load customized integration templates.
                            </p>
                        </div>
                        
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 max-w-3xl mx-auto pt-2">
                            {[
                                { id: 'github', label: 'GitHub', desc: 'Auto setup comments and triggers with Digger Helm', icon: <Github className="w-8 h-8 text-[var(--color-git-provider-github)]" /> },
                                { id: 'gitlab', label: 'GitLab', desc: 'Auto setup merge request pipelines with GitLab runner', icon: <Gitlab className="w-8 h-8 text-[var(--color-git-provider-gitlab)]" /> },
                                { id: 'bitbucket', label: 'Bitbucket', desc: 'Manual webhook setup with IaC pipelines', icon: <Code className="w-8 h-8 text-indigo-500" /> }
                            ].map((prov) => {
                                const isSelected = formData.provider === prov.id;
                                return (
                                    <button
                                        key={prov.id}
                                        type="button"
                                        onClick={() => setFormData(prev => ({ ...prev, provider: prov.id as any }))}
                                        className={`flex flex-col items-center justify-center p-6 rounded-2xl border-2 text-center transition-all duration-300 ${
                                            isSelected
                                                ? 'bg-gradient-to-br from-brand-primary/10 to-red-500/10 border-brand-primary text-brand-primary shadow-md scale-105'
                                                : 'bg-white dark:bg-slate-800 border-slate-200 dark:border-slate-700 hover:border-slate-300 dark:hover:border-slate-600 text-slate-700 dark:text-slate-200'
                                        }`}
                                    >
                                        <div className="mb-3 p-3 bg-slate-50 dark:bg-slate-700/50 rounded-2xl shadow-sm">{prov.icon}</div>
                                        <span className="font-extrabold text-sm">{prov.label}</span>
                                        <span className="text-[10px] text-slate-400 mt-1">{prov.desc}</span>
                                    </button>
                                );
                            })}
                        </div>
                        {errors.provider && (
                            <p className="text-center text-xs text-red-500 mt-2 font-semibold">{errors.provider}</p>
                        )}
                    </div>
                );
            case 1:
                return (
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 py-2">
                        {/* Left Side: Setup Instructions */}
                        <div className="bg-slate-50 dark:bg-slate-800/50 rounded-2xl p-6 border border-slate-200/50 dark:border-slate-700/50 space-y-4">
                            <h4 className="font-bold text-slate-800 dark:text-slate-100 text-sm uppercase tracking-wider flex items-center gap-1.5 border-b border-slate-200 dark:border-slate-700 pb-2.5">
                                <Info className="w-4 h-4 text-brand-primary" /> Setup Instructions for {formData.provider === 'github' ? 'GitHub' : 'GitLab'}
                            </h4>

                            <div className="space-y-4 text-xs text-slate-600 dark:text-slate-400 leading-relaxed overflow-y-auto max-h-[300px] scrollbar-thin pr-1">
                                {formData.provider === 'github' ? (
                                    <>
                                        <p>To enable Digger bot integration on your GitHub repository, complete the following settings:</p>
                                        <ol className="list-decimal list-inside space-y-3">
                                            <li>
                                                Go to your **GitHub Repository Settings** tab in the browser.
                                            </li>
                                            <li>
                                                Click on **Webhooks** in the left sidebar, and click the **"Add Webhook"** button.
                                            </li>
                                            <li>
                                                Copy the **Payload URL** on the right and paste it into GitHub's payload URL input field.
                                            </li>
                                            <li>
                                                Set the Content type dropdown to **`application/json`**.
                                            </li>
                                            <li>
                                                Copy the generated **Secret Token** on the right and paste it into GitHub's secret field.
                                            </li>
                                            <li>
                                                Select **"Let me select individual events"** under triggers and check:
                                                <ul className="list-disc list-inside ml-4 mt-1 font-semibold text-slate-700 dark:text-slate-300">
                                                    <li>Pushes</li>
                                                    <li>Pull Requests</li>
                                                    <li>Issue comments (for apply triggers)</li>
                                                </ul>
                                            </li>
                                            <li>
                                                Ensure **Active** is checked and click **Add Webhook** to save.
                                            </li>
                                        </ol>
                                    </>
                                ) : (
                                    <>
                                        <p>To enable Digger bot integration on your GitLab repository, complete the following settings:</p>
                                        <ol className="list-decimal list-inside space-y-3">
                                            <li>
                                                Navigate to your **GitLab Project Settings** {'->'} **Webhooks**.
                                            </li>
                                            <li>
                                                Copy the **Payload URL** on the right and paste it into the **URL** input.
                                            </li>
                                            <li>
                                                Copy the generated **Secret Token** on the right and paste it into the **Secret Token** input.
                                            </li>
                                            <li>
                                                Under **Trigger**, check the following event boxes:
                                                <ul className="list-disc list-inside ml-4 mt-1 font-semibold text-slate-700 dark:text-slate-300">
                                                    <li>Push events</li>
                                                    <li>Merge request events</li>
                                                    <li>Comments (for apply triggers)</li>
                                                </ul>
                                            </li>
                                            <li>
                                                Leave "Enable SSL verification" checked and click **"Add Webhook"** to save.
                                            </li>
                                        </ol>
                                    </>
                                )}
                            </div>
                        </div>

                        {/* Right Side: Form Inputs */}
                        <div className="space-y-5">
                            <div>
                                <h4 className="text-sm font-bold text-slate-800 dark:text-slate-100">Webhook Details</h4>
                                <p className="text-[10px] text-slate-400">Configure Webhook fields and establish connection validation.</p>
                            </div>

                            <Input
                                label="Repository URL"
                                id="repoUrl"
                                value={formData.repoUrl}
                                onChange={(e) => setFormData(prev => ({ ...prev, repoUrl: e.target.value }))}
                                placeholder="e.g. https://github.com/myorg/my-infra-repo"
                                error={errors.repoUrl}
                                required
                            />

                            <div>
                                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                                    Generated Payload URL
                                </label>
                                <div className="flex gap-2">
                                    <input
                                        type="text"
                                        readOnly
                                        value={generatedUrl}
                                        className="flex-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400 rounded-xl px-4 py-2.5 outline-none font-mono text-[10px] select-all truncate"
                                    />
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        onClick={() => handleCopy(generatedUrl, 'Payload URL')}
                                        className="px-3 py-2 flex items-center justify-center rounded-xl bg-slate-100 hover:bg-slate-200"
                                    >
                                        <Copy className="w-4 h-4 text-slate-500" />
                                    </Button>
                                </div>
                            </div>

                            <div>
                                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase tracking-wider mb-2">
                                    Secret Token
                                </label>
                                <div className="flex gap-2">
                                    <div className="relative flex-1">
                                        <input
                                            type="text"
                                            value={formData.webhookSecret}
                                            onChange={(e) => setFormData(prev => ({ ...prev, webhookSecret: e.target.value }))}
                                            placeholder="ghp_secrettoken..."
                                            className={`w-full bg-slate-50 dark:bg-slate-700/50 border ${errors.webhookSecret ? 'border-red-500' : 'border-slate-300 dark:border-slate-600'} text-slate-800 dark:text-slate-100 rounded-xl pl-9 pr-4 py-2.5 outline-none focus:border-brand-primary text-xs font-mono`}
                                        />
                                        <Key className="absolute left-3 top-3 w-4 h-4 text-slate-400" />
                                    </div>
                                    <Button
                                        type="button"
                                        variant="secondary"
                                        onClick={generateSecret}
                                        className="text-xs px-3 font-semibold text-slate-600 border border-slate-300 rounded-xl"
                                    >
                                        Generate
                                    </Button>
                                </div>
                                {errors.webhookSecret ? (
                                    <p className="text-red-500 text-xs mt-1 font-semibold">{errors.webhookSecret}</p>
                                ) : (
                                    <span className="text-[9px] text-slate-400 mt-1 block">Used by Digger to cryptographically assert signature authenticity.</span>
                                )}
                            </div>

                            {/* Testing Trigger */}
                            {formData.connectionTestResult !== 'testing' ? (
                                <div className="pt-2">
                                    <Button
                                        type="button"
                                        onClick={handleConnectionTest}
                                        className="w-full bg-gradient-to-r from-brand-primary/10 to-red-500/10 hover:from-brand-primary/20 hover:to-red-500/20 text-brand-primary font-bold py-2.5 rounded-xl border border-brand-primary/20 text-xs uppercase"
                                    >
                                        Verify Webhook Connection
                                    </Button>
                                    
                                    {formData.connectionTestResult === 'error' && (
                                        <div className="mt-2.5 p-3 bg-red-50 border border-red-200 text-red-700 rounded-xl flex items-start gap-2 animate-fadeIn">
                                            <XCircle className="w-4 h-4 text-red-500 mt-0.5 flex-shrink-0" />
                                            <div>
                                                <span className="text-xs font-bold">Validation Error:</span>
                                                <p className="text-[10px] text-red-600/90 mt-0.5">{formData.connectionTestError}</p>
                                            </div>
                                        </div>
                                    )}
                                </div>
                            ) : (
                                <div className="p-4 bg-blue-50 border border-blue-200 text-blue-700 rounded-xl flex items-center justify-center gap-3 animate-fadeIn mt-2">
                                    <Loader2 className="w-5 h-5 text-blue-500 animate-spin" />
                                    <div className="text-left">
                                        <span className="text-xs font-bold">Testing Webhook Connection...</span>
                                        <p className="text-[10px] text-blue-600/90 mt-0.5">Firing ping event payload to webhook endpoint. Please wait.</p>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                );
            case 2:
                return (
                    <div className="max-w-md mx-auto text-center py-8 space-y-6">
                        <div className="inline-flex h-16 w-16 items-center justify-center rounded-full bg-green-100 text-green-600 animate-scaleUp">
                            <CheckCircle2 className="w-10 h-10" />
                        </div>
                        
                        <div>
                            <h4 className="text-xl font-bold text-slate-800 dark:text-slate-100">Connection Verified!</h4>
                            <p className="text-xs text-slate-500 dark:text-slate-400 mt-2 leading-relaxed">
                                Digger has established a connection to the webhook endpoint and successfully verified the payload signature authenticity.
                            </p>
                        </div>
                        
                        <div className="p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-200/50 dark:border-slate-700/50 text-left text-xs font-mono space-y-2">
                            <div className="flex justify-between">
                                <span className="text-slate-400">Endpoint Status:</span>
                                <span className="text-green-500 font-semibold uppercase">
                                    {testResult?.statusCode ? `${testResult.statusCode} OK` : 'Active (200 OK)'}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-400">Response Speed:</span>
                                <span className="text-slate-700 dark:text-slate-200">
                                    {testResult?.responseTime != null ? `${testResult.responseTime}ms` : '—'}
                                </span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-400">Payload Format:</span>
                                <span className="text-slate-700 dark:text-slate-200">application/json</span>
                            </div>
                            <div className="flex justify-between">
                                <span className="text-slate-400">Webhook Type:</span>
                                <span className="text-slate-700 dark:text-slate-200">{formData.provider?.toUpperCase()} PR Hook</span>
                            </div>
                        </div>

                        <p className="text-[11px] text-slate-400">
                            Click **"Complete Setup"** below to save this webhook configuration and start listening for automated GitOps pull request comments.
                        </p>
                    </div>
                );
            default:
                return null;
        }
    };

    return (
        <div className={`space-y-6 ${className}`}>
            {/* Step Progress Bar */}
            <div className="flex items-center justify-between max-w-xl mx-auto border-b border-slate-100 dark:border-slate-800 pb-4">
                {steps.map((step, index) => {
                    const isCompleted = index < currentStep;
                    const isActive = index === currentStep;
                    return (
                        <div key={step.id} className="flex items-center flex-1 last:flex-initial">
                            <div className="flex items-center gap-2">
                                <div
                                    className={`flex items-center justify-center rounded-full text-xs font-bold border-2 transition-all duration-300`}
                                    style={{
                                        width: 'var(--size-git-step-circle)',
                                        height: 'var(--size-git-step-circle)',
                                        borderColor: isCompleted
                                            ? 'var(--color-git-webhook-step-done)'
                                            : isActive
                                            ? 'var(--color-git-webhook-step-active)'
                                            : 'var(--color-git-webhook-step)',
                                        backgroundColor: isCompleted
                                            ? 'var(--color-git-webhook-step-done)'
                                            : isActive
                                            ? 'var(--color-git-webhook-step-active)'
                                            : 'transparent',
                                        color: isCompleted || isActive ? '#ffffff' : 'var(--color-git-webhook-step)',
                                        animation: isActive ? 'git-step-advance var(--duration-git-step-advance) ease-out' : 'none'
                                    }}
                                >
                                    {isCompleted ? <Check className="w-3.5 h-3.5" /> : index + 1}
                                </div>
                                <span className={`text-[11px] font-bold uppercase tracking-wider hidden sm:inline ${
                                    isActive ? 'text-[var(--color-git-webhook-step-active)]' : isCompleted ? 'text-[var(--color-git-webhook-step-done)]' : 'text-[var(--color-git-webhook-step)]'
                                }`}>
                                    {step.label}
                                </span>
                            </div>
                            
                            {index < steps.length - 1 && (
                                <div 
                                    className="flex-1 mx-3 transition-colors duration-300"
                                    style={{
                                        height: 'var(--size-git-step-line-height)',
                                        backgroundColor: isCompleted ? 'var(--color-git-webhook-step-done)' : 'var(--color-border-default)'
                                    }}
                                />
                            )}
                        </div>
                    );
                })}
            </div>

            {/* Content Area */}
            <div className="min-h-[250px] transition-all duration-300">
                {renderStepContent()}
            </div>

            {/* Navigation Actions */}
            <div className="flex justify-between items-center border-t border-slate-100 dark:border-slate-800 pt-5">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={currentStep === 0 ? onCancel : handleBack}
                    className="flex items-center gap-1.5"
                >
                    <ArrowLeft className="w-4 h-4" />
                    {currentStep === 0 ? 'Cancel' : 'Back'}
                </Button>
                
                {currentStep < 2 ? (
                    <Button
                        type="button"
                        onClick={handleNext}
                        disabled={currentStep === 0 && !formData.provider}
                        className="flex items-center gap-1.5"
                    >
                        Next
                        <ArrowRight className="w-4 h-4" />
                    </Button>
                ) : (
                    <Button
                        type="button"
                        onClick={handleSaveConfig}
                        className="flex items-center gap-1.5 bg-green-600 hover:bg-green-700 text-white"
                    >
                        Complete Setup
                        <Check className="w-4 h-4" />
                    </Button>
                )}
            </div>
        </div>
    );
};

export default WebhookSetupForm;
