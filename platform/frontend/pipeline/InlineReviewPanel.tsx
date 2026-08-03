import React from 'react';
import { motion } from 'framer-motion';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { ShieldAlert, CheckCircle, XCircle } from 'lucide-react';

export interface InlineReviewPanelProps {
  onApprove: () => void;
  onAbort: () => void;
  isLoading?: boolean;
  refinedSpec?: any;
}

const InlineReviewPanel: React.FC<InlineReviewPanelProps> = ({
  onApprove,
  onAbort,
  isLoading = false,
  refinedSpec,
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
      className="w-full overflow-hidden"
    >
      <Card className="w-full p-6 border-amber-200 dark:border-amber-900/50 bg-amber-50/30 dark:bg-amber-950/20 mb-6 rounded-xl">
        <div className="flex items-start space-x-3 mb-6">
          <div className="mt-1 flex-shrink-0">
            <div className="w-8 h-8 rounded-full bg-amber-100 dark:bg-amber-900/50 flex items-center justify-center text-amber-600 dark:text-amber-400">
              <ShieldAlert size={18} />
            </div>
          </div>
          <div className="flex-1 w-full overflow-hidden">
            <h3 className="text-lg font-semibold text-gray-900 dark:text-gray-100">Human Review Required</h3>
            <p className="text-sm text-gray-600 dark:text-gray-400 mt-1 mb-4">
              The pipeline has paused for human review. Please verify the generated plan and approve to proceed with the execution, or abort to cancel the generation.
            </p>
            {refinedSpec && (
              <div className="mt-4 bg-gray-900 rounded-lg p-4 max-h-96 overflow-y-auto w-full">
                <h4 className="text-sm font-medium text-gray-300 mb-2">Final Specification:</h4>
                <pre className="text-xs text-gray-300 whitespace-pre-wrap font-mono break-words">
                  {typeof refinedSpec === 'string' 
                    ? (() => {
                        try {
                          return JSON.stringify(JSON.parse(refinedSpec), null, 2);
                        } catch(e) {
                          return refinedSpec;
                        }
                      })()
                    : JSON.stringify(refinedSpec, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </div>

        <div className="flex items-center justify-end space-x-3 mt-6 pt-4 border-t border-amber-100 dark:border-amber-900/30">
          <Button 
            variant="ghost" 
            onClick={onAbort} 
            disabled={isLoading}
            className="text-red-600 hover:text-red-700 hover:bg-red-50 dark:hover:bg-red-900/20"
          >
            <XCircle size={16} className="mr-2 inline" />
            Abort Pipeline
          </Button>
          <Button
            variant="primary"
            onClick={onApprove}
            disabled={isLoading}
            className="bg-emerald-600 hover:bg-emerald-700 text-white border-transparent"
          >
            {isLoading ? 'Approving...' : (
              <>
                <CheckCircle size={16} className="mr-2 inline" />
                Approve & Continue
              </>
            )}
          </Button>
        </div>
      </Card>
    </motion.div>
  );
};

export default InlineReviewPanel;
