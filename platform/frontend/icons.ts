/**
 * Icon mapping for frontend components.
 * Replaces placeholder `from ''` imports with actual lucide-react components.
 */
import {
    ChevronDown,
    ChevronUp,
    Folder,
    FolderOpen,
    FileText,
    Loader2,
    Settings,
    Check,
    Plus,
    FileCheck2,
    Box,
    Sparkles,
    Github,
    RefreshCw,
    GitBranch,
    Trash2,
} from 'lucide-react';

export const ICONS: Record<string, React.ComponentType<{ className?: string }>> = {
    CHEVRON_DOWN: ChevronDown,
    CHEVRON_UP: ChevronUp,
    FOLDER_OPEN: FolderOpen,
    FOLDER_CLOSED: Folder,
    FILE_ICON: FileText,
    SPINNER: Loader2,
    GITHUB: Github,
    GIT: GitBranch,
    REDEPLOY: RefreshCw,
    TRASH: Trash2,
    SETTINGS: Settings,
    CHECK: Check,
    PLUS: Plus,
    GITHUB_PUSH: FileCheck2,
    AWS_LOGO: Sparkles,
    GCP_LOGO: Sparkles,
    AZURE_LOGO: Sparkles,
    EMPTY_BOX: Box,
    GENERATOR: Sparkles,
    AUDIT_LOG: FileText,
};
