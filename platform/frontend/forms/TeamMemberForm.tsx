import React, { useState, useEffect } from 'react';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Select from '../ui/Select';

interface TeamMemberFormProps {
    onSubmit: (data: any) => void;
    onCancel: () => void;
    initialData?: any;
    isSubmitting?: boolean;
}

const TeamMemberForm: React.FC<TeamMemberFormProps> = ({
    onSubmit,
    onCancel,
    initialData,
    isSubmitting = false
}) => {
    const [formData, setFormData] = useState({
        email: '',
        name: '',
        role: 'editor',
        avatarUrl: ''
    });
    const [errors, setErrors] = useState<Record<string, string>>({});

    useEffect(() => {
        if (initialData) {
            setFormData({
                email: initialData.email || '',
                name: initialData.name || '',
                role: initialData.role || 'editor',
                avatarUrl: initialData.avatarUrl || ''
            });
        }
    }, [initialData]);

    const validateForm = () => {
        const newErrors: Record<string, string> = {};

        if (!formData.email.trim()) {
            newErrors.email = 'Email address is required';
        } else if (!isValidEmail(formData.email)) {
            newErrors.email = 'Please enter a valid email address';
        }

        if (!formData.name.trim()) {
            newErrors.name = 'Name is required';
        }

        setErrors(newErrors);
        return Object.keys(newErrors).length === 0;
    };

    const isValidEmail = (email: string) => {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
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

    const getRoleDescription = (role: string) => {
        switch (role) {
            case 'owner':
                return 'Full access to all project settings and data';
            case 'admin':
                return 'Can manage team members and project settings';
            case 'editor':
                return 'Can create and edit infrastructure code';
            case 'viewer':
                return 'Can view project and generated code only';
            default:
                return '';
        }
    };

    return (
        <form onSubmit={handleSubmit} className="space-y-4">
            <Input
                label="Email Address"
                id="email"
                type="email"
                value={formData.email}
                onChange={(e) => handleInputChange('email', e.target.value)}
                placeholder="team-member@example.com"
                error={errors.email}
                required
                disabled={isSubmitting}
                autoComplete="email"
            />

            <Input
                label="Full Name"
                id="name"
                value={formData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                placeholder="John Doe"
                error={errors.name}
                required
                disabled={isSubmitting}
                autoComplete="name"
            />

            <div className="space-y-2">
                <Select
                    label="Role"
                    id="role"
                    value={formData.role}
                    onChange={(e) => handleInputChange('role', e.target.value)}
                    disabled={isSubmitting}
                >
                    <option value="viewer">Viewer</option>
                    <option value="editor">Editor</option>
                    <option value="admin">Admin</option>
                    <option value="owner">Owner</option>
                </Select>
                <p className="text-xs text-gray-500">
                    {getRoleDescription(formData.role)}
                </p>
            </div>

            <Input
                label="Avatar URL (Optional)"
                id="avatarUrl"
                value={formData.avatarUrl}
                onChange={(e) => handleInputChange('avatarUrl', e.target.value)}
                placeholder="https://example.com/avatar.jpg"
                disabled={isSubmitting}
                helperText="URL to team member's profile picture"
            />

            <div className="bg-amber-50 border border-amber-200 rounded-xl p-4">
                <div className="flex">
                    <div className="flex-shrink-0">
                        <svg className="h-5 w-5 text-amber-500" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                    </div>
                    <div className="ml-3">
                        <h3 className="text-sm font-medium text-amber-800">
                            Invitation Process
                        </h3>
                        <div className="mt-2 text-sm text-amber-700">
                            <p>An invitation email will be sent to {formData.email || 'the team member'} with instructions to join the project.</p>
                        </div>
                    </div>
                </div>
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
                    {initialData ? 'Update Member' : 'Send Invitation'}
                </Button>
            </div>
        </form>
    );
};

export default TeamMemberForm; 