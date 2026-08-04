import path from 'path';
import fs from 'fs';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Vite plugin to fix broken imports:
// 1. Resolves empty-string placeholder imports (`from ''`)
// 2. Resolves ./name imports from subdirectories by checking parent dirs
function fixImportsPlugin(): any {
    return {
        name: 'fix-imports-resolver',
        enforce: 'pre',
        resolveId(source, importer) {
            if (!importer) return null;

            // Handle empty string imports (placeholder imports)
            if (source === '' || source === "''" || source === '""') {
                return null;
            }

            // Handle relative imports starting with ./ or ../
            if (!source.startsWith('./') && !source.startsWith('../')) {
                return null;
            }

            const importDir = path.dirname(importer);
            const normalizedSource = source.replace(/^\.\.\//, '');
            const importName = source.replace(/^\.\.\//, '').replace(/^\.\//, '');

            // Handle known imports (store, types, constants, icons, services)
            // These are mapped to paths relative to the project root
            const KNOWN_IMPORTS: Record<string, string> = {
                'useProjectStore': 'store/useProjectStore.ts',
                'usePipelineStore': 'store/usePipelineStore.ts',
                'useProjectSettingsStore': 'store/useProjectSettingsStore.ts',
                'useAppStore': 'store/useAppStore.ts',
                'usePipelineWebSocket': 'pipelineWebSocket.ts',
                'workflowService': 'workflowService.ts',
                'getAuthHeaders': 'workflowService.ts',
                'startGeneration': 'workflowService.ts',
                'pollGenerationStatus': 'workflowService.ts',
                'downloadProject': 'workflowService.ts',
                'submitClarifyAnswer': 'workflowService.ts',
                'types': 'types.ts',
                'constants': 'constants.ts',
                'ICONS': 'icons.ts',
                'AVAILABLE_MODELS': 'constants.ts',
                'DEFAULT_MODEL': 'constants.ts',
                'API_BASE_PATH': 'constants.ts',
                // Named type imports → types.ts
                'LogEntry': 'types.ts',
                'ValidationStepLog': 'types.ts',
                'Deployment': 'types.ts',
                'DeploymentLog': 'types.ts',
                'CloudCredentials': 'types.ts',
                'CredentialStatus': 'types.ts',
                'CloudProvider': 'types.ts',
                'GeneratedFile': 'types.ts',
                'GeneratedCode': 'types.ts',
                'GenerationStatus': 'types.ts',
                'PipelinePhase': 'types.ts',
                'PhaseStatus': 'types.ts',
            };

            // Check if the import matches a known import name
            // This handles cases like: from './useProjectStore' or from '../useProjectStore'
            if (KNOWN_IMPORTS[importName]) {
                const mappedPath = path.resolve(path.dirname(importer), KNOWN_IMPORTS[importName]);
                if (fs.existsSync(mappedPath)) {
                    return mappedPath;
                }
            }

            // Try to resolve in the current directory
            const localCandidates = [
                path.join(importDir, importName),
                path.join(importDir, importName + '.ts'),
                path.join(importDir, importName + '.tsx'),
                path.join(importDir, importName, 'index.ts'),
                path.join(importDir, importName, 'index.tsx'),
            ];

            for (const candidate of localCandidates) {
                if (fs.existsSync(candidate)) {
                    return candidate;
                }
            }

            // Try to resolve in parent directories (up to 3 levels)
            for (let depth = 0; depth <= 3; depth++) {
                const parentDir = depth === 0 ? importDir : path.join(importDir, '..'.repeat(depth));

                // Check the same file names at each parent level
                for (const base of [
                    importName, importName + '.ts', importName + '.tsx',
                    importName + '/index.ts', importName + '/index.tsx',
                ]) {
                    const candidate = path.join(parentDir, base);
                    if (fs.existsSync(candidate)) {
                        return candidate;
                    }
                }

                // Check common subdirectory patterns at parent level
                for (const subDir of ['constants', 'model-config', 'ui']) {
                    const candidate = path.join(parentDir, subDir, importName);
                    if (fs.existsSync(candidate)) {
                        return candidate;
                    }
                    for (const ext of ['.ts', '.tsx']) {
                        const candidate = path.join(parentDir, subDir, importName + ext);
                        if (fs.existsSync(candidate)) {
                            return candidate;
                        }
                    }
                }
            }

            return null;
        }
    };
}

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      plugins: [
        react(),
        fixImportsPlugin(),
      ],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.MISTRAL_API_KEY': JSON.stringify(env.MISTRAL_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        },
      },
      css: {
        postcss: './postcss.config.cjs'
      },
      build: {
        rollupOptions: {
          external: ['monaco-editor'],
          output: {
            manualChunks(id) {
              if (id.includes('node_modules')) {
                return id.toString().split('node_modules/')[1].split('/')[0].toString();
              }
            }
          }
        },
        chunkSizeWarningLimit: 1024
      },
      server: {
        port: 5173,
        host: true,
        proxy: {
          '/api': {
            target: 'http://localhost:8000',
            changeOrigin: true,
            secure: false,
            ws: true,
          }
        }
      }
    };
});
