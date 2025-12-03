import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const webRoot = dirname(fileURLToPath(import.meta.url))
const projectRoot = resolve(webRoot, '..', '..')

// https://vite.dev/config/
export default defineConfig({
  envDir: projectRoot,
  plugins: [react()],
})
