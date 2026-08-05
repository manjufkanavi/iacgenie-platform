
import React, { useState } from 'react';
import Button from '../ui/Button';

interface CodePreviewProps {
  code: string;
  language: string;
}

const CodePreview: React.FC<CodePreviewProps> = ({ code, language }) => {
  const [isCopied, setIsCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className="bg-[#1F2937] rounded-b-md overflow-hidden">
        <div className="flex justify-between items-center px-4 py-2 bg-gray-900/50">
            <span className="text-xs font-semibold text-gray-400 uppercase">{language}</span>
            <Button
                variant="ghost"
                size="sm"
                onClick={handleCopy}
                className="text-gray-300 hover:text-white hover:bg-gray-700 focus:ring-gray-500"
            >
                {isCopied ? (
                    <>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                        Copied!
                    </>
                ) : (
                     <>
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4 mr-1.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                        </svg>
                        Copy
                    </>
                )}
            </Button>
        </div>
        <pre className="p-4 text-sm overflow-auto h-[450px] max-h-[60vh] text-gray-300">
            <code className={`language-${language}`}>
                {code}
            </code>
        </pre>
    </div>
  );
};

export default CodePreview;