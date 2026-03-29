import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  build: {
    chunkSizeWarningLimit: 1000,
    rolldownOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules')) {
            if (
              id.includes('/react/') ||
              id.includes('/react-dom/') ||
              id.includes('/react-router-dom/')
            ) {
              return 'react-vendor';
            }

            if (
              id.includes('/@mui/') ||
              id.includes('/@emotion/')
            ) {
              return 'mui-vendor';
            }

            if (id.includes('/recharts/')) {
              return 'charts-vendor';
            }

            if (
              id.includes('/axios/') ||
              id.includes('/@tanstack/react-query/')
            ) {
              return 'data-vendor';
            }

            return 'vendor';
          }
        },
      },
    },
  },
});