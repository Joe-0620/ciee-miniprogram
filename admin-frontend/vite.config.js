import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';


export default defineConfig(({ command }) => ({
  plugins: [react()],
  base: command === 'serve' ? '/' : '/static/admin/',
  build: {
    outDir: '../wxcloudrun/static/admin',
    emptyOutDir: true,
    sourcemap: false,
    rollupOptions: {
      output: {
        entryFileNames: 'assets/admin-app.js',
        chunkFileNames: 'assets/[name].js',
        assetFileNames: 'assets/admin-app[extname]',
      },
    },
  },
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/dashboard-api': 'http://127.0.0.1:27081',
    },
  },
}));
