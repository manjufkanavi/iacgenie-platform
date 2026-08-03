import React, { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import Select from '../ui/Select';
import { DiffViewer } from '../ui/DiffViewer';

interface GenerationVersion {
  id: string;
  version: number;
  createdAt: string;
  filesCount: number;
  linesCount: number;
  status: string;
}

interface DiffSummary {
  filesChanged: number;
  filesAdded: number;
  filesRemoved: number;
  linesAdded: number;
  linesRemoved: number;
}

interface DiffTabPanelProps {
  versions?: GenerationVersion[];
  onRevert?: (version: number) => void;
}

const DEFAULT_VERSIONS: GenerationVersion[] = [
  { id: 'ver_001', version: 1, createdAt: new Date('2026-03-08T10:30:00Z').toISOString(), filesCount: 8, linesCount: 245, status: 'completed' },
  { id: 'ver_002', version: 2, createdAt: new Date('2026-03-08T10:35:00Z').toISOString(), filesCount: 9, linesCount: 271, status: 'completed' },
  { id: 'ver_003', version: 3, createdAt: new Date('2026-03-08T10:40:00Z').toISOString(), filesCount: 12, linesCount: 316, status: 'completed' },
];

const MOCK_FILES = ['main.tf', 'variables.tf', 'outputs.tf', 'providers.tf'];

const MOCK_DIFF_CONTENT_LEFT = `resource "aws_eks_cluster" "cluster" {
  name     = "iacgenie-eks"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.28"

  vpc_config {
    cluster_endpoint_public_access = true
  }
}
`;

const MOCK_DIFF_CONTENT_RIGHT = `resource "aws_eks_cluster" "cluster" {
  name     = "iacgenie-eks-prod"
  role_arn = aws_iam_role.eks_cluster_role.arn
  version  = "1.29"

  vpc_config {
    cluster_endpoint_public_access = true
    subnet_ids = data.aws_subnets.cluster.ids
  }

  encryption_config {
    resource = "secrets"
    provider = "aws:kms"
  }
}

resource "aws_eks_node_group" "node_group" {
  cluster_name   = aws_eks_cluster.cluster.name
  node_group_name = "iacgenie-node-group"
  node_role_arn  = aws_iam_role.node_group_role.arn
  subnet_ids     = data.aws_subnets.cluster.ids

  scaling_config {
    desired_size = 3
    min_size     = 2
    max_size     = 10
  }
}
`;

const DiffTabPanel: React.FC<DiffTabPanelProps> = ({ versions = DEFAULT_VERSIONS, onRevert }) => {
  const [leftVersion, setLeftVersion] = useState(1);
  const [rightVersion, setRightVersion] = useState(2);
  const [selectedFile, setSelectedFile] = useState<string>('');
  const [diffSummary, setDiffSummary] = useState<DiffSummary | null>(null);

  const currentLeftVersion = versions.find(v => v.version === leftVersion);
  const currentRightVersion = versions.find(v => v.version === rightVersion);

  const handleCompare = () => {
    setDiffSummary({
      filesChanged: 3,
      filesAdded: 1,
      filesRemoved: 0,
      linesAdded: 83,
      linesRemoved: 20
    });
  };

  const handleRevert = () => {
    if (!window.confirm(`Revert to version ${leftVersion}? This will create a new version based on the selected one.`)) {
      return;
    }
    onRevert?.(leftVersion);
  };

  return (
    <div className="space-y-6">
      {/* Version Selectors */}
      <Card>
        <div className="flex items-center gap-6">
          <div className="flex-1">
            <Select
              label="Left Version"
              value={leftVersion.toString()}
              onChange={(e) => setLeftVersion(parseInt(e.target.value))}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.version}>
                  v{v.version}.0 - {new Date(v.createdAt).toLocaleString()} ({v.filesCount} files, {v.linesCount} lines)
                </option>
              ))}
            </Select>
          </div>
          <div className="text-2xl text-slate-400 dark:text-slate-500">{"↔"}</div>
          <div className="flex-1">
            <Select
              label="Right Version"
              value={rightVersion.toString()}
              onChange={(e) => setRightVersion(parseInt(e.target.value))}
            >
              {versions.map((v) => (
                <option key={v.id} value={v.version}>
                  v{v.version}.0 - {new Date(v.createdAt).toLocaleString()} ({v.filesCount} files, {v.linesCount} lines)
                </option>
              ))}
            </Select>
          </div>
          <Button variant="primary" onClick={handleCompare}>Compare</Button>
        </div>
      </Card>

      {/* Diff Summary */}
      {diffSummary && (
        <Card>
          <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Change Summary</h3>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="text-center p-4 bg-slate-50 dark:bg-slate-700/50 rounded-lg">
              <div className="text-2xl font-bold text-slate-900 dark:text-slate-50">{diffSummary.filesChanged}</div>
              <div className="text-sm text-slate-500 dark:text-slate-400">Files Changed</div>
            </div>
            <div className="text-center p-4 bg-emerald-50 dark:bg-emerald-500/10 rounded-lg">
              <div className="text-2xl font-bold text-emerald-600 dark:text-emerald-400">+{diffSummary.filesAdded}</div>
              <div className="text-sm text-emerald-600 dark:text-emerald-400">Files Added</div>
            </div>
            <div className="text-center p-4 bg-rose-50 dark:bg-rose-500/10 rounded-lg">
              <div className="text-2xl font-bold text-rose-600 dark:text-rose-400">-{diffSummary.filesRemoved}</div>
              <div className="text-sm text-rose-600 dark:text-rose-400">Files Removed</div>
            </div>
            <div className="text-center p-4 bg-blue-50 dark:bg-blue-500/10 rounded-lg">
              <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">+{diffSummary.linesAdded}/-{diffSummary.linesRemoved}</div>
              <div className="text-sm text-blue-600 dark:text-blue-400">Lines Added/Removed</div>
            </div>
          </div>
        </Card>
      )}

      {/* File List */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Files</h3>
        <div className="space-y-2">
          {MOCK_FILES.map((file) => (
            <button
              key={file}
              onClick={() => setSelectedFile(file)}
              className={`w-full flex items-center justify-between p-3 rounded-lg transition-colors ${
                selectedFile === file
                  ? 'bg-brand-primary-subtle border-2 border-brand-primary'
                  : 'hover:bg-slate-50 dark:bg-slate-700/50 border-2 border-transparent'
              }`}
            >
              <span className="text-sm font-mono text-slate-900 dark:text-slate-50">{file}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400 uppercase">OpenTofu</span>
            </button>
          ))}
        </div>
      </Card>

      {/* Diff Viewer */}
      {selectedFile && currentLeftVersion && currentRightVersion && (
        <Card>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500">{selectedFile}</h3>
            <div className="flex gap-2">
              <Button variant="secondary" size="sm">Download Diff</Button>
              {onRevert && (
                <Button variant="primary" size="sm" onClick={handleRevert}>Revert to v{leftVersion}</Button>
              )}
            </div>
          </div>
          <DiffViewer
            leftFile={{ name: selectedFile, content: MOCK_DIFF_CONTENT_LEFT }}
            rightFile={{ name: selectedFile, content: MOCK_DIFF_CONTENT_RIGHT, language: 'hcl' }}
            viewMode="inline"
          />
        </Card>
      )}

      {/* Version Timeline */}
      <Card>
        <h3 className="text-sm font-semibold text-slate-400 dark:text-slate-500 mb-4">Version History</h3>
        <div className="space-y-4">
          {versions.map((version) => (
            <div key={version.id} className="flex items-center gap-4">
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-primary text-white flex items-center justify-center font-semibold">
                {version.version}
              </div>
              <div className="flex-1">
                <div className="text-sm font-medium text-slate-900 dark:text-slate-50">Iteration {version.version}</div>
                <div className="text-xs text-slate-500 dark:text-slate-400">
                  {new Date(version.createdAt).toLocaleString()} {"•"} {version.filesCount} files {"•"} {version.linesCount} lines
                </div>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => {
                  setLeftVersion(version.version);
                  setSelectedFile('');
                }}
              >
                Compare
              </Button>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
};

export default DiffTabPanel;
