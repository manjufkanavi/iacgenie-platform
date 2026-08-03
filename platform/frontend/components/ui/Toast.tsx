import React, { useEffect } from 'react';
import { CheckCircle, Info, AlertTriangle, X } from 'lucide-react';

interface ToastProps {
  message: string;
  type?: 'success' | 'info' | 'warning';
  duration?: number;
  onClose: () => void;
  position?: 'top-right' | 'top-center' | 'bottom-right' | 'bottom-center';
}

const iconMap = {
  success: CheckCircle,
  info: Info,
  warning: AlertTriangle,
};

const bgByType: Record<string, string> = {
  success: 'bg-status-success',
  info: 'bg-status-running',
  warning: 'bg-status-escalated',
};

const Toast: React.FC<ToastProps> = ({
  message,
  type = 'info',
  duration = 3000,
  onClose,
  position = 'top-right'
}) => {
  const Icon = iconMap[type];

  useEffect(() => {
    if (duration > 0) {
      const timer = setTimeout(() => {
        onClose();
      }, duration);
      return () => clearTimeout(timer);
    }
  }, [duration, onClose]);

  const positionClasses = {
    'top-right': 'top-4 right-4',
    'top-center': 'top-4 left-1/2 -translate-x-1/2',
    'bottom-right': 'bottom-4 right-4',
    'bottom-center': 'bottom-4 left-1/2 -translate-x-1/2'
  };

  return (
    <div className={`fixed z-[var(--z-toast,500)] ${positionClasses[position]} animate-fade-in-down`}>
      <div className={`${bgByType[type]} text-white px-6 py-4 rounded-lg shadow-xl flex items-center gap-3 min-w-[250px]`}>
        <div className="flex-shrink-0">
          <Icon className="w-5 h-5" />
        </div>
        <p className="font-medium">{message}</p>
        <button
          onClick={onClose}
          className="ml-auto text-white/70 hover:text-white transition-colors focus:outline-none focus:ring-2 focus:ring-white/50 rounded"
          aria-label="Dismiss notification"
        >
          <X className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default Toast;
