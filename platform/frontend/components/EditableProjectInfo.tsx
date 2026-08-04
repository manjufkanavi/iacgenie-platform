import React, { useState, useEffect } from 'react';
import Button from './ui/Button';
import EditableField from './ui/EditableField';
import { useAppStore } from './store/useAppStore';
import toast from 'react-hot-toast';
import { ICONS } from './icons';
import { useProjectStore } from './store/useProjectStore';
import EnvironmentModeSelector from './settings/EnvironmentModeSelector';
import { DollarSign, BarChart3, Tag } from 'lucide-react';
import { usePipelineStore } from './store/usePipelineStore';

interface EditableProjectInfoProps {
  readOnly?: boolean;
  onChange?: () => void;
}
const EditableProjectInfo: React.FC<EditableProjectInfoProps> = ({ readOnly = false }) => {
  const { currentProject: appProject, hasProjectEditAccess, deploymentMode, setDeploymentMode } = useAppStore();
  const projectId = appProject?.id;
  const {
    currentProject,
    isLoading,
    isSaving,
    error,
    updateProject,
    setCurrentProjectId,
    clearError,
  } = useProjectStore();
  const activePipeline = usePipelineStore((s) => s.activePipeline);

  const [isEditing, setIsEditing] = useState(false);
  const [formData, setFormData] = useState({ name: '', description: '' });
  const [originalData, setOriginalData] = useState({ name: '', description: '' });
  const [hydrated, setHydrated] = useState(false);

  // Hydrate project info from store on mount and when projectId changes
  useEffect(() => {
    if (!projectId) return;
    setCurrentProjectId(projectId).then(() => setHydrated(true));
  }, [projectId, setCurrentProjectId]);

  // Sync form state with store
  useEffect(() => {
    if (currentProject) {
      setFormData({ name: currentProject.name || '', description: currentProject.description || '' });
      setOriginalData({ name: currentProject.name || '', description: currentProject.description || '' });
    }
  }, [currentProject]);

  // Show error toast if error in store
  useEffect(() => {
    if (error) {
      toast.error(error);
      clearError();
    }
  }, [error, clearError]);

  if (!projectId) {
    return (
      <div className="text-center py-8">
        <p className="text-gray-500 mb-4">No project selected</p>
        <p className="text-sm text-gray-400">Please create a project first</p>
      </div>
    );
  }

  if (!hasProjectEditAccess(projectId)) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 font-semibold">You do not have permission to edit this project. Only owners and admins can modify project info.</p>
        <EditableField label="Project Name" value={formData.name} isEditing={false} type="text" id="project-name" onChange={() => {}} />
        <EditableField label="Description" value={formData.description} isEditing={false} type="textarea" id="project-description" onChange={() => {}} />
      </div>
    );
  }

  if (readOnly) {
    return (
      <div className="space-y-6">
        <EditableField label="Project Name" value={formData.name} isEditing={false} type="text" id="project-name" onChange={() => {}} />
        <EditableField label="Description" value={formData.description} isEditing={false} type="textarea" id="project-description" onChange={() => {}} />
      </div>
    );
  }

  const renderCompactCostCard = () => {
    if (deploymentMode === 'aws') {
      return (
        <div className="border border-orange-200 dark:border-orange-950 bg-orange-50/50 dark:bg-orange-950/20 rounded-xl p-4 space-y-3 animate-[console-log-enter_150ms_ease-out]">
          <div className="flex items-center gap-2 text-orange-600 dark:text-orange-400">
            <DollarSign className="w-4.5 h-4.5 flex-shrink-0" />
            <h4 className="text-xs font-bold uppercase tracking-wider font-sans">Cost Estimate</h4>
          </div>
          <div className="text-xs space-y-1 font-sans text-slate-600 dark:text-slate-300">
            <div>Current Mode: <strong className="text-slate-800 dark:text-slate-100 font-bold">AWS (Production)</strong></div>
            <div>Estimated Cost (Last 7 Days): <span className="font-mono font-bold text-slate-800 dark:text-slate-100">$142.53</span></div>
            <div className="text-slate-500 dark:text-slate-400 font-semibold pt-1">
              Switch to LocalStack to preview costs before real deploy.
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button
              onClick={() => setDeploymentMode('localstack')}
              className="px-3 py-1.5 bg-brand-primary text-white text-[10px] font-sans font-extrabold uppercase tracking-wider rounded-lg hover:bg-brand-primary-hover transition cursor-pointer"
            >
              Switch to LocalStack
            </button>
            <button
              onClick={() => useAppStore.getState().navigate('pipeline-dashboard')}
              className="px-3 py-1.5 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-[10px] font-sans font-extrabold uppercase tracking-wider rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              View Full Cost Breakdown -&gt;
            </button>
          </div>
        </div>
      );
    }

    if (deploymentMode === 'localstack') {
      return (
        <div className="border border-teal-200 dark:border-teal-950 bg-teal-50/20 dark:bg-teal-950/10 rounded-xl p-4 space-y-3 animate-[console-log-enter_150ms_ease-out]">
          <div className="flex items-center gap-2 text-teal-600 dark:text-teal-400">
            <BarChart3 className="w-4.5 h-4.5 flex-shrink-0" />
            <h4 className="text-xs font-bold uppercase tracking-wider font-sans">Cost Estimate</h4>
          </div>
          <div className="text-xs space-y-1 font-sans text-slate-650 dark:text-slate-300">
            <div>Current Mode: <strong className="text-slate-800 dark:text-slate-100 font-bold">LocalStack (Simulation)</strong></div>
            <div>Estimated Cost (Last 7 Days): <span className="font-mono font-bold text-slate-800 dark:text-slate-100">$0.00</span></div>
            <div>Real AWS Equivalent: <span className="font-mono font-bold text-slate-800 dark:text-slate-100">$22.97</span></div>
            <div className="flex items-center gap-1.5 mt-1 select-none">
              Savings:{' '}
              <span className="px-2 py-0.5 bg-status-success-bg text-status-success-text border border-status-success-border text-[10px] font-bold rounded-full inline-flex items-center gap-1">
                <Tag className="w-3.5 h-3.5 animate-pulse-subtle" />
                $22.95 (97%)
              </span>
            </div>
          </div>
          <div className="pt-2">
            <button
              onClick={() => useAppStore.getState().navigate('pipeline-dashboard')}
              className="px-3 py-1.5 border border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-300 text-[10px] font-sans font-extrabold uppercase tracking-wider rounded-lg hover:bg-slate-50 dark:hover:bg-slate-800 transition cursor-pointer"
            >
              View Full Cost Breakdown -&gt;
            </button>
          </div>
        </div>
      );
    }

    // Offline active
    return (
      <div className="border border-slate-200 dark:border-slate-750 bg-slate-50/50 dark:bg-slate-900/20 rounded-xl p-4 space-y-2 animate-[console-log-enter_150ms_ease-out]">
        <div className="flex items-center gap-2 text-slate-500 dark:text-slate-400">
          <DollarSign className="w-4.5 h-4.5 flex-shrink-0" />
          <h4 className="text-xs font-bold uppercase tracking-wider font-sans">Cost Estimate</h4>
        </div>
        <div className="text-xs space-y-1 font-sans text-slate-650 dark:text-slate-300">
          <div>Current Mode: <strong className="text-slate-800 dark:text-slate-100 font-bold">Offline (Manual Review)</strong></div>
          <div className="font-semibold text-slate-500">No automated deployment. No costs incurred.</div>
          <div className="text-slate-450 dark:text-slate-450 mt-1">Deploy via `tofu apply` to see real AWS costs.</div>
        </div>
      </div>
    );
  };

  const isModified = formData.name !== originalData.name || formData.description !== originalData.description;

  const handleEdit = () => setIsEditing(true);
  const handleCancel = () => {
    setFormData(originalData);
    setIsEditing(false);
  };

  const handleSave = async () => {
    if (!formData.name.trim()) {
      toast.error('Project name is required');
      return;
    }
    await updateProject({ name: formData.name, description: formData.description });
    setIsEditing(false);
  };

  if (!hydrated || isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <span className="animate-spin mr-2">{ICONS.SPINNER}</span>
        <span className="text-gray-500">Loading project info...</span>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <EditableField
        label="Project Name"
        value={formData.name}
        isEditing={isEditing}
        onChange={(value) => setFormData(prev => ({ ...prev, name: value }))}
        type="text"
        placeholder="Enter project name"
        required={true}
        id="project-name"
      />
      <EditableField
        label="Description"
        value={formData.description}
        isEditing={isEditing}
        onChange={(value) => setFormData(prev => ({ ...prev, description: value }))}
        type="textarea"
        textareaRows={3}
        placeholder="Enter project description"
        id="project-description"
      />
      {!isEditing && (
        <div className="border-t border-gray-200 dark:border-slate-750 pt-6 space-y-6">
          <div>
            <h3 className="text-sm font-bold text-slate-800 dark:text-slate-100 uppercase tracking-wider">
              Deployment Target
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 mt-1 leading-relaxed">
              Select where your Infrastructure-as-Code will be applied. Cost estimation is available for LocalStack mode.
            </p>
          </div>

          <EnvironmentModeSelector
            mode={deploymentMode}
            onModeChange={setDeploymentMode}
            disabled={activePipeline?.status === 'running'}
          />

          {renderCompactCostCard()}
        </div>
      )}

      <div className="flex justify-end pt-4 border-t border-gray-200 space-x-3">
        {!isEditing ? (
          <Button
            onClick={handleEdit}
            variant="secondary"
            className="flex items-center space-x-2 hover:bg-gray-100 transition-colors duration-200"
          >
            <span className="w-4 h-4">{ICONS.SETTINGS}</span>
            <span>Modify Project Info</span>
          </Button>
        ) : (
          <>
            <Button
              onClick={handleCancel}
              variant="secondary"
              disabled={isSaving}
              className="transition-all duration-200 hover:bg-gray-100"
            >
              Cancel
            </Button>
            <Button
              onClick={handleSave}
              variant="primary"
              disabled={isSaving || !isModified || !formData.name.trim()}
              className="flex items-center space-x-2 transition-all duration-200"
            >
              {isSaving ? (
                <>
                  <span className="w-4 h-4 animate-spin">{ICONS.SPINNER}</span>
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <span className="w-4 h-4">{ICONS.CHECK}</span>
                  <span>Save Changes</span>
                </>
              )}
            </Button>
          </>
        )}
      </div>
    </div>
  );
};

export default EditableProjectInfo; 