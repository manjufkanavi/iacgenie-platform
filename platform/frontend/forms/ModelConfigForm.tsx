import React, { useState, useEffect } from 'react';
import Input from '../ui/Input';
import Select from '../ui/Select';
import Button from '../ui/Button';
import SecurePasswordInput from '../ui/SecurePasswordInput';
interface ModelConfigFormData {
    projectId: string;
    provider: string;
    model_name: string;
    base_url: string;
    api_key: string;
    max_tokens: number;
    temperature: number;
}

interface ModelConfigFormProps {
    onSubmit: (data: any) => Promise<void>;
    onCancel: () => void;
    initialData?: Partial<ModelConfigFormData>;
    isSubmitting: boolean;
    projectId: string;
}

const PROVIDERS = [
    { value: 'openai', label: 'OpenAI' },
    { value: 'mistral', label: 'Mistral' },
    { value: 'anthropic', label: 'Anthropic' },
    { value: 'custom', label: 'Custom' }
];

const DEFAULT_CONFIGS = {
    openai: {
        base_url: 'https://api.openai.com/v1',
        model_name: 'gpt-4-turbo',
        max_tokens: 8192,
        temperature: 0.7
    },
    mistral: {
        base_url: 'https://api.mistral.ai/v1',
        model_name: 'mistral-large-latest',
        max_tokens: 8192,
        temperature: 0.7
    },
    anthropic: {
        base_url: 'https://api.anthropic.com/v1',
        model_name: 'claude-3-sonnet-20240229',
        max_tokens: 8192,
        temperature: 0.7
    },
    custom: {
        base_url: 'https://your-api-endpoint.com/v1',
        model_name: 'your-model-name',
        max_tokens: 8192,
        temperature: 0.7
    }
};

const ModelConfigForm: React.FC<ModelConfigFormProps> = ({
    onSubmit,
    onCancel,
    initialData,
    isSubmitting,
    projectId
}) => {
    const [formData, setFormData] = useState<Omit<ModelConfigFormData, 'projectId'>>({
        provider: initialData?.provider || 'openai',
        model_name: initialData?.model_name || '',
        base_url: initialData?.base_url || '',
        api_key: initialData?.api_key || '',
        max_tokens: initialData?.max_tokens || 8192,
        temperature: initialData?.temperature || 0.7
    });

    const [errors, setErrors] = useState<Record<string, string>>({});

    useEffect(() => {
        if (formData.provider && DEFAULT_CONFIGS[formData.provider as keyof typeof DEFAULT_CONFIGS]) {
            const defaults = DEFAULT_CONFIGS[formData.provider as keyof typeof DEFAULT_CONFIGS];
            setFormData(prev => ({
                ...prev,
                ...defaults,
                api_key: prev.api_key // Keep the API key
            }));
        }
    }, [formData.provider]);

    const validateForm = (): boolean => {
        const newErrors: Record<string, string> = {};

        if (!projectId) {
            newErrors.projectId = 'Project ID is required';
        }

        if (!formData.provider) {
            newErrors.provider = 'Provider is required';
        }

        if (!formData.model_name.trim()) {
            newErrors.model_name = 'Model name is required';
        }

        if (!formData.base_url.trim()) {
            newErrors.base_url = 'Base URL is required';
        } else {
            // Validate URL format
            try {
                new URL(formData.base_url);
            } catch {
                newErrors.base_url = 'Base URL must be a valid URL';
            }
        }

        if (!formData.api_key.trim()) {
            newErrors.api_key = 'API key is required';
        }

        if (formData.max_tokens <= 0) {
            newErrors.max_tokens = 'Max tokens must be greater than 0';
        }

        if (formData.temperature < 0 || formData.temperature > 2) {
            newErrors.temperature = 'Temperature must be between 0 and 2';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!validateForm()) {
            return;
        }

        try {
            await onSubmit({
                ...formData,
                projectId,
                secure: true
            });
        } catch (error) {
            console.error('Error submitting form:', error);
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Select
                    label="Provider"
                    id="provider"
                    value={formData.provider}
                    onChange={(e) => setFormData(prev => ({ ...prev, provider: e.target.value }))}
                    required
                >
                    {PROVIDERS.map(provider => (
                        <option key={provider.value} value={provider.value}>
                            {provider.label}
                        </option>
                    ))}
                </Select>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                    label="Model Name"
                    id="model_name"
                    value={formData.model_name}
                    onChange={(e) => setFormData(prev => ({ ...prev, model_name: e.target.value }))}
                    error={errors.model_name}
                    required
                />

                <Input
                    label="Base URL"
                    id="base_url"
                    value={formData.base_url}
                    onChange={(e) => setFormData(prev => ({ ...prev, base_url: e.target.value }))}
                    error={errors.base_url}
                    required
                />
            </div>

            <SecurePasswordInput
                label="API Key"
                id="api_key"
                value={formData.api_key}
                onChange={(e) => setFormData(prev => ({ ...prev, api_key: e.target.value }))}
                error={errors.api_key}
                required
            />

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <Input
                    label="Max Tokens"
                    id="max_tokens"
                    type="number"
                    value={formData.max_tokens}
                    onChange={(e) => setFormData(prev => ({ ...prev, max_tokens: parseInt(e.target.value) || 0 }))}
                    error={errors.max_tokens}
                    required
                />

                <Input
                    label="Temperature"
                    id="temperature"
                    type="number"
                    step="0.1"
                    min="0"
                    max="2"
                    value={formData.temperature}
                    onChange={(e) => setFormData(prev => ({ ...prev, temperature: parseFloat(e.target.value) || 0 }))}
                    error={errors.temperature}
                    required
                />
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
                    disabled={isSubmitting}
                >
                    {isSubmitting ? 'Saving...' : 'Save Configuration'}
                </Button>
            </div>
        </form>
    );
};

export default ModelConfigForm; 