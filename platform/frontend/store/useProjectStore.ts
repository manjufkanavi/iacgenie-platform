import { create } from 'zustand';
import { projectService } from '../services/projectService';
import toast from 'react-hot-toast';

export interface ProjectMeta {
  id: string;
  name: string;
  description: string;
  updatedAt?: string | null;
}

interface ProjectStore {
  currentProjectId: string | null;
  currentProject: ProjectMeta | null;
  isLoading: boolean;
  isSaving: boolean;
  error: string | null;
  setCurrentProjectId: (id: string) => Promise<void>;
  fetchProject: (id: string) => Promise<void>;
  updateProject: (data: { name: string; description: string }) => Promise<void>;
  clearError: () => void;
}

export const useProjectStore = create<ProjectStore>((set, get) => ({
  currentProjectId: null,
  currentProject: null,
  isLoading: false,
  isSaving: false,
  error: null,

  setCurrentProjectId: async (id: string) => {
    set({ currentProjectId: id, isLoading: true, error: null });
    localStorage.setItem('currentProjectId', id);
    await get().fetchProject(id);
  },

  fetchProject: async (id: string) => {
    set({ isLoading: true, error: null });
    try {
      const project = await projectService.getProject(id);
      const meta: ProjectMeta = {
        id: project.id,
        name: project.name || '',
        description: project.description || '',
        updatedAt: project.updated_at || null,
      };
      set({ currentProject: meta, isLoading: false });
    } catch (err: any) {
      set({ currentProject: null, isLoading: false, error: err.message || 'Failed to load project' });
      toast.error('Failed to load project info');
    }
  },

  updateProject: async (data) => {
    const id = get().currentProjectId;
    if (!id) return;
    set({ isSaving: true, error: null });
    try {
      const updated = await projectService.updateProject(id, data);
      const meta: ProjectMeta = {
        id: updated.id,
        name: updated.name || '',
        description: updated.description || '',
        updatedAt: updated.updated_at || null,
      };
      set({ currentProject: meta, isSaving: false });
      toast.success('Project info updated!');
    } catch (err: any) {
      set({ isSaving: false, error: err.message || 'Failed to update project' });
      toast.error('Failed to update project');
    }
  },

  clearError: () => set({ error: null }),
}));

// On app load, hydrate from localStorage if available
const cachedId = localStorage.getItem('currentProjectId');
if (cachedId) {
  useProjectStore.getState().setCurrentProjectId(cachedId);
}
