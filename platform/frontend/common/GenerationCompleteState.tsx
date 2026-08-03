import React from 'react';
import Button from '../ui/Button';

interface GenerationCompleteStateProps {
    onDeploy?: () => void;
    onDownloadZip?: () => void;
}

const GenerationCompleteState: React.FC<GenerationCompleteStateProps> = ({
    onDeploy,
    onDownloadZip,
}) => {
    const downloadZip = onDownloadZip || (() => console.log('Download ZIP'));
    const deploy = onDeploy || (() => console.log('Deploy'));

    return (
        <div className="flex items-center justify-center gap-3">
            <Button variant="secondary" size="sm" onClick={downloadZip}>
                Download ZIP
            </Button>
            <Button
                variant="primary"
                size="sm"
                onClick={deploy}
                className="bg-emerald-600 hover:bg-emerald-700 text-white border-none"
            >
                Deploy Now
            </Button>
        </div>
    );
};

export default GenerationCompleteState;
