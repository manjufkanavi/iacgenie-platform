import React from 'react';
import { CheckCircle, Cloud, CloudRain, CloudLightning, Trash2, Settings } from 'lucide-react';
import Button from '../ui/Button';

interface CloudCredentialsItemProps {
    item: any;
    onEdit: () => void;
    onDelete: () => void;
    onTest?: () => void;
}

const CloudCredentialsItem: React.FC<CloudCredentialsItemProps> = ({
    item,
    onEdit,
    onDelete,
    onTest
}) => {
    const getProviderIcon = () => {
        const iconClassName = 'w-8 h-8';
        switch (item.provider) {
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

    const getProviderName = () => {
        switch (item.provider) {
            case 'aws':
                return 'Amazon Web Services';
            case 'gcp':
                return 'Google Cloud Platform';
            case 'azure':
                return 'Microsoft Azure';
            default:
                return item.provider;
        }
    };

    const getProviderColor = () => {
        switch (item.provider) {
            case 'aws':
                return 'bg-brand-primary/10 text-brand-primary';
            case 'gcp':
                return 'bg-blue-100 text-blue-800';
            case 'azure':
                return 'bg-blue-100 text-blue-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                    {getProviderIcon()}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                            {item.name}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xl text-xs font-medium ${getProviderColor()}`}>
                            {getProviderName()}
                        </span>
                    </div>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                        <span>Region: {item.region || 'Not specified'}</span>
                    </div>
                </div>
            </div>
            
            <div className="flex items-center space-x-2">
                {onTest && (
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={onTest}
                        title="Test credentials"
                    >
                        <CheckCircle className="w-4 h-4" />
                    </Button>
                )}
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onEdit}
                    title="Edit credentials"
                >
                    <Settings className="w-4 h-4" />
                </Button>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onDelete}
                    title="Delete credentials"
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
};

export default CloudCredentialsItem; 