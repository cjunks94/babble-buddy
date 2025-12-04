import { defineConfig } from 'vite';
import dts from 'vite-plugin-dts';
import { resolve } from 'path';

export default defineConfig({
  plugins: [dts({ rollupTypes: true })],
  publicDir: 'public',
  build: {
    lib: {
      entry: resolve(__dirname, 'src/index.ts'),
      name: 'BabbleBuddy',
      fileName: 'babble-buddy',
    },
    rollupOptions: {
      output: {
        assetFileNames: 'babble-buddy.[ext]',
      },
    },
    copyPublicDir: true,
  },
});
