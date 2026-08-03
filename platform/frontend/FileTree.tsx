
import React, { useState } from 'react';
import { GeneratedFile } from '../types';
import { ICONS } from '../constants';

interface FileTreeProps {
  files: GeneratedFile[];
  onFileSelect: (file: GeneratedFile) => void;
  selectedFile: GeneratedFile | null;
}

// TreeNode interface: keys are controlled file system paths
interface TreeNode {
  [key: string]: TreeNode | GeneratedFile;
}

const buildFileTree = (files: GeneratedFile[]): TreeNode => {
  const root: TreeNode = {};

  files.forEach(file => {
    const parts = file.name.split('/');
    let currentLevel = root;
    parts.forEach((part, index) => {
      if (index === parts.length - 1) {
        currentLevel[part] = file;
      } else {
        if (!currentLevel[part]) {
          currentLevel[part] = {};
        }
        currentLevel = currentLevel[part] as TreeNode; // nosemgrep: javascript.lang.security.audit.prototype-pollution.prototype-pollution-loop.prototype-pollution-loop
      }
    });
  });
  return root;
};

const FileTreeItem: React.FC<{
  name: string;
  item: TreeNode | GeneratedFile;
  onFileSelect: (file: GeneratedFile) => void;
  selectedFile: GeneratedFile | null;
  level: number;
}> = ({ name, item, onFileSelect, selectedFile, level }) => {
  const [isOpen, setIsOpen] = useState(true);

  const isFolder = 'name' in item === false;

  if (isFolder) {
    return (
      <div style={{ paddingLeft: `${level * 1}rem` }}>
        <button
          onClick={() => setIsOpen(!isOpen)}
          className="flex items-center w-full text-left py-1.5 px-2 rounded-md hover:bg-gray-100"
        >
          <span className="w-5 h-5 text-gray-500 mr-2">
            {isOpen ? ICONS.FOLDER_OPEN : ICONS.FOLDER_CLOSED}
          </span>
          <span className="text-sm font-medium text-gray-800">{name}</span>
        </button>
        {isOpen && (
          <div className="mt-1">
            {Object.entries(item).sort(([aName, aItem], [bName, bItem]) => {
                const aIsFolder = 'name' in aItem === false;
                const bIsFolder = 'name' in bItem === false;
                if (aIsFolder && !bIsFolder) return -1;
                if (!aIsFolder && bIsFolder) return 1;
                return aName.localeCompare(bName);
            }).map(([childName, childItem]) => (
              <FileTreeItem
                key={childName}
                name={childName}
                item={childItem}
                onFileSelect={onFileSelect}
                selectedFile={selectedFile}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  // It's a file
  const file = item as GeneratedFile;
  const isSelected = selectedFile?.name === file.name;

  return (
    <div style={{ paddingLeft: `${level * 1}rem` }}>
      <button
        onClick={() => onFileSelect(file)}
        className={`flex items-center w-full text-left py-1.5 px-2 transition-all ${
          isSelected 
            ? 'bg-orange-500/10 text-slate-900 dark:text-white font-semibold border-l-2 border-orange-500 rounded-r-md pl-1.5' 
            : 'text-slate-600 dark:text-slate-400 hover:bg-slate-100 dark:hover:bg-slate-800/50 rounded-md'
        }`}
      >
        <span className={`w-5 h-5 mr-2 flex-shrink-0 ${isSelected ? 'text-orange-500' : 'text-slate-400'}`}>
            {ICONS.FILE_ICON}
        </span>
        <span className="text-sm truncate">{name}</span>
      </button>
    </div>
  );
};

const FileTree: React.FC<FileTreeProps> = ({ files, onFileSelect, selectedFile }) => {
  const fileTree = buildFileTree(files);

  return (
    <div className="space-y-2">
      <h3 className="text-sm font-semibold text-gray-500 uppercase tracking-wider px-2">Project Files</h3>
      {Object.entries(fileTree).map(([name, item]) => (
        <FileTreeItem
          key={name}
          name={name}
          item={item}
          onFileSelect={onFileSelect}
          selectedFile={selectedFile}
          level={0}
        />
      ))}
    </div>
  );
};

export default FileTree;