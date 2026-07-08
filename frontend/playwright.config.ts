import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { defineConfig, devices } from '@playwright/test'
import { getTestDatabaseUrl } from './e2e/env'

const CONFIG_DIR = path.dirname(fileURLToPath(import.meta.url))
const BACKEND_PORT = 8100
const FRONTEND_PORT = 4173
const ROOT_DIR = path.resolve(CONFIG_DIR, '..')
const BACKEND_DIR = path.join(ROOT_DIR, 'backend')
const TEST_DATABASE_URL = getTestDatabaseUrl(path.join(ROOT_DIR, '.env'))

export default defineConfig({
  testDir: './e2e',
  fullyParallel: false,
  workers: 1,
  reporter: 'list',
  globalSetup: path.join(CONFIG_DIR, 'e2e/global-setup.ts'),
  use: {
    baseURL: `http://localhost:${FRONTEND_PORT}`,
    trace: 'on-first-retry',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: [
    {
      command: `uv run uvicorn app.main:app --port ${BACKEND_PORT}`,
      cwd: BACKEND_DIR,
      port: BACKEND_PORT,
      env: {
        DATABASE_URL: TEST_DATABASE_URL,
        CORS_ALLOW_ORIGINS: `http://localhost:${FRONTEND_PORT}`,
      },
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
    {
      command: `npm run dev -- --port ${FRONTEND_PORT} --strictPort`,
      cwd: CONFIG_DIR,
      port: FRONTEND_PORT,
      env: {
        VITE_API_BASE_URL: `http://localhost:${BACKEND_PORT}`,
      },
      reuseExistingServer: !process.env.CI,
      timeout: 30_000,
    },
  ],
})
