import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react-swc';
import tailwindcss from '@tailwindcss/vite';
import path from 'path';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Preview path. NEVER output to ./static/workspace (the live REALFRONTEND
  // bundle protected by AGENTS.md). Promote to /workspace/ only after audit.
  base: '/workspace-next/',
  build: {
    outDir: './static/workspace-next',
    emptyOutDir: true,
    assetsDir: 'assets',
    sourcemap: false
  },
  server: {
    proxy: {
      '/api': { target: 'http://5.78.135.11:8088', changeOrigin: true }
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src')
    }
  }
});
