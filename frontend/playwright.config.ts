import { defineConfig, devices } from '@playwright/test';

/**
 * ScanIt E2E 测试配置
 * 测试关键流程：登录、作品管理、检测任务、结果查看
 */
export default defineConfig({
  testDir: './e2e',
  timeout: 30 * 1000,
  retries: 2,
  workers: 1,
  
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:3000',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});
