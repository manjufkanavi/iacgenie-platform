import * as monaco from 'monaco-editor';
import { GeneratedFile } from './types';

// ============================================================
// HCL Monaco Theme Definitions
// ============================================================

export const iacgenieHclDark: monaco.editor.IStandaloneThemeData = {
  base: 'vs-dark',
  inherit: true,
  rules: [
    { token: 'keyword', foreground: 'a78bfa' },
    { token: 'keyword.directive', foreground: 'a78bfa' },
    { token: 'keyword.control', foreground: '8b5cf6' },
    { token: 'string', foreground: '4ade80' },
    { token: 'string.unquoted', foreground: '60a5fa' },
    { token: 'comment', foreground: '6b728c' },
    { token: 'bracket', foreground: '9ca3af' },
    { token: 'bracket.special', foreground: 'fb923c' },
    { token: 'number', foreground: '22d3ee' },
    { token: 'operator', foreground: 'a8a29e' },
    { token: 'punctuation', foreground: 'a8a29e' },
    { token: 'tag', foreground: 'd97706' },
    { token: 'attribute', foreground: '22d3ee' },
    { token: 'interpolation', foreground: 'ef4444' },
    { token: 'interpolation.bracket', foreground: 'fb923c' },
    { token: 'reference', foreground: 'd97706' },
    { token: 'reference.attribute', foreground: 'd97706' },
  ],
  colors: {
    'editor.background': '#0f172a',
    'editor.foreground': '#e2e8f0',
    'editor.lineHighlightBackground': '#1e293b',
    'editor.selectionBackground': '#334155',
    'editorCursor.foreground': '#94a3b8',
    'editorWhitespace.foreground': '#334155',
    'editorLineNumber.foreground': '#475569',
    'editorIndentGuide.background': '#1e293b',
    'editorBracketMatch.background': '#7c3aed33',
    'editorBracketMatch.border': '#7c3aed',
    'editor.findMatchBackground': '#7c3aed44',
    'editor.findMatchHighlightBackground': '#7c3aed22',
    'editorInlayHint.foreground': '#94a3b8',
    'editorInlayHint.background': '#0f172a',
    'editorLink.activeForeground': '#a78bfa',
    'editorSuggestWidget.background': '#1e293b',
    'editorSuggestWidget.border': '#334155',
    'editorWidget.background': '#1e293b',
    'editorWidget.border': '#334155',
    'scrollbar.shadow': '#0f172a',
    'editorGroupHeader.tabsBackground': '#0f172a',
  },
};

export const iacgenieHclLight: monaco.editor.IStandaloneThemeData = {
  base: 'vs',
  inherit: true,
  rules: [
    { token: 'keyword', foreground: '7c3aed' },
    { token: 'keyword.directive', foreground: '7c3aed' },
    { token: 'keyword.control', foreground: '6d28d9' },
    { token: 'string', foreground: '16a34a' },
    { token: 'string.unquoted', foreground: '2563eb' },
    { token: 'comment', foreground: '6b728c' },
    { token: 'bracket', foreground: '374151' },
    { token: 'bracket.special', foreground: 'ea580c' },
    { token: 'number', foreground: '0891b2' },
    { token: 'operator', foreground: '78716c' },
    { token: 'punctuation', foreground: '78716c' },
    { token: 'tag', foreground: 'b45309' },
    { token: 'attribute', foreground: '0891b2' },
    { token: 'interpolation', foreground: 'dc2626' },
    { token: 'interpolation.bracket', foreground: 'c2410c' },
    { token: 'reference', foreground: 'b45309' },
    { token: 'reference.attribute', foreground: 'd97706' },
  ],
  colors: {
    'editor.background': '#fafafa',
    'editor.foreground': '#1e293b',
    'editor.lineHighlightBackground': '#f1f5f9',
    'editor.selectionBackground': '#fed7aa',
    'editorCursor.foreground': '#64748b',
    'editorWhitespace.foreground': '#e2e8f0',
    'editorLineNumber.foreground': '#94a3b8',
    'editorIndentGuide.background': '#e2e8f0',
    'editorBracketMatch.background': '#7c3aed33',
    'editorBracketMatch.border': '#7c3aed',
    'editor.findMatchBackground': '#7c3aed44',
    'editor.findMatchHighlightBackground': '#7c3aed22',
    'editorInlayHint.foreground': '#64748b',
    'editorInlayHint.background': '#fafafa',
    'editorLink.activeForeground': '#7c3aed',
    'editorSuggestWidget.background': '#ffffff',
    'editorSuggestWidget.border': '#e2e8f0',
    'editorWidget.background': '#ffffff',
    'editorWidget.border': '#e2e8f0',
    'scrollbar.shadow': '#e2e8f0',
    'editorGroupHeader.tabsBackground': '#fafafa',
  },
};

// ============================================================
// HCL Monarch Tokenizer
// ============================================================

export function registerHCLLanguage(): void {
  if (monaco.languages.getLanguages().find((l) => l.id === 'hcl')) {
    return;
  }

  monaco.languages.register({ id: 'hcl' });

  monaco.languages.setMonarchTokensProvider('hcl', {
    tokenPostfix: '.hcl',

    // Top-level regex patterns (used as defaults before tokenizer states)
    keywords: [
      'resource',
      'data',
      'output',
      'variable',
      'module',
      'provider',
      'terraform',
      'locals',
      'dynamic',
      'null',
      'true',
      'false',
      'if',
      'for_each',
      'else',
      'in',
    ],

    typekeywords: [
      'for',
    ],

    // Symbols used as operators
    operators: [
      '=',
      '==',
      '!=',
      '<',
      '>',
      '<=',
      '>=',
      '+',
      '-',
      '*',
      '/',
      '%',
      '&',
      '|',
      '^',
      '!',
      '~',
      '?',
      '&&',
      '||',
    ],

    // Numbers
    number: /\d+(\.\d+)?/,

    // Delimiters
    delimiters: /[{}[\]()]/,

    // Symbols for escaping
    escapes: /\\./,

    // The default token type: 'token'
    // The tokenizer can be referenced by name: stateName: [...]
    tokenizer: {
      root: [
        // Comments
        [/\/\/.*$/, 'comment'],

        // Heredoc
        [/<<\s*'?(\w+)\'?/, { token: 'tag', bracket: '@open', next: 'heredoc.$1' }],

        // Double-quote strings with escape sequences
        [/\"/, { token: 'string', bracket: '@open', next: 'string' }],

        // Interpolation
        [/=\s*/, { token: 'operator', bracket: '@open' }],
        [/\$\{/, { token: 'interpolation.bracket', bracket: '@open', next: 'interpolation' }],

        // Block labels
        [/'[^']*'/, 'string'],
        [/"[^"]*"/, 'string'],

        // Keywords
        [/\b(resource|data|output|variable|module|provider|terraform)\b/, 'keyword'],
        [/\b(locals|dynamic|for_each|else|in|if|null|true|false)\b/, 'keyword.control'],
        [/\b(for)\b/, 'typekeyword'],

        // Numbers
        [/\d+(\.\d+)?/, 'number'],

        // References (resource_type.name.attr pattern)
        [/[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*/, 'reference'],
        [/[a-zA-Z_][a-zA-Z0-9_]*\.[a-zA-Z_][a-zA-Z0-9_]*/, { token: 'reference.attribute', next: '@pop' }],

        // Directives
        [/^\s*#\s*.*/, 'keyword.directive'],

        // Operators
        [/[+*/%=&|^~!?<>=-]+/, 'operator'],

        // Brackets
        [/[{}[\](),]/, 'bracket'],

        // Punctuation
        [/[;,]/, 'punctuation'],

        // Whitespace
        [/ +/, 'white'],

        // Unquoted block labels (before = or on their own)
        [/^[a-zA-Z_][a-zA-Z0-9_]*==/, 'attribute'],
      ],

      string: [
        [/[^"\\]+/, 'string'],
        [/\\./, 'escape'],
        [/"/, { token: 'string', bracket: '@close', next: '@pop' }],
      ],

      interpolation: [
        [/\}/, { token: 'interpolation.bracket', bracket: '@close', next: '@pop' }],
        [/\$\{/, { token: 'interpolation.bracket', bracket: '@open' }],
        [/[^}]+/, 'interpolation'],
      ],

      heredoc: [
        [/./, 'string'],
      ],
    },
  });
}

// ============================================================
// Language Detection
// ============================================================

export function getLanguageFromExtension(file: GeneratedFile): string {
  const ext = file.name.split('.').pop()?.toLowerCase() ?? '';
  const langMap: Record<string, string> = {
    tf: 'hcl',
    tfvars: 'hcl',
    json: 'json',
    sh: 'shell',
    bash: 'shell',
    yaml: 'yaml',
    yml: 'yaml',
    to: 'hcl',
    tom: 'hcl',
    tfstate: 'json',
    md: 'markdown',
    txt: 'plaintext',
    py: 'python',
    js: 'javascript',
    ts: 'typescript',
    go: 'go',
  };
  return langMap[ext] ?? 'hcl';
}
