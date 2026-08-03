import React from 'react';
import { Trash2, Settings } from 'lucide-react';
import Button from '../ui/Button';

interface TeamMemberItemProps {
    item: any;
    onEdit: () => void;
    onDelete: () => void;
}

const TeamMemberItem: React.FC<TeamMemberItemProps> = ({
    item,
    onEdit,
    onDelete
}) => {
    const getRoleColor = () => {
        switch (item.role) {
            case 'owner':
                return 'bg-purple-100 text-purple-800';
            case 'admin':
                return 'bg-red-100 text-red-800';
            case 'editor':
                return 'bg-blue-100 text-blue-800';
            case 'viewer':
                return 'bg-gray-100 text-gray-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusColor = () => {
        switch (item.status) {
            case 'active':
                return 'bg-green-100 text-green-800';
            case 'pending':
                return 'bg-yellow-100 text-yellow-800';
            case 'invited':
                return 'bg-blue-100 text-blue-800';
            default:
                return 'bg-gray-100 text-gray-800';
        }
    };

    const getStatusText = () => {
        switch (item.status) {
            case 'active':
                return 'Active';
            case 'pending':
                return 'Pending';
            case 'invited':
                return 'Invited';
            default:
                return item.status;
        }
    };

    return (
        <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
                <div className="flex-shrink-0">
                    {item.avatarUrl ? (
                        <img 
                            className="h-10 w-10 rounded-full" 
                            src={item.avatarUrl} 
                            alt={item.name}
                            onError={(e) => {
                                e.currentTarget.style.display = 'none';
                                e.currentTarget.nextElementSibling?.classList.remove('hidden');
                            }}
                        />
                    ) : null}
                    <div className={`h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center ${item.avatarUrl ? 'hidden' : ''}`}>
                        <span className="text-sm font-medium text-gray-700">
                            {(item.name || item.email || '').split(' ').map((n: string) => n[0]).join('').toUpperCase()}
                        </span>
                    </div>
                </div>
                <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2">
                        <h4 className="text-sm font-medium text-gray-900 truncate">
                            {item.name || item.email || 'Unknown User'}
                        </h4>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xl text-xs font-medium ${getRoleColor()}`}>
                            {(item.role || 'Member').charAt(0).toUpperCase() + (item.role || 'Member').slice(1)}
                        </span>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-xl text-xs font-medium ${getStatusColor()}`}>
                            {getStatusText()}
                        </span>
                    </div>
                    <div className="mt-1 text-sm text-gray-500">
                        {item.email}
                    </div>
                </div>
            </div>
            
            <div className="flex items-center space-x-2">
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onEdit}
                    title="Edit member"
                >
                    <Settings className="w-4 h-4" />
                </Button>
                <Button
                    variant="secondary"
                    size="sm"
                    onClick={onDelete}
                    title="Remove member"
                >
                    <Trash2 className="w-4 h-4" />
                </Button>
            </div>
        </div>
    );
};

export default TeamMemberItem; 