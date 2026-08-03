import path from 'path';
import { defineConfig, loadEnv } from 'vite';
import react from '@vitejs/plugin-react';
import monacoEditorPlugin from 'vite-plugin-monaco-editor';
import fs from 'fs';

// Patch fs.rmdirSync to fix vite-plugin-monaco-editor in newer Node versions
const originalRmdirSync = fs.rmdirSync;
fs.rmdirSync = function(dirPath: fs.PathLike, options?: fs.RmDirOptions) {
    if (options && options.recursive) {
        return fs.rmSync(dirPath, { recursive: true, force: true });
    }
    return originalRmdirSync(dirPath, options);
} as any;

export default defineConfig(({ mode }) => {
    const env = loadEnv(mode, '.', '');
    return {
      plugins: [
        react(),
        // @ts-ignore
        (monacoEditorPlugin.default || monacoEditorPlugin)({
          languageWorkers: ['json', 'editorWorkerService']
        })
      ],
      define: {
        'process.env.API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.GEMINI_API_KEY': JSON.stringify(env.GEMINI_API_KEY),
        'process.env.MISTRAL_API_KEY': JSON.stringify(env.MISTRAL_API_KEY)
      },
      resolve: {
        alias: {
          '@': path.resolve(__dirname, '.'),
        }
      },
      css: {
        postcss: './postcss.config.cjs'
      },
      build: {
        rollupOptions: {
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
