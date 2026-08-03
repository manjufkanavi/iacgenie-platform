import React, { useState } from 'react';

type ActionVariant = 'primary' | 'danger' | 'secondary';
type ActionsBarVariant = 'default' | 'agent-actions';
type Alignment = 'left' | 'center' | 'right';

interface ActionItem {
  label: string;
  onClick: () => void;
  variant?: ActionVariant;
  icon?: React.ReactNode;
  disabled?: boolean;
}

interface ActionsBarProps {
  selectedCount?: number;
  variant?: ActionsBarVariant;
  align?: Alignment;
  actions?: ActionItem[];
  children?: React.ReactNode;
  onConfirmDestructive?: (action: ActionItem) => void;
}

const getButtonVariant = (variant?: ActionVariant): string => {
  switch (variant) {
    case 'danger':
      return 'bg-red-500 hover:bg-red-600 text-white';
    case 'primary':
      return 'bg-brand-primary hover:bg-brand-primary/90 text-white';
    default:
      return 'bg-gray-100 hover:bg-gray-200 text-gray-900 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-gray-100';
  }
};

const agentActionStyles: string = 'bg-slate-800 border border-slate-700 shadow-md';
const defaultBarStyles: string = 'bg-gray-50 border border-gray-200 rounded-lg';

const alignmentStyles: Record<Alignment, string> = {
  left: 'justify-start',
  center: 'justify-center',
  right: 'justify-end',
};

export const ActionsBar: React.FC<ActionsBarProps> = ({
  selectedCount = 0,
  variant = 'default',
  align = 'right',
  actions = [],
  children,
  onConfirmDestructive,
}) => {
  const [pendingAction, setPendingAction] = useState<ActionItem | null>(null);

  const handleActionClick = (action: ActionItem) => {
    if (action.variant === 'danger' && onConfirmDestructive) {
      setPendingAction(action);
    } else {
      action.onClick();
    }
  };

  const handleConfirm = () => {
    if (pendingAction) {
      onConfirmDestructive?.(pendingAction);
      setPendingAction(null);
    }
  };

  const handleCancel = () => {
    setPendingAction(null);
  };

  return (
    <div className={`${variant === 'agent-actions' ? agentActionStyles : defaultBarStyles} p-4 flex items-center justify-between`}>
      {selectedCount > 0 && (
        <div className="text-sm font-medium text-gray-700 dark:text-gray-200">
          {selectedCount} item{selectedCount !== 1 ? 's' : ''} selected
        </div>
      )}

      <div className={`flex items-center gap-3 ${alignmentStyles[align]}`}>
        {children}

        {actions.map((action, index) => (
          <button
            key={index}
            onClick={() => handleActionClick(action)}
            disabled={action.disabled}
            className={`inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-colors ${getButtonVariant(action.variant)} disabled:opacity-50 disabled:cursor-not-allowed`}
          >
            {action.icon}
            {action.label}
          </button>
        ))}
      </div>

      {/* Confirmation modal for destructive actions */}
      {pendingAction && (
        <div className="fixed inset-0 bg-black/50 z-[60] flex items-center justify-center p-4" onClick={handleCancel}>
          <div
            className="bg-white dark:bg-slate-800 rounded-2xl shadow-xl p-6 max-w-md w-full"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-gray-900 dark:text-gray-100 mb-2">Confirm Action</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400 mb-4">
              Are you sure you want to "{pendingAction.label}"? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                onClick={handleCancel}
                className="px-4 py-2 rounded-md text-sm font-medium bg-gray-100 hover:bg-gray-200 text-gray-900 dark:bg-slate-700 dark:hover:bg-slate-600 dark:text-gray-100"
              >
                Cancel
              </button>
              <button
                onClick={handleConfirm}
                className="px-4 py-2 rounded-md text-sm font-medium bg-red-500 hover:bg-red-600 text-white"
              >
                Confirm
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default ActionsBar;
