import React, { useState, useEffect } from 'react';
import { Cloud, CloudRain, CloudLightning } from 'lucide-react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';
import Textarea from '../ui/Textarea';
import SecureInput from '../ui/SecureInput';
import EncryptionTrustBanner from '../ui/EncryptionTrustBanner';
import { useAppStore } from '@/store/useAppStore';

interface CloudCredentialsFormProps {
    onSubmit: (data: any) => void;
    onCancel: () => void;
    initialData?: any;
    isSubmitting?: boolean;
}

const CloudCredentialsForm: React.FC<CloudCredentialsFormProps> = ({
    onSubmit,
    onCancel,
    initialData,
    isSubmitting = false
}) => {
    const { currentProject } = useAppStore();
    const canEdit = currentProject ? useAppStore.getState().hasProjectEditAccess(currentProject.id) || useAppStore.getState().isAdmin() : true;

    const [formData, setFormData] = useState({
        name: '',
        provider: 'aws',
        region: '',
        credentials: {} as Record<string, any>
    });
    const [errors, setErrors] = useState<Record<string, string>>({});
    const [passwordStrength, setPasswordStrength] = useState<{ percent: number; label: string }>({ percent: 0, label: '' });

    useEffect(() => {
        if (initialData) {
            setFormData({
                name: initialData.name || '',
                provider: initialData.provider || 'aws',
                region: initialData.region || '',
                credentials: {}
            });
        }
    }, [initialData]);

    const validateForm = () => {
        const newErrors: Record<string, string> = {};

        if (!formData.name.trim()) {
            newErrors.name = 'Credentials name is required';
        }

        if (!formData.region.trim()) {
            newErrors.region = 'Region is required';
        }

        // Provider-specific validation
        switch (formData.provider) {
            case 'aws':
                if (!formData.credentials.accessKeyId?.trim()) {
                    newErrors.accessKeyId = 'AWS Access Key ID is required';
                } else if (!/^AKIA[0-9A-Z]{16}$/.test(formData.credentials.accessKeyId.trim())) {
                    newErrors.accessKeyId = 'Invalid AWS Access Key ID format';
                }
                if (!formData.credentials.secretAccessKey?.trim()) {
                    newErrors.secretAccessKey = 'AWS Secret Access Key is required';
                }
                break;
            case 'gcp':
                if (!formData.credentials.serviceAccountJson?.trim()) {
                    newErrors.serviceAccountJson = 'GCP Service Account JSON is required';
                }
                break;
            case 'azure':
                if (!formData.credentials.clientId?.trim()) {
                    newErrors.clientId = 'Azure Client ID is required';
                }
                if (!formData.credentials.clientSecret?.trim()) {
                    newErrors.clientSecret = 'Azure Client Secret is required';
                }
                if (!formData.credentials.subscriptionId?.trim()) {
                    newErrors.subscriptionId = 'Azure Subscription ID is required';
                }
                if (!formData.credentials.tenantId?.trim()) {
                    newErrors.tenantId = 'Azure Tenant ID is required';
                }
                break;
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (validateForm()) {
            onSubmit(formData);
        }
    };

    const handleInputChange = (field: string, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const handleCredentialChange = (field: string, value: string) => {
        const sanitized = value.trim();
        setFormData(prev => ({
            ...prev,
            credentials: { ...prev.credentials, [field]: sanitized }
        }));
        if (errors[field]) {
            setErrors(prev => ({ ...prev, [field]: '' }));
        }
    };

    const calculateStrength = (value: string) => {
        let score = 0;
        if (value.length >= 8) score++;
        if (/[A-Z]/.test(value)) score++;
        if (/[a-z]/.test(value)) score++;
        if (/[0-9]/.test(value)) score++;
        if (/[^A-Za-z0-9]/.test(value)) score++;

        const thresholds: Record<number, { percent: number; label: string }> = {
            0: { percent: 0, label: '' },
            1: { percent: 20, label: 'Weak' },
            2: { percent: 40, label: 'Fair' },
            3: { percent: 60, label: 'Fair' },
            4: { percent: 80, label: 'Strong' },
            5: { percent: 100, label: 'Excellent' },
        };
        return thresholds[score] || { percent: 0, label: '' };
    };

    const handleSecretChange = (field: string, value: string) => {
        handleCredentialChange(field, value);
        const strength = calculateStrength(value);
        setPasswordStrength(strength);
    };

    const maskKey = (key: string, visibleChars: number = 4) => {
        if (!key) return '';
        if (key.length <= visibleChars) return key;
        return key.slice(0, visibleChars) + '*'.repeat(Math.min(key.length - visibleChars, 13)) + key.slice(-3);
    };

    const renderProviderFields = () => {
        switch (formData.provider) {
            case 'aws':
                return (
                    <div className="space-y-4">
                        <Input
                            label="AWS Access Key ID"
                            id="accessKeyId"
                            value={formData.credentials.accessKeyId || ''}
                            onChange={(e) => handleCredentialChange('accessKeyId', e.target.value)}
                            placeholder="AKIAIOSFODNN7EXAMPLE"
                            error={errors.accessKeyId}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="off"
                        />
                        <SecureInput
                            label="AWS Secret Access Key"
                            id="secretAccessKey"
                            value={formData.credentials.secretAccessKey || ''}
                            onChange={(e) => handleSecretChange('secretAccessKey', e.target.value)}
                            placeholder="••••••••••••••••••••••••"
                            error={errors.secretAccessKey}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="new-password"
                            strengthBar={formData.credentials.secretAccessKey ? true : false}
                            strengthPercent={passwordStrength.percent}
                            strengthLabel={passwordStrength.label}
                        />
                    </div>
                );
            case 'gcp':
                return (
                    <div className="space-y-4">
                        <Textarea
                            label="GCP Service Account JSON"
                            id="serviceAccountJson"
                            value={formData.credentials.serviceAccountJson || ''}
                            onChange={(e) => handleCredentialChange('serviceAccountJson', e.target.value)}
                            placeholder={`{\n  "type": "service_account",\n  "project_id": "your-project-id",\n  ...\n}`}
                            error={errors.serviceAccountJson}
                            required
                            disabled={isSubmitting || !canEdit}
                            rows={8}
                            helperText="Paste your complete service account JSON key"
                        />
                    </div>
                );
            case 'azure':
                return (
                    <div className="space-y-4">
                        <Input
                            label="Azure Client ID"
                            id="clientId"
                            value={formData.credentials.clientId || ''}
                            onChange={(e) => handleCredentialChange('clientId', e.target.value)}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                            error={errors.clientId}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="off"
                        />
                        <SecureInput
                            label="Azure Client Secret"
                            id="clientSecret"
                            value={formData.credentials.clientSecret || ''}
                            onChange={(e) => handleSecretChange('clientSecret', e.target.value)}
                            placeholder="••••••••••••••••••••••••"
                            error={errors.clientSecret}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="new-password"
                            strengthBar={formData.credentials.clientSecret ? true : false}
                            strengthPercent={passwordStrength.percent}
                            strengthLabel={passwordStrength.label}
                        />
                        <Input
                            label="Azure Subscription ID"
                            id="subscriptionId"
                            value={formData.credentials.subscriptionId || ''}
                            onChange={(e) => handleCredentialChange('subscriptionId', e.target.value)}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                            error={errors.subscriptionId}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="off"
                        />
                        <Input
                            label="Azure Tenant ID"
                            id="tenantId"
                            value={formData.credentials.tenantId || ''}
                            onChange={(e) => handleCredentialChange('tenantId', e.target.value)}
                            placeholder="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
                            error={errors.tenantId}
                            required
                            disabled={isSubmitting || !canEdit}
                            autoComplete="off"
                        />
                    </div>
                );
            default:
                return null;
        }
    };

    const getProviderIcon = () => {
        const iconClassName = 'w-8 h-8';
        switch (formData.provider) {
            case 'aws':
                return <CloudLightning className={iconClassName} />;
            case 'gcp':
                return <CloudRain className={iconClassName} />;
            case 'azure':
                return <Cloud className={iconClassName} />;
            default:
                return <Cloud className={iconClassName} />;
        }
    };

    if (!canEdit) {
        return (
            <div className="space-y-6">
                <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-50 border border-amber-200 rounded-lg">
                    <span className="text-xs font-medium text-amber-700 dark:text-amber-400">Read Only</span>
                </div>
                <EncryptionTrustBanner
                    variant="info"
                    message="Credentials are encrypted with OpenBao before storage."
                    compact
                />
                <div className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Credentials Name</label>
                        <span className="block text-sm text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                            {formData.name || '—'}
                        </span>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Cloud Provider</label>
                        <span className="block text-sm text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2 capitalize">
                            {formData.provider}
                        </span>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Default Region</label>
                        <span className="block text-sm text-slate-900 dark:text-slate-50 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-2">
                            {formData.region || '—'}
                        </span>
                    </div>
                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-1.5">Credentials</label>
                        <div className="space-y-3 bg-slate-50 dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded-lg px-3 py-3">
                            {formData.provider === 'aws' && (
                                <>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Access Key ID</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">{maskKey(formData.credentials.accessKeyId || '', 4)}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Secret Access Key</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">••••••••••••••••</span>
                                    </div>
                                </>
                            )}
                            {formData.provider === 'azure' && (
                                <>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Client ID</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">{maskKey(formData.credentials.clientId || '', 8)}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Client Secret</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">••••••••••••••••</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Subscription ID</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">{maskKey(formData.credentials.subscriptionId || '', 8)}</span>
                                    </div>
                                    <div className="flex justify-between items-center text-sm">
                                        <span className="text-slate-500 dark:text-slate-400">Tenant ID</span>
                                        <span className="text-slate-900 dark:text-slate-50 font-mono">{maskKey(formData.credentials.tenantId || '', 8)}</span>
                                    </div>
                                </>
                            )}
                            {formData.provider === 'gcp' && (
                                <div className="flex justify-between items-center text-sm">
                                    <span className="text-slate-500 dark:text-slate-400">Service Account</span>
                                    <span className="text-slate-900 dark:text-slate-50">Configured</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <form onSubmit={handleSubmit} className="space-y-6">
            <EncryptionTrustBanner
                variant="info"
                message="Your credentials are encrypted with OpenBao before storage."
                compact
            />
            <Input
                label="Credentials Name"
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="Production AWS Credentials"
                error={errors.name}
                required
                disabled={isSubmitting}
            />

            <div className="space-y-4">
                <Select
                    label="Cloud Provider"
                    id="provider"
                    value={formData.provider}
                    onChange={(e) => handleInputChange('provider', e.target.value)}
                    disabled={isSubmitting}
                >
                    <option value="aws">AWS</option>
                    <option value="gcp">Google Cloud Platform</option>
                    <option value="azure">Microsoft Azure</option>
                </Select>

                <div className="flex items-center space-x-3 p-3 bg-gray-50 rounded-lg">
                    <div className="flex-shrink-0">
                        {getProviderIcon()}
                    </div>
                    <div className="text-sm text-gray-600">
                        {formData.provider === 'aws' && 'Amazon Web Services'}
                        {formData.provider === 'gcp' && 'Google Cloud Platform'}
                        {formData.provider === 'azure' && 'Microsoft Azure'}
                    </div>
                </div>
            </div>

            <Input
                label="Default Region"
                id="region"
                value={formData.region}
                onChange={(e) => handleInputChange('region', e.target.value)}
                placeholder={formData.provider === 'aws' ? 'us-east-1' : 
                           formData.provider === 'gcp' ? 'us-central1' : 
                           'eastus'}
                error={errors.region}
                required
                disabled={isSubmitting}
                helperText={`Default region for ${formData.provider.toUpperCase()} resources`}
            />

            <div className="space-y-4">
                <h4 className="text-sm font-medium text-gray-900">Credentials</h4>
                {renderProviderFields()}
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
                    {initialData ? 'Update Credentials' : 'Add Credentials'}
                </Button>
            </div>
        </form>
    );
};

export default CloudCredentialsForm; 