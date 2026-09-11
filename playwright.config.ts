import { defineConfig } from '@playwright/test'
export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: true,
  use: { baseURL: 'http://127.0.0.1:5173', headless: true, trace: 'retain-on-failure' },
  webServer: [
    {
      command: 'npm run dev -- --port 5173 --strictPort',
      url: 'http://127.0.0.1:5173',
      reuseExistingServer: !process.env.CI,
    },
    ...(process.env.AGENT_SCENARIOS === '1'
      ? [
          {
            command: 'npm run agent:demo',
            url: 'http://127.0.0.1:8000/health',
            reuseExistingServer: !process.env.CI,
          },
        ]
      : []),
  ],
  projects: [
    { name: 'chromium', use: { browserName: 'chromium', viewport: { width: 1440, height: 1050 } } },
  ],
})
