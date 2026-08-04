const fs = require('fs');
const path = require('path');

function walk(dir) {
  let results = [];
  const list = fs.readdirSync(dir);
  list.forEach(file => {
    const filePath = path.join(dir, file);
    const stat = fs.statSync(filePath);
    if (stat && stat.isDirectory() && !file.includes('node_modules')) {
      results = results.concat(walk(filePath));
    } else if (file.endsWith('.tsx') || file.endsWith('.ts')) {
      results.push(filePath);
    }
  });
  return results;
}

const files = walk('.');
const replacements = [
  [/\.\.\/types/g, './types'],
  [/\.\.\/constants/g, './constants'],
  [/\.\.\/services\/geminiService/g, './services/geminiService'],
  [/\.\.\/services\/authHeaders/g, './services/authHeaders'],
  [/\.\.\/store\/useAppStore/g, './store/useAppStore'],
  [/\.\.\/store\/useProjectStore/g, './store/useProjectStore'],
  [/\.\.\/store\/usePipelineStore/g, './store/usePipelineStore'],
  [/\.\.\/store\/useProjectSettingsStore/g, './store/useProjectSettingsStore'],
  [/\.\.\/hooks\/usePipelineWebSocket/g, './hooks/usePipelineWebSocket'],
  [/\.\.\/hooks\/useDeploymentLogs/g, './hooks/useDeploymentLogs'],
  [/\.\.\/common\/AppErrorBoundary/g, './common/AppErrorBoundary'],
  [/\.\.\/common\/DeploymentPreviewModal/g, './common/DeploymentPreviewModal'],
  [/\.\.\/billing\/PaymentMethodsContainer/g, './billing/PaymentMethodsContainer'],
  [/\.\.\/billing\/InvoiceHistoryTable/g, './billing/InvoiceHistoryTable'],
  [/\.\.\/pipeline\/PromptCanvas/g, './pipeline/PromptCanvas'],
  [/\.\.\/pipeline\/PipelineRail/g, './pipeline/PipelineRail'],
  [/\.\.\/pipeline\/ConversationalClarifyAgent/g, './pipeline/ConversationalClarifyAgent'],
  [/\.\.\/pipeline\/InlineReviewPanel/g, './pipeline/InlineReviewPanel'],
  [/\.\.\/pipeline\/UnifiedAgentLog/g, './pipeline/UnifiedAgentLog'],
  [/\.\.\/pipeline\/GenerativePreviewPane/g, './pipeline/GenerativePreviewPane'],
  [/\.\.\/forms\/CloudCredentialsForm/g, './forms/CloudCredentialsForm'],
  [/\.\.\/forms\/GitRepositoryForm/g, './forms/GitRepositoryForm'],
  [/\.\.\/styles\/tokens\.css/g, './styles/tokens.css'],
  [/\.\.\/index\.css/g, './index.css'],
  [/\.\.\/types/g, './types'],
  [/\.\.\/constants/g, './constants'],
];

let totalReplacements = 0;
for (const file of files) {
  let content = fs.readFileSync(file, 'utf-8');
  for (const [pattern, replacement] of replacements) {
    const matches = content.match(pattern);
    if (matches) {
      content = content.replace(pattern, replacement);
      totalReplacements += matches.length;
    }
  }
  fs.writeFileSync(file, content, 'utf-8');
}
console.log('Total replacements:', totalReplacements);
console.log('Files processed:', files.length);
