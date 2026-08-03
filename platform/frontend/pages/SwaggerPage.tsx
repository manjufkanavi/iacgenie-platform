import React, { useState } from 'react';
import SwaggerUI from 'swagger-ui-react';
import 'swagger-ui-react/swagger-ui.css';
import Button from '../ui/Button';

const SwaggerPage: React.FC = () => {
    const [viewMode, setViewMode] = useState<'swagger' | 'static'>('swagger');

    return (
        <div className="space-y-6">
            <div className="flex items-center justify-between mb-4">
                <div className="flex space-x-2">
                    <Button
                        onClick={() => setViewMode('swagger')}
                        className={`${viewMode === 'swagger' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                    >
                        Interactive API
                    </Button>
                    <Button
                        onClick={() => setViewMode('static')}
                        className={`${viewMode === 'static' ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'}`}
                    >
                        Static Docs
                    </Button>
                </div>
            </div>
            {viewMode === 'swagger' ? (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    <SwaggerUI url="http://localhost:8000/openapi.json"
                        docExpansion="list"
                        defaultModelsExpandDepth={2}
                        defaultModelExpandDepth={2}
                        displayOperationId={false}
                        displayRequestDuration={true}
                        filter={true}
                        showExtensions={true}
                        showCommonExtensions={true}
                        tryItOutEnabled={true}
                    />
                </div>
            ) : (
                <div className="bg-white rounded-lg shadow-sm border border-gray-200">
                    <iframe
                        src="http://localhost:8000/redoc"
                        title="ReDoc API Documentation"
                        className="w-full h-[80vh] border-0 rounded-b-lg"
                        style={{ minHeight: '600px' }}
                    />
                </div>
            )}
        </div>
    );
};

export default SwaggerPage;