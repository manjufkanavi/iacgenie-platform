
import React from 'react';
import { Deployment, DeploymentLog } from '../types';
import Badge from './ui/Badge';
import { getStatusVariant } from './pages/DashboardPage'; // Re-using this handy function

interface LogViewerProps {
    isOpen: boolean;
    onClose: () => void;
    deployment: Deployment | null;
    logs: DeploymentLog | null;
    isLoading: boolean;
}

const LogSection: React.FC<{ title: string, content: string | undefined }> = ({ title, content }) => {
    if (!content) return null;
    return (
        <div>
            <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-2 font-mono">{title}</h3>
            <pre className="bg-gray-950 p-4 rounded-lg text-sm text-gray-300 overflow-x-auto">
                <code>{content.trim()}</code>
            </pre>
        </div>
    );
};


const LogViewer: React.FC<LogViewerProps> = ({ isOpen, onClose, deployment, logs, isLoading }) => {
    if (!isOpen) return null;
    
    return (
        <div
            className="fixed inset-0 bg-black/60 z-40 transition-opacity"
            aria-hidden="true"
            onClick={onClose}
        >
            <div
                className="fixed inset-y-0 right-0 w-full max-w-3xl bg-gray-900 z-50 shadow-2xl flex flex-col transform transition-transform ease-in-out duration-300"
                onClick={(e) => e.stopPropagation()}
                style={{ transform: isOpen ? 'translateX(0)' : 'translateX(100%)' }}
            >
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700 flex-shrink-0">
                    <div>
                        <h2 className="text-xl font-bold text-white">{deployment?.projectName}</h2>
                        <p className="text-sm text-gray-400">Deployment Logs</p>
                    </div>
                    <button onClick={onClose} className="p-2 rounded-full text-gray-400 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-primary">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                    </button>
                </div>
                
                {/* Body */}
                <div className="flex-1 p-6 overflow-y-auto space-y-6">
                    {isLoading && <div className="text-center text-gray-400">Loading logs...</div>}
                    {!isLoading && deployment && (
                         <div className="space-y-4 bg-gray-800 p-4 rounded-xl">
                            <div className="flex flex-wrap gap-4 items-center">
                               <Badge variant={getStatusVariant(deployment.status)}>{deployment.status}</Badge>
                               <span className="text-sm text-gray-400">Provider: <span className="font-medium text-gray-200">{deployment.provider.toUpperCase()}</span></span>
                               <span className="text-sm text-gray-400">Type: <span className="font-medium text-gray-200">{deployment.type}</span></span>
                            </div>
                         </div>
                    )}
                    {!isLoading && logs && (
                        <>
                            <LogSection title="OpenTofu Plan" content={logs.plan} />
                            <LogSection title="OpenTofu Apply" content={logs.apply} />
                            <LogSection title="OpenTofu Outputs" content={logs.output} />
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default LogViewer;