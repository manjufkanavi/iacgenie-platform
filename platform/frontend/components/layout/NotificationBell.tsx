import React, { useState, useRef, useEffect } from 'react';
import { Bell, Check, Trash } from 'lucide-react';

interface AlertNotification {
  id: string;
  title: string;
  message: string;
  time: string;
  unread: boolean;
  type: 'info' | 'success' | 'warning' | 'error';
}

const NotificationBell: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const [notifications, setNotifications] = useState<AlertNotification[]>([
    {
      id: 'n1',
      title: 'Clarification Required',
      message: 'Generator Agent requested feedback on Pipeline #3842 (V2 Spec)',
      time: '3m ago',
      unread: true,
      type: 'warning',
    },
    {
      id: 'n2',
      title: 'Terraform Deploy Complete',
      message: 'Successfully updated AWS VPC architecture in stage-west-1',
      time: '1h ago',
      unread: true,
      type: 'success',
    },
    {
      id: 'n3',
      title: 'Static Analysis Warn',
      message: 'Found public security exposure (S3 bucket acl public-read) in generator.tf',
      time: '4h ago',
      unread: false,
      type: 'error',
    },
    {
      id: 'n4',
      title: 'Invoice Paid',
      message: 'Monthly invoice #TG-2026-05 was successfully paid',
      time: '1d ago',
      unread: false,
      type: 'info',
    },
  ]);

  const unreadCount = notifications.filter((n) => n.unread).length;

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleMarkAllRead = () => {
    setNotifications((prev) => prev.map((n) => ({ ...n, unread: false })));
  };

  const handleToggleRead = (id: string) => {
    setNotifications((prev) =>
      prev.map((n) => (n.id === id ? { ...n, unread: !n.unread } : n))
    );
  };

  const handleDismiss = (id: string) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };


  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        data-testid="top-bar-notifications"
        aria-label={`View notifications, ${unreadCount} unread`}
        className="relative p-2 rounded-lg text-gray-500 hover:text-gray-800 hover:bg-gray-50 border border-transparent hover:border-gray-200 transition"
      >
        <Bell className="h-5 w-5" />
        {unreadCount > 0 && (
          <span 
            data-testid="notifications-unread-count"
            className="absolute top-1.5 right-1.5 h-4 w-4 rounded-full bg-red-500 text-[10px] text-white flex items-center justify-center font-bold ring-2 ring-white"
          >
            {unreadCount}
          </span>
        )}
      </button>

      {isOpen && (
        <div 
          className="absolute right-0 mt-2 w-80 rounded-xl border border-gray-150 bg-white shadow-xl z-55 overflow-hidden py-1 animate-in fade-in slide-in-from-top-2 duration-200"
          role="menu"
        >
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-gray-100 bg-gray-50/50">
            <span className="text-sm font-semibold text-gray-700">Notifications</span>
            {unreadCount > 0 && (
              <button
                onClick={handleMarkAllRead}
                className="text-xs font-semibold text-brand-primary hover:text-brand-primary/80 flex items-center gap-1 transition"
              >
                <Check className="h-3.5 w-3.5" />
                Mark all read
              </button>
            )}
          </div>

          <div className="max-h-72 overflow-y-auto divide-y divide-gray-50">
            {notifications.map((item) => (
              <div
                key={item.id}
                className={`p-3 transition-colors relative flex items-start gap-3 hover:bg-gray-50/80 ${
                  item.unread ? 'bg-brand-primary/5' : ''
                }`}
              >
                <span className={`h-2.5 w-2.5 rounded-full mt-1.5 flex-shrink-0 transition-opacity ${
                  item.unread ? 'bg-brand-primary' : 'opacity-0'
                }`} />

                <div className="flex-1">
                  <div className="flex items-center justify-between gap-1">
                    <span className="text-xs font-bold text-gray-800 line-clamp-1">{item.title}</span>
                    <span className="text-[10px] text-gray-400 whitespace-nowrap">{item.time}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 leading-relaxed">{item.message}</p>
                  
                  <div className="flex gap-3 mt-2">
                    <button
                      onClick={() => handleToggleRead(item.id)}
                      className="text-[10px] text-gray-400 hover:text-gray-600 transition font-medium"
                    >
                      {item.unread ? 'Mark Read' : 'Mark Unread'}
                    </button>
                    <button
                      onClick={() => handleDismiss(item.id)}
                      className="text-[10px] text-red-400 hover:text-red-600 transition font-medium flex items-center gap-0.5"
                    >
                      <Trash className="h-2.5 w-2.5" /> Dismiss
                    </button>
                  </div>
                </div>
              </div>
            ))}

            {notifications.length === 0 && (
              <div className="py-8 text-center text-gray-400 italic text-xs">
                No notifications to display
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default NotificationBell;
