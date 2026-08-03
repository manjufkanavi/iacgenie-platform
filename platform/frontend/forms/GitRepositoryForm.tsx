import React, { useState, useEffect } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';

interface GitRepositoryFormProps {
    onSubmit: (data: any) => void;
    onCancel: () => void;
    initialData?: any;
    isSubmitting?: boolean;
}

const GitRepositoryForm: React.FC<GitRepositoryFormProps> = ({
    onSubmit,
    onCancel,
    initialData,
    isSubmitting = false
}) => {
    const [formData, setFormData] = useState({
        url: '',
        branch: 'main',
        accessToken: '',
        provider: 'github',
        enableGitOps: false,
        webhookSecret: ''
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    useEffect(() => {
        if (initialData) {
            setFormData({
                url: initialData.url || '',
                branch: initialData.branch || 'main',
                accessToken: '', // Don't populate for security
                provider: initialData.provider || 'github',
                enableGitOps: initialData.enableGitOps || false,
                webhookSecret: initialData.webhookSecret || ''
            });
        }
    }, [initialData]);

    const generateSecret = () => {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*()';
        let secret = '';
        for (let i = 0; i < 24; i++) {
            secret += chars.charAt(Math.floor(Math.random() * chars.length));
        }
        handleInputChange('webhookSecret', secret);
    };

    const validateForm = () => {
        const newErrors: Record<string, string> = {};

        if (!formData.url.trim()) {
            newErrors.url = 'Repository URL is required';
        } else if (!isValidUrl(formData.url)) {
            newErrors.url = 'Please enter a valid repository URL';
        }

        if (!formData.accessToken.trim() && !initialData) {
            newErrors.accessToken = 'Access token is required';
        }

        if (formData.enableGitOps) {
            if (!formData.webhookSecret.trim()) {
                newErrors.webhookSecret = 'Webhook secret is required';
            } else if (formData.webhookSecret.length < 16) {
                newErrors.webhookSecret = 'Secret must be at least 16 characters for security';
            }
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const isValidUrl = (url: string) => {
        try {
            new URL(url);
            return true;
        } catch {
            return false;
        }
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (validateForm()) {
            // Extract a name from URL if needed by backend, e.g., github.com/user/repo -> repo
            const name = formData.url.split('/').pop()?.replace('.git', '') || 'repository';
            onSubmit({ ...formData, name });
        }
    };

    const handleInputChange = (field: string, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">

            <Select
                label="Git Provider"
                id="provider"
                value={formData.provider}
                onChange={(e) => handleInputChange('provider', e.target.value)}
                disabled={isSubmitting}
            >
                <option value="github">GitHub</option>
                <option value="gitlab">GitLab</option>
                <option value="bitbucket">Bitbucket</option>
                <option value="azure-devops">Azure DevOps</option>
                <option value="aws-codecommit">AWS CodeCommit</option>
                <option value="gitea">Gitea</option>
                <option value="gogs">Gogs</option>
                <option value="bitbucket-server">Bitbucket Server</option>
                <option value="gerrit">Gerrit</option>
                <option value="custom">Custom Provider</option>
            </Select>

            <Input
                label="Repository URL"
                id="url"
                value={formData.url}
                onChange={(e) => handleInputChange('url', e.target.value)}
                placeholder="https://github.com/username/repository.git"
                error={errors.url}
                required
                disabled={isSubmitting}
            />

            <Input
                label="Default Branch"
                id="branch"
                value={formData.branch}
                onChange={(e) => handleInputChange('branch', e.target.value)}
                placeholder="main"
                disabled={isSubmitting}
            />

            <Input
                label="Access Token"
                id="accessToken"
                type="password"
                value={formData.accessToken}
                onChange={(e) => handleInputChange('accessToken', e.target.value)}
                placeholder="••••••••••••••••••••••••"
                error={errors.accessToken}
                required={!initialData}
                disabled={isSubmitting}
                helperText={initialData ? "Leave blank to keep existing token" : "Personal access token with repo permissions"}
            />

            <div className="border-t border-slate-200 dark:border-slate-700/60 pt-4 mt-4 space-y-4">
                <div className="flex items-start gap-3">
                    <input
                        type="checkbox"
                        id="enableGitOps"
                        checked={formData.enableGitOps}
                        onChange={(e) => handleInputChange('enableGitOps', e.target.checked)}
                        disabled={isSubmitting}
                        className="mt-1 w-4 h-4 rounded text-brand-primary focus:ring-brand-primary accent-brand-primary"
                    />
                    <div className="text-xs">
                        <label htmlFor="enableGitOps" className="font-bold text-slate-800 dark:text-slate-200 uppercase tracking-wide cursor-pointer">
                            Enable Digger GitOps (PR-driven Automation)
                        </label>
                        <p className="text-[10px] text-slate-500 mt-0.5">
                            Automatically trigger plan & apply pipelines inside your pull requests when committing generated IaC code.
                        </p>
                    </div>
                </div>

                {formData.enableGitOps && (
                    <div className="bg-slate-50 dark:bg-slate-800/40 p-4 border border-slate-200 dark:border-slate-700/50 rounded-xl space-y-4 animate-slideDown">
                        <div className="flex items-center space-x-2">
                            <span className="text-[10px] uppercase font-bold tracking-wider text-slate-400">Webhook Validation</span>
                        </div>
                        
                        <div className="space-y-3">
                            <div>
                                <label className="block text-xs font-semibold text-slate-500 dark:text-slate-400 uppercase mb-1">
                                    Webhook Secret
                                </label>
                                <div className="flex items-center space-x-2">
                                    <input
                                        type="text"
                                        value={formData.webhookSecret}
                                        onChange={(e) => handleInputChange('webhookSecret', e.target.value)}
                                        placeholder="e.g. at least 16 characters"
                                        className={`flex-1 bg-white dark:bg-slate-900 border ${
                                            errors.webhookSecret ? 'border-red-500' : 'border-slate-300 dark:border-slate-700'
                                        } text-slate-800 dark:text-slate-100 rounded-xl px-4 py-2 text-xs font-mono focus:outline-none focus:ring-2 focus:ring-brand-primary`}
                                    />
                                    <button
                                        type="button"
                                        onClick={generateSecret}
                                        className="whitespace-nowrap px-3 py-2 bg-slate-200 hover:bg-slate-300 dark:bg-slate-700 dark:hover:bg-slate-600 text-slate-700 dark:text-slate-200 rounded-xl text-xs font-bold transition-colors"
                                    >
                                        Generate
                                    </button>
                                </div>
                                {errors.webhookSecret ? (
                                    <p className="text-red-500 text-[10px] mt-1 font-semibold">{errors.webhookSecret}</p>
                                ) : (
                                    <span className="text-[9px] text-slate-400 mt-1 block">
                                        Cryptographic token used to assert webhook signature authenticity.
                                    </span>
                                )}
                            </div>
                        </div>
                    </div>
                )}
            </div>

            <div className="flex justify-end space-x-3 pt-4">
                <Button
                    type="button"
                    variant="secondary"
                    onClick={onCancel}
                    disabled={isSubmitting}
                >
                    Cancel
                </Button>
                <Button
                    type="submit"
                    isLoading={isSubmitting}
                    disabled={isSubmitting}
                >
                    {initialData ? 'Update Repository' : 'Add Repository'}
                </Button>
            </div>
        </form>
    );
};

export default GitRepositoryForm; 