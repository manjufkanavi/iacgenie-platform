import React, { useState, useEffect } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';
import Textarea from '../ui/Textarea';

interface IntegrationFormProps {
    onSubmit: (data: any) => void;
    onCancel: () => void;
    initialData?: any;
    isSubmitting?: boolean;
}

const IntegrationForm: React.FC<IntegrationFormProps> = ({
    onSubmit,
    onCancel,
    initialData,
    isSubmitting = false
}) => {
    const [formData, setFormData] = useState({
        name: '',
        type: 'slack',
        isActive: true,
        config: {} as Record<string, any>
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name || '',
                type: initialData.type || 'slack',
                isActive: initialData.isActive !== false,
                config: {}
            });
        }
    }, [initialData]);

    const validateForm = () => {
        const newErrors: Record<string, string> = {};

        if (!formData.name.trim()) {
            newErrors.name = 'Integration name is required';
        }

        // Type-specific validation
        switch (formData.type) {
            case 'slack':
            case 'discord':
                if (!formData.config.webhookUrl?.trim()) {
                    newErrors.webhookUrl = 'Webhook URL is required';
                } else if (!isValidUrl(formData.config.webhookUrl)) {
                    newErrors.webhookUrl = 'Please enter a valid webhook URL';
                }
                break;
            case 'webhook':
                if (!formData.config.url?.trim()) {
                    newErrors.url = 'Webhook URL is required';
                } else if (!isValidUrl(formData.config.url)) {
                    newErrors.url = 'Please enter a valid webhook URL';
                }
                break;
            case 'email':
                if (!formData.config.smtpHost?.trim()) {
                    newErrors.smtpHost = 'SMTP Host is required';
                }
                if (!formData.config.smtpPort?.trim()) {
                    newErrors.smtpPort = 'SMTP Port is required';
                }
                if (!formData.config.username?.trim()) {
                    newErrors.username = 'Username is required';
                }
                if (!formData.config.password?.trim()) {
                    newErrors.password = 'Password is required';
                }
                if (!formData.config.fromEmail?.trim()) {
                    newErrors.fromEmail = 'From Email is required';
                }
                break;
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
            onSubmit(formData);
        }
    };

    const handleInputChange = (field: string, value: any) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const handleConfigChange = (field: string, value: string) => {
        setFormData(prev => ({
            ...prev,
            config: { ...prev.config, [field]: value }
        }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const renderTypeFields = () => {
        switch (formData.type) {
            case 'slack':
                return (
                    <div className="space-y-4">
                        <Input
                            label="Slack Webhook URL"
                            id="webhookUrl"
                            value={formData.config.webhookUrl || ''}
                            onChange={(e) => handleConfigChange('webhookUrl', e.target.value)}
                            placeholder="[YOUR_SLACK_WEBHOOK_URL]"
                            error={errors.webhookUrl}
                            required
                            disabled={isSubmitting}
                            helperText="Create a webhook in your Slack workspace settings"
                        />
                        <Input
                            label="Channel (Optional)"
                            id="channel"
                            value={formData.config.channel || ''}
                            onChange={(e) => handleConfigChange('channel', e.target.value)}
                            placeholder="#general"
                            disabled={isSubmitting}
                            helperText="Default channel to send notifications to"
                        />
                    </div>
                );
            case 'discord':
                return (
                    <div className="space-y-4">
                        <Input
                            label="Discord Webhook URL"
                            id="webhookUrl"
                            value={formData.config.webhookUrl || ''}
                            onChange={(e) => handleConfigChange('webhookUrl', e.target.value)}
                            placeholder="https://discord.com/api/webhooks/123456789/abcdef..."
                            error={errors.webhookUrl}
                            required
                            disabled={isSubmitting}
                            helperText="Create a webhook in your Discord server settings"
                        />
                        <Input
                            label="Username (Optional)"
                            id="username"
                            value={formData.config.username || ''}
                            onChange={(e) => handleConfigChange('username', e.target.value)}
                            placeholder="Iacgenie Bot"
                            disabled={isSubmitting}
                            helperText="Custom username for the webhook"
                        />
                    </div>
                );
            case 'webhook':
                return (
                    <div className="space-y-4">
                        <Input
                            label="Webhook URL"
                            id="url"
                            value={formData.config.url || ''}
                            onChange={(e) => handleConfigChange('url', e.target.value)}
                            placeholder="https://api.example.com/webhook"
                            error={errors.url}
                            required
                            disabled={isSubmitting}
                        />
                        <Select
                            label="HTTP Method"
                            id="method"
                            value={formData.config.method || 'POST'}
                            onChange={(e) => handleConfigChange('method', e.target.value)}
                            disabled={isSubmitting}
                        >
                            <option value="POST">POST</option>
                            <option value="PUT">PUT</option>
                            <option value="PATCH">PATCH</option>
                        </Select>
                        <Textarea
                            label="Headers (Optional)"
                            id="headers"
                            value={formData.config.headers || ''}
                            onChange={(e) => handleConfigChange('headers', e.target.value)}
                            placeholder={`{\n  "Authorization": "Bearer token",\n  "Content-Type": "application/json"\n}`}
                            disabled={isSubmitting}
                            rows={4}
                            helperText="JSON format for custom headers"
                        />
                    </div>
                );
            case 'email':
                return (
                    <div className="space-y-4">
                        <Input
                            label="SMTP Host"
                            id="smtpHost"
                            value={formData.config.smtpHost || ''}
                            onChange={(e) => handleConfigChange('smtpHost', e.target.value)}
                            placeholder="smtp.gmail.com"
                            error={errors.smtpHost}
                            required
                            disabled={isSubmitting}
                        />
                        <Input
                            label="SMTP Port"
                            id="smtpPort"
                            value={formData.config.smtpPort || ''}
                            onChange={(e) => handleConfigChange('smtpPort', e.target.value)}
                            placeholder="587"
                            error={errors.smtpPort}
                            required
                            disabled={isSubmitting}
                        />
                        <Input
                            label="Username"
                            id="username"
                            value={formData.config.username || ''}
                            onChange={(e) => handleConfigChange('username', e.target.value)}
                            placeholder="user@example.com"
                            error={errors.username}
                            required
                            disabled={isSubmitting}
                        />
                        <Input
                            label="Password"
                            id="password"
                            type="password"
                            value={formData.config.password || ''}
                            onChange={(e) => handleConfigChange('password', e.target.value)}
                            placeholder="••••••••••••••••••••••••"
                            error={errors.password}
                            required
                            disabled={isSubmitting}
                        />
                        <Input
                            label="From Email"
                            id="fromEmail"
                            type="email"
                            value={formData.config.fromEmail || ''}
                            onChange={(e) => handleConfigChange('fromEmail', e.target.value)}
                            placeholder="notifications@example.com"
                            error={errors.fromEmail}
                            required
                            disabled={isSubmitting}
                        />
                        <Input
                            label="To Email"
                            id="toEmail"
                            type="email"
                            value={formData.config.toEmail || ''}
                            onChange={(e) => handleConfigChange('toEmail', e.target.value)}
                            placeholder="team@example.com"
                            disabled={isSubmitting}
                            helperText="Default recipient for notifications"
                        />
                    </div>
                );
            default:
                return null;
        }
    };

    const getTypeDescription = (type: string) => {
        switch (type) {
            case 'slack':
                return 'Send notifications to Slack channels';
            case 'discord':
                return 'Send notifications to Discord channels';
            case 'webhook':
                return 'Send data to external webhook endpoints';
            case 'email':
                return 'Send notifications via email';
            default:
                return '';
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <Input
                label="Integration Name"
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Production Notifications"
                error={errors.name}
                required
                disabled={isSubmitting}
            />

            <div className="space-y-4">
                <Select
                    label="Integration Type"
                    id="type"
                    value={formData.type}
                    onChange={(e) => handleInputChange('type', e.target.value)}
                    disabled={isSubmitting}
                >
                    <option value="slack">Slack</option>
                    <option value="discord">Discord</option>
                    <option value="webhook">Webhook</option>
                    <option value="email">Email</option>
                </Select>
                <p className="text-sm text-gray-500">
                    {getTypeDescription(formData.type)}
                </p>
            </div>

            <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900">Configuration</h4>
                {renderTypeFields()}
            </div>

            <div className="flex items-center space-x-3">
                <input
                    type="checkbox"
                    id="isActive"
                    checked={formData.isActive}
                    onChange={(e) => handleInputChange('isActive', e.target.checked)}
                    disabled={isSubmitting}
                    className="h-4 w-4 text-brand-primary focus:ring-brand-primary border-gray-300 rounded-xl"
                />
                <label htmlFor="isActive" className="text-sm text-gray-700">
                    Enable this integration
                </label>
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
                    {initialData ? 'Update Integration' : 'Add Integration'}
                </Button>
            </div>
        </form>
    );
};

export default IntegrationForm; 