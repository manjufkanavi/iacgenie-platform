import path from 'path';
import fs from 'fs';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';

// Vite plugin to fix broken imports:
// 1. Resolves empty-string placeholder imports (`from ''`)
// 2. Resolves ./name imports from subdirectories by checking parent dirs
// 3. Does NOT interfere with node_modules imports or directory imports
function fixImportsPlugin(): any {
    // Known imports mapped to paths relative to project root
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
    };

    function tryResolve(importName: string, dir: string): string | null {
        // Check same file names at a directory level
        const baseCandidates = [
            path.join(dir, importName),
            path.join(dir, importName + '.ts'),
            path.join(dir, importName + '.tsx'),
        ];
        for (const candidate of baseCandidates) {
            if (fs.existsSync(candidate)) {
                if (candidate.includes('node_modules')) return null;
                const stat = fs.statSync(candidate);
                if (!stat.isDirectory()) return candidate;
            }
        }
        // Check directory/index.ts or directory/index.tsx
        const indexCandidates = [
            path.join(dir, importName, 'index.ts'),
            path.join(dir, importName, 'index.tsx'),
        ];
        for (const candidate of indexCandidates) {
            if (fs.existsSync(candidate) && !candidate.includes('node_modules')) {
                return candidate;
            }
        }
        // Check common subdirectory patterns
        for (const subDir of ['constants', 'model-config', 'ui']) {
            const subCandidates = [
                path.join(dir, subDir, importName),
                path.join(dir, subDir, importName + '.ts'),
                path.join(dir, subDir, importName + '.tsx'),
            ];
            for (const candidate of subCandidates) {
                if (fs.existsSync(candidate)) {
                    if (candidate.includes('node_modules')) return null;
                    const stat = fs.statSync(candidate);
                    if (!stat.isDirectory()) return candidate;
                }
            }
        }
        return null;
    }

    return {
        name: 'fix-imports-resolver',
        enforce: 'pre',
        resolveId(source, importer) {
            if (!importer) return null;

            // Handle empty string imports (placeholder imports)
            if (source === '' || source === "''" || source === '""') {
                return null;
            }

            // Only handle relative imports
            if (!source.startsWith('./') && !source.startsWith('../')) {
                return null;
            }

            const importDir = path.dirname(importer);
            const importName = source.replace(/^\.\\.?\//, '');

            // Check if the import matches a known import name
            if (KNOWN_IMPORTS.hasOwnProperty(importName)) {
                const mappedPath = path.resolve(path.dirname(importer), KNOWN_IMPORTS[importName]);
                if (fs.existsSync(mappedPath)) {
                    return mappedPath;
                }
            }

            // Try to resolve in the current directory
            const result = tryResolve(importName, importDir);
            if (result) return result;

            // Try to resolve in parent directories (up to 3 levels)
            for (let depth = 1; depth <= 3; depth++) {
                const parentDir = path.join(importDir, '..'.repeat(depth));
                const resolved = tryResolve(importName, parentDir);
                if (resolved) return resolved;
            }

            return null;
        },
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
      optimizeDeps: {
        exclude: ['@monaco-editor/react'],
      },
      css: {
        postcss: './postcss.config.cjs'
      },
      build: {
        rollupOptions: {
          output: {
            manualChunks(id) {
              if (id.includes('node_modules')) {
                const pkg = id.toString().split('node_modules/')[1].split('/')[0].toString();
                // Keep UMD packages (react, react-dom, scheduler) in main bundle
                if (['react', 'react-dom', 'scheduler'].includes(pkg)) return null;
                return pkg;
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
