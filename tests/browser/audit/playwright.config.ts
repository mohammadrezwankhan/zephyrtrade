import { defineConfig } from 'playwright/test';
import path from 'node:path';

const baseURL = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:4173/run/';
const localTLS = process.env.AUDIT_LOCAL_TLS === '1';
const results = path.resolve(process.env.AUDIT_RESULTS_DIR || 'test-results');
const root = path.resolve(__dirname, '../../..');
if (localTLS && !['localhost', '127.0.0.1', '[::1]'].includes(new URL(baseURL).hostname)) {
  throw new Error('AUDIT_LOCAL_TLS is restricted to loopback fixtures');
}

export default defineConfig({
  webServer: process.env.AUDIT_BASE_URL ? undefined : {
    command: 'python scripts/serve-audit.py --html .cloudflare/site/run/index.html --headers .cloudflare/runtime-security-headers.json',
    cwd: root,
    url: baseURL,
    reuseExistingServer: false,
    timeout: 15_000,
  },
  testDir: '.',
  testMatch: 'audit-verify.spec.ts',
  timeout: 45_000,
  expect: { timeout: 10_000 },
  fullyParallel: true,
  workers: process.env.CI ? 2 : 2,
  retries: 0,
  forbidOnly: true,
  outputDir: path.join(results, 'artifacts'),
  reporter: [['list'], ['html', { open: 'never', outputFolder: path.join(results, 'html') }],
    ['json', { outputFile: path.join(results, 'results.json') }]],
  use: {
    baseURL,
    viewport: { width: 1440, height: 900 },
    locale: 'en-GB',
    timezoneId: 'UTC',
    reducedMotion: 'reduce',
    storageState: { cookies: [], origins: [] },
    acceptDownloads: true,
    ignoreHTTPSErrors: localTLS,
    actionTimeout: 10_000,
    navigationTimeout: 30_000,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'off',
  },
  projects: [
    { name: 'chromium', use: { browserName: 'chromium' } },
    { name: 'firefox', use: { browserName: 'firefox' } },
    { name: 'webkit', use: { browserName: 'webkit' } },
  ],
});
