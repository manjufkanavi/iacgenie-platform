import React from 'react';
import { Trash2, Settings, CheckCircle, Plug } from 'lucide-react';
import Button from '../ui/Button';

interface IntegrationItemProps {
    item: any;
    onEdit: () => void;
    onDelete: () => void;
    onTest?: () => void;
}

const IntegrationItem: React.FC<IntegrationItemProps> = ({
    item,
    onEdit,
    onDelete,
    onTest
}) => {
    const getTypeIcon = () => {
        switch (item.type) {
            case 'slack':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M6 15a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm0-6a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm6 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm6 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm-6 6a2 2 0 1 1 0-4 2 2 0 0 1 0 4zm6 0a2 2 0 1 1 0-4 2 2 0 0 1 0 4z"/>
                    </svg>
                );
            case 'discord':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M20.317 4.37a19.791 19.791 0 0 0-4.885-1.515a.074.074 0 0 0-.079.037c-.21.375-.444.864-.608 1.25a18.27 18.27 0 0 0-5.487 0a12.64 12.64 0 0 0-.617-1.25a.077.077 0 0 0-.079-.037A19.736 19.736 0 0 0 3.677 4.37a.07.07 0 0 0-.032.027C.533 9.046-.32 13.58.099 18.057a.082.082 0 0 0 .031.057a19.9 19.9 0 0 0 5.993 3.03a.078.078 0 0 0 .084-.028a14.09 14.09 0 0 0 1.226-1.994a.076.076 0 0 0-.041-.106a13.107 13.107 0 0 1-1.872-.892a.077.077 0 0 1-.008-.128a10.2 10.2 0 0 0 .372-.292a.074.074 0 0 1 .077-.01c3.928 1.793 8.18 1.793 12.062 0a.074.074 0 0 1 .078.01c.12.098.246.198.373.292a.077.077 0 0 1-.006.127a12.299 12.299 0 0 1-1.873.892a.077.077 0 0 0-.041.107c.36.698.772 1.362 1.225 1.993a.076.076 0 0 0 .084.028a19.839 19.839 0 0 0 6.002-3.03a.077.077 0 0 0 .032-.054c.5-5.177-.838-9.674-3.549-13.66a.061.061 0 0 0-.031-.03zM8.02 15.33c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.956-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.956 2.418-2.157 2.418zm7.975 0c-1.183 0-2.157-1.085-2.157-2.419c0-1.333.955-2.419 2.157-2.419c1.21 0 2.176 1.096 2.157 2.42c0 1.333-.946 2.418-2.157 2.418z"/>
                    </svg>
                );
            case 'webhook':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
                        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
                    </svg>
                );
            case 'email':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/>
                        <polyline points="22,6 12,13 2,6"/>
                    </svg>
                );
            default:
                return <Plug className="w-5 h-5" />;
        }
    };

    const getTypeName = () => {
        switch (item.type) {
            case 'slack':
                return 'Slack';
            case 'discord':
                return 'Discord';
            case 'webhook':
                return 'Webhook';
            case 'email':
                return 'Email';
            default:
                return item.type;
        }
    };

    const getTypeColor = () => {
        switch (item.type) {
            case 'slack':
                return 'bg-purple-100 text-purple-800';
            case 'discord':
                return 'bg-indigo-100 text-indigo-800';
            case 'webhook':
                return 'bg-green-100 text-green-800';
            case 'email':
                return 'bg-blue-100 text-blue-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                    {getTypeIcon()}
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                            {item.name}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xl text-xs font-medium ${getTypeColor()}`}>
                            {getTypeName()}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xl text-xs font-medium ${item.isActive ? 'bg-green-100 text-green-800' : 'bg-gray-100 text-gray-800'}`}>
                            {item.isActive ? 'Active' : 'Inactive'}
                        </span>
                    </div>
                    <div className="mt-1 text-sm text-gray-500">
                        {item.type === 'slack' && 'Slack channel notifications'}
                        {item.type === 'discord' && 'Discord channel notifications'}
                        {item.type === 'webhook' && 'External webhook endpoint'}
                        {item.type === 'email' && 'Email notifications'}
                    </div>
                </div>
            </div>
            
            <div className="flex items-center space-x-2">
                {onTest && (
                    <Button
                        variant="secondary"
                        size="sm"
                        onClick={onTest}
                        title="Test integration"
                    >
                        <CheckCircle className="w-4 h-4" />
                    </Button>
                )}
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onEdit}
                    title="Edit integration"
                >
                    <Settings className="w-4 h-4" />
                </Button>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onDelete}
                    title="Delete integration"
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
};

export default IntegrationItem; 