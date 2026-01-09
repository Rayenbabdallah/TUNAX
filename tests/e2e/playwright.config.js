import { defineConfig } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const headlessEnv = process.env.PLAYWRIGHT_HEADLESS;
const headless = headlessEnv ? headlessEnv !== 'false' : true;

export default defineConfig({
  timeout: 90_000,
  workers: 1,
  use: {
    baseURL,
    headless,
    screenshot: 'only-on-failure',
    trace: 'retain-on-failure'
  },
  reporter: [['list']]
});
