import React from 'react';
import { X, Plus } from 'lucide-react';
import { EditorTab } from '../../types';

interface EditorTabBarProps {
  tabs: EditorTab[];
  activeTabId: string | null;
  onTabClick: (tab: EditorTab) => void;
  onTabClose: (tab: EditorTab) => void;
  onAddFile: () => void;
}

const EditorTabBar: React.FC<EditorTabBarProps> = ({
  tabs,
  activeTabId,
  onTabClick,
  onTabClose,
  onAddFile,
}) => {
  const handleTabClick = (tab: EditorTab) => {
    if (tab.isClosed) return;
    onTabClick(tab);
  };

  const handleTabClose = (e: React.MouseEvent, tab: EditorTab) => {
    e.stopPropagation();
    onTabClose(tab);
  };

  return (
    <div
      className="flex items-center h-[36px] min-h-[36px] border-b"
      style={{
        background: 'var(--color-m7-tabbar-bg)',
        borderColor: 'var(--color-m7-tabbar-border)',
      }}
      role="tablist"
      aria-label="Editor tabs"
    >
      <div className="flex items-center overflow-x-auto flex-1 scrollbar-none gap-0">
        {tabs.map((tab) => {
          if (tab.isClosed) return null;
          const isActive = tab.id === activeTabId;
          return (
            <div
              key={tab.id}
              role="tab"
              aria-selected={isActive}
              aria-label={`Tab: ${tab.file.name}`}
              tabIndex={isActive ? 0 : -1}
              onKeyDown={(e) => {
                if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') {
                  const tabList = e.currentTarget.parentElement;
                  const allTabs = tabList?.children;
                  const currentIndex = Array.from(allTabs || []).indexOf(e.currentTarget);
                  const nextIndex =
                    e.key === 'ArrowRight'
                      ? Math.min(currentIndex + 1, allTabs?.length || 0 - 1)
                      : Math.max(currentIndex - 1, 0);
                  const nextEl = allTabs?.item(nextIndex) as HTMLElement | null;
                  if (nextEl) { nextEl.focus(); }
                }
              }}
              onClick={() => handleTabClick(tab)}
              className={`
                flex items-center gap-1.5 px-3 h-full cursor-pointer select-none
                transition-colors duration-100 relative
                max-w-[200px] min-w-[80px]
                border-r border-r-transparent
              `}
              style={{
                background: isActive
                  ? 'var(--color-m7-tab-active-bg)'
                  : tab.id === activeTabId
                    ? 'var(--color-m7-tab-bg)'
                    : 'transparent',
                color: isActive
                  ? 'var(--color-m7-tab-active-text)'
                  : 'var(--color-m7-tab-text)',
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLDivElement).style.background =
                    'var(--color-m7-tab-hover-bg)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  (e.currentTarget as HTMLDivElement).style.background = 'transparent';
                }
              }}
            >
              {/* File icon (FileText from lucide) */}
              <span className="shrink-0 opacity-70" style={{ fontSize: '16px' }}>
                {tab.file.language === 'json' ? '{ }' : 'TF'}
              </span>

              {/* Tab label */}
              <span
                className="truncate text-sm font-medium"
                style={{
                  maxWidth: '120px',
                }}
              >
                {tab.file.name}
              </span>

              {/* Dirty indicator */}
              {tab.isDirty && (
                <span
                  className="shrink-0 rounded-full"
                  style={{
                    width: '6px',
                    height: '6px',
                    background: 'var(--color-m7-tab-dirty)',
                    transition: 'opacity 300ms ease-in',
                  }}
                  aria-label="Unsaved changes"
                />
              )}

              {/* Close button */}
              <button
                onClick={(e) => handleTabClose(e, tab)}
                className={`
                  shrink-0 p-0.5 rounded opacity-60 hover:opacity-100
                  flex items-center justify-center transition-opacity
                `}
                style={{
                  fontSize: '14px',
                  background: isActive
                    ? 'transparent'
                    : 'transparent',
                }}
                onMouseEnter={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background =
                    'var(--color-m7-tab-close-hover)';
                  (e.currentTarget as HTMLButtonElement).style.color =
                    'var(--color-m7-tab-close-hover-text)';
                }}
                onMouseLeave={(e) => {
                  (e.currentTarget as HTMLButtonElement).style.background = 'transparent';
                  (e.currentTarget as HTMLButtonElement).style.opacity = '0.6';
                }}
                aria-label={`Close ${tab.file.name}`}
              >
                <X size={12} />
              </button>

              {/* Active tab bottom border */}
              {isActive && (
                <div
                  className="absolute bottom-0 left-0 right-0 h-[2px]"
                  style={{
                    background: 'var(--color-m7-tab-active-border)',
                  }}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Add file button */}
      <button
        onClick={onAddFile}
        className="flex items-center justify-center p-2 shrink-0 opacity-60 hover:opacity-100 transition-opacity"
        style={{
          fontSize: '16px',
        }}
        aria-label="Add new file"
      >
        <Plus size={16} />
      </button>
    </div>
  );
};

export default EditorTabBar;
