import React from 'react';
import Button from '../ui/Button';
import { ICONS } from '.../constants';

interface GitRepositoryItemProps {
    item: any;
    onEdit: () => void;
    onDelete: () => void;
    onTest?: () => void;
}

const GitRepositoryItem: React.FC<GitRepositoryItemProps> = ({
    item,
    onEdit,
    onDelete,
    onTest
}) => {
    const getProviderIcon = () => {
        switch (item.provider) {
            case 'github':
                return ICONS.GITHUB;
            case 'gitlab':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M22.65 14.39L12 22.13 1.35 14.39a.84.84 0 0 1-.3-.94l1.22-3.78 2.44-7.51A.42.42 0 0 1 4.82 2a.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18L7.44 9.67H16.56l2.93-7.49a.42.42 0 0 1 .11-.18.43.43 0 0 1 .58 0 .42.42 0 0 1 .11.18l2.44 7.51 1.22 3.78a.84.84 0 0 1-.3.94z"/>
                    </svg>
                );
            case 'bitbucket':
                return (
                    <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="currentColor">
                        <path d="M.778 1.213a.768.768 0 00-.768.892l3.263 19.81c.084.5.515.868 1.022.873H19.26a.772.772 0 00.77-.646l3.27-20.03a.774.774 0 00-.787-.912zM14.972 15.399H9.28l-1.972-9.44h9.44z"/>
                    </svg>
                );
            default:
                return ICONS.GIT;
        }
    };

    const getProviderName = () => {
        switch (item.provider) {
            case 'github':
                return 'GitHub';
            case 'gitlab':
                return 'GitLab';
            case 'bitbucket':
                return 'Bitbucket';
            default:
                return item.provider;
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
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800">
                            {getProviderName()}
                        </span>
                    </div>
                    <div className="mt-1 flex items-center space-x-4 text-sm text-gray-500">
                        <span className="truncate">{item.url}</span>
                        <span>•</span>
                        <span>Branch: {item.branch}</span>
                    </div>
                </div>
            </div>
            
            <div className="flex items-center space-x-2">
                {onTest && (
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={onTest}
                        title="Test connection"
                    >
                        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M9 12l2 2 4-4"/>
                            <path d="M21 12c0 4.97-4.03 9-9 9s-9-4.03-9-9 4.03-9 9-9 9 4.03 9 9z"/>
                        </svg>
                    </Button>
                )}
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onEdit}
                    title="Edit repository"
                >
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="m18.5 2.5 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                </Button>
                <Button
                    variant="ghost"
                    size="sm"
                    onClick={onDelete}
                    title="Delete repository"
                >
                    {ICONS.TRASH}
                </Button>
            </div>
        </div>
    );
};

export default GitRepositoryItem; 