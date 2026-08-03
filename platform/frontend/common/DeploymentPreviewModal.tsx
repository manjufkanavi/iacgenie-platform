import React from 'react';
import Modal from '../ui/Modal';
import Card from '../ui/Card';
import Button from '../ui/Button';

interface DeploymentPreviewModalProps {
    isOpen: boolean;
    onClose: () => void;
    generationId: string;
    provider: string;
    region: string;
    resources?: Array<{
        name: string;
        type: string;
        action: 'create' | 'update' | 'delete';
    }>;
}

const DeploymentPreviewModal: React.FC<DeploymentPreviewModalProps> = ({
    isOpen,
    onClose,
    generationId,
    provider,
    region,
    resources = []
}) => {
    return (
        <Modal isOpen={isOpen} onClose={onClose} title="Review Deployment" size="2xl">
            <Card className="space-y-6">
                {/* Summary Section */}
                <div className="bg-blue-50 p-4 rounded-lg border-l-4 border-blue-500">
                    <h3 className="text-sm font-semibold text-blue-800 mb-2 flex items-center">
                        <span className="mr-2">⚠️</span>
                        Preview Mode
                    </h3>
                    <p className="text-sm text-blue-800">
                        This is a preview of the infrastructure that will be created. Review carefully before confirming deployment.
                    </p>
                </div>

                {/* Source Generation */}
                <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Source Generation</label>
                    <div className="px-3 py-2 bg-gray-50 rounded-lg text-sm font-mono truncate" title={generationId}>
                        Gen-{generationId.substring(0, 8)}...
                    </div>
                </div>

                {/* Provider Details */}
                <div className="grid grid-cols-2 gap-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Cloud Provider</label>
                        <div className="px-3 py-2 bg-gray-50 rounded-lg text-sm flex items-center">
                            {provider === 'aws' && <span className="text-brand-primary font-bold mr-2">AWS</span>}
                            {provider === 'gcp' && <span className="text-blue-500 font-bold mr-2">GCP</span>}
                            {provider === 'azure' && <span className="text-purple-500 font-bold mr-2">Azure</span>}
                            <span className="text-gray-900 capitalize">{provider}</span>
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-700 mb-1">Region</label>
                        <div className="px-3 py-2 bg-gray-50 rounded-lg text-sm text-gray-900">
                            {region}
                        </div>
                    </div>
                </div>

                {/* Resources Preview */}
                <div className="pt-4 border-t">
                    <h3 className="text-sm font-semibold text-gray-900 mb-3">Resources to be Created</h3>
                    
                    {resources.length > 0 ? (
                        <div className="bg-gray-50 rounded-lg overflow-hidden">
                            <table className="min-w-full divide-y divide-gray-200">
                                <thead className="bg-gray-100">
                                    <tr>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Resource Name</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Type</th>
                                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">Action</th>
                                    </tr>
                                </thead>
                                <tbody className="bg-white divide-y divide-gray-200">
                                    {resources.map((resource, index) => (
                                        <tr key={index}>
                                            <td className="px-4 py-2 text-sm text-gray-900">{resource.name}</td>
                                            <td className="px-4 py-2 text-sm text-gray-500">{resource.type}</td>
                                            <td className="px-4 py-2">
                                                {resource.action === 'create' && (
                                                    <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-green-100 text-green-800">
                                                        Create
                                                    </span>
                                                )}
                                                {resource.action === 'update' && (
                                                    <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-yellow-100 text-yellow-800">
                                                        Update
                                                    </span>
                                                )}
                                                {resource.action === 'delete' && (
                                                    <span className="inline-flex px-2 py-1 text-xs font-medium rounded-full bg-red-100 text-red-800">
                                                        Delete
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    ) : (
                        <div className="p-4 bg-gray-50 rounded-lg text-sm text-gray-600">
                            No specific resources defined. Review the Terraform plan for details.
                        </div>
                    )}
                </div>

                {/* Warning */}
                <div className="bg-yellow-50 p-4 rounded-lg border border-yellow-200">
                    <h4 className="text-sm font-semibold text-yellow-800 mb-2">Important:</h4>
                    <ul className="text-xs text-yellow-700 space-y-1">
                        <li>• This action will create actual cloud resources</li>
                        <li>• You will be charged for the created infrastructure</li>
                        <li>• Review your cloud provider pricing before confirming</li>
                        <li>• You can delete resources later if needed</li>
                    </ul>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-3">
                    <button
                        onClick={onClose}
                        className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 transition font-medium text-sm"
                    >
                        Cancel
                    </button>
                    <Button variant="primary" onClick={onClose}>
                        Confirm Deployment
                    </Button>
                </div>
            </Card>
        </Modal>
    );
};

export default DeploymentPreviewModal;