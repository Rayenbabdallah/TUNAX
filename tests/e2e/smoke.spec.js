import { test, expect } from '@playwright/test';

const baseURL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:3000';
const password = process.env.PLAYWRIGHT_PASSWORD || 'TunaxDemo123!';
const apiBase = process.env.PLAYWRIGHT_API_BASE || 'http://localhost:5000/api/v1';
const loginRetries = Number(process.env.PLAYWRIGHT_LOGIN_RETRIES || 6);
const loginBackoffMs = Number(process.env.PLAYWRIGHT_LOGIN_BACKOFF_MS || 1000);
const loginSpacingMs = Number(process.env.PLAYWRIGHT_LOGIN_SPACING_MS || 5000);

const tokenCache = new Map();
let lastLoginTs = 0;

const users = [
  { role: 'citizen', username: 'demo_citizen', path: '/dashboards/citizen/index.html' },
  { role: 'business', username: 'demo_business', path: '/dashboards/business/index.html' },
  { role: 'municipal_agent', username: 'demo_agent', path: '/dashboards/agent/index.html' },
  { role: 'inspector', username: 'demo_inspector', path: '/dashboards/inspector/index.html' },
  { role: 'finance_officer', username: 'demo_finance', path: '/dashboards/finance/index.html' },
  { role: 'contentieux_officer', username: 'demo_contentieux', path: '/dashboards/contentieux/index.html' },
  { role: 'urbanism_officer', username: 'demo_urbanism', path: '/dashboards/urbanism/index.html' },
  { role: 'municipal_admin', username: 'demo_admin', path: '/dashboards/admin/index.html' },
  { role: 'ministry_admin', username: 'ministry_admin', path: '/dashboards/ministry/index.html' }
];

test.describe('dashboard smoke', () => {
  for (const user of users) {
    test(`${user.role} dashboard loads without console errors`, async ({ page }) => {
      const consoleErrors = [];
      page.on('console', msg => {
        if (msg.type() === 'error') consoleErrors.push(msg.text());
      });

      const failedRequests = [];
      page.on('requestfailed', req => {
        failedRequests.push({ url: req.url(), error: req.failure()?.errorText, method: req.method() });
      });

      // Login via API with spacing, retry, and token cache to avoid 429s
      const apiData = await getAuthTokens(page, user);

      // Seed tokens/role into localStorage at app origin
      await page.goto(`${baseURL}/`);
      await page.evaluate(({ access, refresh, role }) => {
        localStorage.setItem('access_token', access);
        localStorage.setItem('refresh_token', refresh);
        localStorage.setItem('role', role.toLowerCase());
      }, { access: apiData.access_token, refresh: apiData.refresh_token, role: apiData.role || apiData.user?.role || '' });

      // Navigate directly to dashboard
      const targetUrl = `${baseURL}${user.path}`;
      await page.goto(targetUrl);
      await page.waitForLoadState('domcontentloaded');

      // Basic sanity waits for visible content to finish rendering
      await page.waitForTimeout(1000);

      const filteredErrors = consoleErrors.filter(msg => {
        const lower = msg.toLowerCase();
        return !lower.includes('too many requests') && !lower.includes('429');
      });

      if (consoleErrors.length || failedRequests.length) {
        const details = {
          role: user.role,
          consoleErrors,
          filteredErrors,
          failedRequests
        };
        console.log(`SMOKE_RESULT ${JSON.stringify(details, null, 2)}`);
      }

      expect(filteredErrors, 'Console errors present (excluding 429 rate limits)').toEqual([]);
      expect(failedRequests, 'Network failures present').toEqual([]);
    });
  }
});

async function getAuthTokens(page, user) {
  if (tokenCache.has(user.username)) return tokenCache.get(user.username);
  const sinceLast = Date.now() - lastLoginTs;
  if (sinceLast < loginSpacingMs) {
    await page.waitForTimeout(loginSpacingMs - sinceLast);
  }
  let apiData;
  for (let attempt = 1; attempt <= loginRetries; attempt++) {
    const apiResponse = await page.request.post(`${apiBase}/auth/login`, {
      data: { username: user.username, password }
    });
    apiData = await apiResponse.json();
    if (apiResponse.ok()) {
      lastLoginTs = Date.now();
      tokenCache.set(user.username, apiData);
      return apiData;
    }
    if (apiResponse.status() === 429) {
      await page.waitForTimeout(3000);
    }
    if (attempt === loginRetries) {
      throw new Error(`Login failed for ${user.role}: ${apiData.error || apiResponse.status()}`);
    }
    await page.waitForTimeout(loginBackoffMs * attempt);
  }
  throw new Error(`Login failed for ${user.role}: unknown error`);
}
