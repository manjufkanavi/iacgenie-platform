import React from 'react';
import { CheckCircle, Settings, Trash2 } from 'lucide-react';
import { ModelConfig } from '../../store/useAppStore';
import Button from '../ui/Button';
import Badge from '../ui/Badge';

interface ModelConfigItemProps {
    item: ModelConfig;
    onEdit: (item: ModelConfig) => void;
    onDelete: (id: string) => void;
    onTest: (item: ModelConfig) => void;
}

const ModelConfigItem: React.FC<ModelConfigItemProps> = ({
    item,
    onEdit,
    onDelete,
    onTest
}) => {
    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    };

    const getProviderColor = (provider: string) => {
        switch (provider.toLowerCase()) {
            case 'openai':
                return 'bg-green-100 text-green-800';
            case 'mistral':
                return 'bg-purple-100 text-purple-800';
            case 'gemini':
                return 'bg-blue-100 text-blue-800';
            case 'claude':
                return 'bg-brand-primary/10 text-brand-primary';
            case 'custom':
                return 'bg-gray-100 text-gray-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    return (
        <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between">
                <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                        <h3 className="text-lg font-semibold text-gray-900">
                            {item.model_name}
                        </h3>
                        <Badge className={getProviderColor(item.provider)}>
                            {item.provider}
                        </Badge>
                        {item.secure && (
                            <Badge className="bg-green-100 text-green-800">
                                Secure
                            </Badge>
                        )}
                    </div>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm text-gray-600 mb-3">
                        <div>
                            <span className="font-medium">Base URL:</span>
                            <span className="ml-2 font-mono text-xs break-all">
                                {item.base_url}
                            </span>
                        </div>
                        <div>
                            <span className="font-medium">Max Tokens:</span>
                            <span className="ml-2">{item.max_tokens.toLocaleString()}</span>
                        </div>
                        <div>
                            <span className="font-medium">Temperature:</span>
                            <span className="ml-2">{item.temperature}</span>
                        </div>
                    </div>

                    <div className="flex items-center gap-4 text-xs text-gray-500">
                        <span>Created: {formatDate(item.createdAt)}</span>
                        <span>Updated: {formatDate(item.updatedAt)}</span>
                    </div>
                </div>

                <div className="flex items-center gap-2 ml-4">
                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onTest(item)}
                        className="flex items-center gap-1"
                    >
                        <CheckCircle className="w-4 h-4" />
                        Test
                    </Button>

                    <Button
                        size="sm"
                        variant="secondary"
                        onClick={() => onEdit(item)}
                        className="flex items-center gap-1"
                    >
                        <Settings className="w-4 h-4" />
                        Edit
                    </Button>

                    <Button
                        size="sm"
                        variant="danger"
                        onClick={() => onDelete(item.id)}
                        className="flex items-center gap-1"
                    >
                        <Trash2 className="w-4 h-4" />
                        Delete
                    </Button>
                </div>
            </div>
        </div>
    );
};

export default ModelConfigItem; 