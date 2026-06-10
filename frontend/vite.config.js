import { defineConfig } from 'vite';

// Minimal Vite config for the Phase 1 placeholder shell.
// The full React 18 + Tailwind setup is configured in ISSUE 1.5.
export default defineConfig({
  server: {
    host: true,
    port: 3000,
  },
  build: {
    outDir: 'dist',
  },
});
