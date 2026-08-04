import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { workflowService as workflowService } from './workflowService';
import toast from 'react-hot-toast';
import { useAppStore } from '../store/useAppStore';

const ClarifyAgentPanel: React.FC = () => {
  const deploymentMode = useAppStore(state => state.deploymentMode);
  const [name, setName] = useState('');
  const [userRequest, setUserRequest] = useState('');
  const [workspaceId, setWorkspaceId] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!userRequest.trim()) {
      toast.error('Please enter a user request');
      return;
    }

    setLoading(true);
    try {
      const response = await workflowService.createPipeline({
        name: name || `Pipeline ${new Date().toLocaleDateString()}`,
        workspace_id: workspaceId || 'default',
        user_request: userRequest,
        deploymentMode,
      });

      const pipelineId = response.data?.id;
      if (pipelineId) {
        toast.success('Pipeline started successfully');
        window.location.href = `/pipelines/${pipelineId}`;
      } else {
        toast.success('Pipeline started');
        window.location.href = '/pipelines';
      }
    } catch (err: any) {
      toast.error(err.message || 'Failed to start pipeline');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Start New Pipeline</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Describe your infrastructure requirements and the Clarify agent will refine your request
        </p>
      </div>

      {/* Form */}
      <Card padding="lg">
        <form onSubmit={handleSubmit} className="space-y-5">
          {/* Pipeline Name */}
          <div>
            <label htmlFor="pipeline-name" className="block text-sm font-medium text-gray-300 mb-1.5">
              Pipeline Name <span className="text-gray-500">(optional)</span>
            </label>
            <input
              id="pipeline-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Infrastructure Pipeline"
              className="w-full px-3 py-2.5 text-sm border border-gray-600 dark:border-slate-600 rounded-lg bg-gray-900 dark:bg-slate-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {/* Workspace ID */}
          <div>
            <label htmlFor="workspace-id" className="block text-sm font-medium text-gray-300 mb-1.5">
              Workspace ID <span className="text-gray-500">(optional)</span>
            </label>
            <input
              id="workspace-id"
              type="text"
              value={workspaceId}
              onChange={(e) => setWorkspaceId(e.target.value)}
              placeholder="default"
              className="w-full px-3 py-2.5 text-sm border border-gray-600 dark:border-slate-600 rounded-lg bg-gray-900 dark:bg-slate-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary"
            />
          </div>

          {/* User Request */}
          <div>
            <label htmlFor="user-request" className="block text-sm font-medium text-gray-300 mb-1.5">
              User Request <span className="text-red-400">*</span>
            </label>
            <textarea
              id="user-request"
              value={userRequest}
              onChange={(e) => setUserRequest(e.target.value)}
              placeholder="Describe the infrastructure you want to create. For example: 'Create an AWS VPC with 2 subnets, a security group allowing HTTP and HTTPS traffic, and an EC2 instance in the public subnet.'"
              rows={6}
              className="w-full px-3 py-2.5 text-sm border border-gray-600 dark:border-slate-600 rounded-lg bg-gray-900 dark:bg-slate-800 text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-brand-primary resize-y"
            />
          </div>

          {/* Submit */}
          <div className="flex items-center gap-3 pt-2">
            <Button type="submit" disabled={loading}>
              {loading ? 'Starting...' : 'Start Pipeline'}
            </Button>
            <Button variant="ghost" onClick={() => { window.location.href = '/pipelines'; }}>
              Cancel
            </Button>
          </div>
        </form>
      </Card>

      {/* Info */}
      <Card padding="md">
        <div className="flex items-start gap-3">
          <svg className="h-5 w-5 text-brand-primary mt-0.5 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div className="text-sm text-gray-400 dark:text-gray-500">
            <p className="font-medium text-gray-300 dark:text-gray-200 mb-1">What happens next?</p>
            <ul className="list-disc list-inside space-y-1 text-gray-400 dark:text-gray-500">
              <li>The Clarify agent will analyze your request and ask follow-up questions if needed</li>
              <li>Once clarified, the Generator agent will produce HCL code</li>
              <li>The pipeline will then run format, static analysis, and review phases</li>
            </ul>
          </div>
        </div>
      </Card>
    </div>
  );
};

export default ClarifyAgentPanel;
