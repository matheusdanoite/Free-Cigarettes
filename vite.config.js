import { defineConfig } from 'vite'

export default defineConfig({
  root: 'barzar',
  server: {
    port: 3000,
  },
  build: {
    outDir: '../dist',
  }
})
