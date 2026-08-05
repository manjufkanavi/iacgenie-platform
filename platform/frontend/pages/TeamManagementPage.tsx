import React, { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Input from '../ui/Input';
import Modal from '../ui/Modal';
import Badge from '../ui/Badge';
import { ICONS } from '../constants.ts';
import { useAppStore } from '../store/useAppStore';
import { toast } from 'react-hot-toast';
import { teamMemberService } from '../services/teamMemberService';

interface TeamMember {
  id: string;
  email: string;
  role: 'owner' | 'admin' | 'editor' | 'viewer';
  status: 'active' | 'invited';
  name?: string;
  joinedAt?: string;
}

interface AvailableUser {
  id: string;
  email: string;
  name?: string;
}

const TeamManagementPage: React.FC = () => {
    const { currentProject } = useAppStore();
    const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
    const [availableUsers, _setAvailableUsers] = useState<AvailableUser[]>([]);
    void _setAvailableUsers;
    const [loading, setLoading] = useState(true);
    const [isInviteModalOpen, setIsInviteModalOpen] = useState(false);
    const [selectedMembers, setSelectedMembers] = useState<Set<string>>(new Set());
    const [inviteEmail, setInviteEmail] = useState('');
    const [inviteRole, setInviteRole] = useState<'owner' | 'admin' | 'editor' | 'viewer'>('viewer');
    const [searchQuery, setSearchQuery] = useState('');

    useEffect(() => {
        fetchTeamMembers();
    }, [currentProject]);

    const fetchTeamMembers = async () => {
        if (!currentProject?.id) return;
        
        setLoading(true);
        try {
            const members = await teamMemberService.listTeamMembers(currentProject.id);
            setTeamMembers(members as unknown as TeamMember[]);
        } catch (error: any) {
            toast.error(error.message || 'Failed to fetch team members');
        } finally {
            setLoading(false);
        }
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            setSelectedMembers(new Set(teamMembers.map(m => m.id)));
        } else {
            setSelectedMembers(new Set());
        }
    };

    const handleToggleMember = (id: string, checked: boolean) => {
        setSelectedMembers(prev => {
            const newSet = new Set(prev);
            if (checked) {
                newSet.add(id);
            } else {
                newSet.delete(id);
            }
            return newSet;
        });
    };

    const handleInviteMember = async () => {
        if (!currentProject?.id) {
            toast.error('Please select a project');
            return;
        }

        try {
            await teamMemberService.inviteTeamMember(currentProject.id, { email: inviteEmail, role: inviteRole });
            toast.success('Invitation sent successfully!');
            setIsInviteModalOpen(false);
            setInviteEmail('');
            fetchTeamMembers();
        } catch (error: any) {
            toast.error(error.message || 'Failed to send invitation');
        }
    };

    const handleRemoveMember = async (memberId: string) => {
        if (!currentProject?.id) return;

        try {
            await teamMemberService.removeTeamMember(currentProject.id, memberId);
            toast.success('Member removed successfully');
            fetchTeamMembers();
        } catch (error: any) {
            toast.error(error.message || 'Failed to remove member');
        }
    };

    const handleUpdateRole = async (memberId: string, newRole: TeamMember['role']) => {
        if (!currentProject?.id) return;

        try {
            await teamMemberService.updateTeamMember(currentProject.id, memberId, { role: newRole });
            toast.success('Role updated successfully');
            fetchTeamMembers();
        } catch (error: any) {
            toast.error(error.message || 'Failed to update role');
        }
    };

    const handleResendInvite = async (memberId: string) => {
        if (!currentProject?.id) return;

        try {
            // Resend invite by re-inviting the member
            const member = teamMembers.find(m => m.id === memberId);
            if (member) {
                await teamMemberService.inviteTeamMember(currentProject.id, { email: member.email, role: member.role });
                toast.success('Invitation resent successfully');
            }
        } catch (error: any) {
            toast.error(error.message || 'Failed to resend invitation');
        }
    };

    const handleRemoveSelected = async () => {
        if (!currentProject?.id || selectedMembers.size === 0) return;

        try {
            for (const memberId of selectedMembers) {
                await teamMemberService.removeTeamMember(currentProject.id, memberId);
            }
            toast.success(`${selectedMembers.size} member(s) removed successfully`);
            setSelectedMembers(new Set());
            fetchTeamMembers();
        } catch (error: any) {
            toast.error(error.message || 'Failed to remove selected members');
        }
    };

    const filteredAvailableUsers = availableUsers.filter((user: AvailableUser) =>
        user.email.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const assignAvailableUser = async (userId: string) => {
        if (!currentProject?.id) return;

        try {
            // Find the user's email from available users
            const user = availableUsers.find((u: AvailableUser) => u.id === userId);
            if (user) {
                await teamMemberService.inviteTeamMember(currentProject.id, { email: user.email, role: 'viewer' as any });
                toast.success(`${user.email} assigned to project`);
            }
        } catch (error: any) {
            toast.error(error.message || 'Failed to assign user');
        }
    };

    const getStatusBadgeVariant = (status: string) => {
        return status === 'active' ? 'success' as const : 'info' as const;
    };

    return (
        <div className="space-y-6">
            {/* Invite Member Modal */}
            <Modal isOpen={isInviteModalOpen} onClose={() => setIsInviteModalOpen(false)}>
                <div className="space-y-4">
                    <h3 className="text-lg font-medium">Invite Team Member</h3>
                    
                    <Input
                        id="invite-email-input"
                        label="Email Address"
                        type="email"
                        placeholder="user@example.com"
                        value={inviteEmail}
                        onChange={(e) => setInviteEmail(e.target.value)}
                        required
                    />

                    <div>
                        <label className="block text-sm font-medium text-slate-700 dark:text-slate-200">Role</label>
                        <select
                            className="mt-1 block w-full rounded-md border-slate-300 dark:border-slate-500 shadow-sm focus:border-brand-primary focus:ring-brand-primary"
                            value={inviteRole}
                            onChange={(e) => setInviteRole(e.target.value as TeamMember['role'])}
                        >
                            <option value="owner">Owner</option>
                            <option value="admin">Admin</option>
                            <option value="editor">Editor</option>
                            <option value="viewer">Viewer</option>
                        </select>
                    </div>

                    <div className="mt-6 flex justify-end space-x-3">
                        <Button variant="secondary" onClick={() => setIsInviteModalOpen(false)}>Cancel</Button>
                        <Button onClick={handleInviteMember} disabled={!inviteEmail}>
                            Send Invitation
                        </Button>
                    </div>
                </div>
            </Modal>

            {/* Page Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-50">Team Members</h1>
                    <p className="mt-1 text-slate-600 dark:text-slate-300">
                        Manage team access and permissions for this project.
                    </p>
                </div>
                <Button onClick={() => setIsInviteModalOpen(true)}>
                    {ICONS.PLUS}
                    <span className="ml-2">Invite Member</span>
                </Button>
            </div>

            {/* Selected Members Actions */}
            {selectedMembers.size > 0 && (
                <Card className="bg-red-50 border-red-200 flex justify-between items-center px-6 py-3">
                    <div className="text-red-800 font-medium">
                        {selectedMembers.size} member(s) selected
                    </div>
                    <Button variant="danger" onClick={handleRemoveSelected}>
                        Remove Selected
                    </Button>
                </Card>
            )}

            {/* Team Members Table */}
            <Card padding="none">
                <div className="p-4 border-b border-slate-200 dark:border-slate-600">
                    <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-50">Team Members</h2>
                </div>
                
                {loading ? (
                    <div className="p-8 text-center">
                        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-brand-primary mx-auto"></div>
                        <p className="mt-4 text-slate-600 dark:text-slate-300">Loading team members...</p>
                    </div>
                ) : (
                    <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-600">
                        <thead className="bg-slate-50 dark:bg-slate-700/50">
                            <tr>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">
                                    <input 
                                        type="checkbox" 
                                        checked={selectedMembers.size > 0 && selectedMembers.size === teamMembers.length}
                                        onChange={(e) => handleSelectAll(e.target.checked)}
                                    />
                                </th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">User</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Role</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Status</th>
                                <th className="px-6 py-3 text-left text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Joined</th>
                                <th className="px-6 py-3 text-right text-xs font-medium text-slate-500 dark:text-slate-400 uppercase tracking-wider">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="bg-white divide-y divide-slate-200 dark:divide-slate-600">
                            {teamMembers.length === 0 ? (
                                <tr>
                                    <td colSpan={6} className="px-6 py-8 text-center text-slate-500 dark:text-slate-400">
                                        No team members yet. Invite someone to get started!
                                    </td>
                                </tr>
                            ) : (
                                teamMembers.map((member) => (
                                    <tr key={member.id}>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <input 
                                                type="checkbox" 
                                                checked={selectedMembers.has(member.id)}
                                                onChange={(e) => handleToggleMember(member.id, e.target.checked)}
                                            />
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center">
                                                <div className="h-10 w-10 rounded-full bg-brand-primary/10 flex items-center justify-center text-brand-primary font-semibold">
                                                    {member.name?.charAt(0) || member.email.charAt(0).toUpperCase()}
                                                </div>
                                                <div className="ml-4">
                                                    <div className="text-sm font-medium text-slate-900 dark:text-slate-50">{member.name || 'Unknown User'}</div>
                                                    <div className="text-sm text-slate-500 dark:text-slate-400">{member.email}</div>
                                                </div>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <select
                                                value={member.role}
                                                onChange={(e) => handleUpdateRole(member.id, e.target.value as TeamMember['role'])}
                                                className={`px-2 py-1 rounded-full text-xs font-medium ${
                                                    member.role === 'owner' ? 'bg-red-100 text-red-800' :
                                                    member.role === 'admin' ? 'bg-brand-primary/10 text-brand-primary' :
                                                    member.role === 'editor' ? 'bg-blue-100 text-blue-800' :
                                                    'bg-green-100 text-green-800'
                                                }`}
                                            >
                                                <option value="owner">Owner</option>
                                                <option value="admin">Admin</option>
                                                <option value="editor">Editor</option>
                                                <option value="viewer">Viewer</option>
                                            </select>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <Badge variant={getStatusBadgeVariant(member.status)}>
                                                {member.status.charAt(0).toUpperCase() + member.status.slice(1)}
                                            </Badge>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500 dark:text-slate-400">
                                            {member.joinedAt ? new Date(member.joinedAt).toLocaleDateString() : '-'}
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                                            <div className="flex justify-end space-x-2">
                                                {member.status === 'invited' && (
                                                    <button 
                                                        onClick={() => handleResendInvite(member.id)}
                                                        className="text-brand-primary hover:text-brand-primary/80"
                                                    >
                                                        Resend Invite
                                                    </button>
                                                )}
                                                <button 
                                                    onClick={() => handleRemoveMember(member.id)}
                                                    className="text-red-600 hover:text-red-900"
                                                >
                                                    Remove
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                )}
            </Card>

            {/* Available Users Section */}
            {currentProject?.hasOwnProperty('ownerId') && (
                <Card>
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-lg font-medium text-slate-900 dark:text-slate-50">Available Users</h3>
                        <Input
                            id="search-users-input"
                            label=""
                            type="text"
                            placeholder="Search users..."
                            value={searchQuery}
                            onChange={(e) => setSearchQuery(e.target.value)}
                        />
                    </div>
                    
                    {filteredAvailableUsers.length === 0 ? (
                        <p className="text-slate-500 dark:text-slate-400 text-sm">No available users found</p>
                    ) : (
                        <div className="space-y-2">
                            {filteredAvailableUsers.map((user: AvailableUser) => (
                                <div key={user.id} className="flex items-center justify-between p-3 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
                                    <div className="flex items-center">
                                        <div className="h-8 w-8 rounded-full bg-slate-200 dark:bg-slate-600 flex items-center justify-center text-slate-600 dark:text-slate-300 text-sm font-medium">
                                            {user.name?.charAt(0) || user.email.charAt(0).toUpperCase()}
                                        </div>
                                        <div className="ml-3">
                                            <p className="text-sm font-medium text-slate-900 dark:text-slate-50">{user.name || 'Unknown User'}</p>
                                            <p className="text-xs text-slate-500 dark:text-slate-400">{user.email}</p>
                                        </div>
                                    </div>
                                    <Button 
                                        size="sm" 
                                        variant="secondary"
                                        onClick={() => assignAvailableUser(user.id)}
                                    >
                                        Assign to Project
                                    </Button>
                                </div>
                            ))}
                        </div>
                    )}
                </Card>
            )}

            {/* Usage Limit Warning */}
            {teamMembers.length > 0 && (
                <Card className="bg-blue-50 border-blue-200">
                    <div className="flex">
                        <svg className="h-5 w-5 text-blue-400 mt-0.5" viewBox="0 0 20 20" fill="currentColor">
                            <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <div className="ml-3">
                            <h3 className="text-sm font-medium text-blue-800">Team Management</h3>
                            <div className="mt-2 text-sm text-blue-700">
                                <p>Team members can access this project based on their role permissions.</p>
                            </div>
                        </div>
                    </div>
                </Card>
            )}
        </div>
    );
};

export default TeamManagementPage;