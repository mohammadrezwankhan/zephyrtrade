import { test as base, expect, type Page, type Locator, type TestInfo } from 'playwright/test';
import { createHash } from 'node:crypto';

/**
 * Release verification, authored against proposed/run.html on 2026-10-20.
 * Browser E2E was NOT run during authorship. --list validates discovery/transpilation only.
 * All tests use isolated, empty browser contexts. There are no blanket error allowances.
 */
const BASE_URL = process.env.AUDIT_BASE_URL || 'http://127.0.0.1:4173/run/';
const RELEASE_SHA = process.env.AUDIT_EXPECTED_DOCUMENT_SHA256 || '';
const ROUTES = {
  overview: 'From wind to value.', lab: 'Test the trade-off.',
  models: 'Let the evidence lead.', data: 'Every number, traceable.',
  method: 'Know what you are seeing.',
} as const;
type Route = keyof typeof ROUTES;
const MODELS = [
  'direct_regression', 'direct_classification', 'locally_weighted', 'polynomial_ols',
  'ridge_polynomial', 'clustered_ridge', 'linear_ols', 'lasso_polynomial', 'persistence_24h',
];
const VIEWPORTS = [
  { width: 1920, height: 1080 }, { width: 1440, height: 900 },
  { width: 768, height: 1024 }, { width: 375, height: 812 },
];
const DEFAULT_INPUT = {
  capacity: 30, hours: 1, da: 420, up: 610, down: 310,
  scenarios: [2, 5, 9, 13, 18, 24, 28], probabilities: [] as number[],
};
type LabInput = typeof DEFAULT_INPUT;
type AuditLog = {
  unexpected: { kind: string; detail: string }[];
  warnings: string[];
  requests: { url: string; method: string; resourceType: string }[];
  websockets: string[];
};

const test = base.extend<{ audit: AuditLog }>({
  audit: [async ({ context }, use, testInfo) => {
    const log: AuditLog = { unexpected: [], warnings: [], requests: [], websockets: [] };
    const record = (kind: string, detail: string) => log.unexpected.push({ kind, detail });
    const monitored = new WeakSet<Page>();
    const watch = (page: Page) => {
      if (monitored.has(page)) return;
      monitored.add(page);
      page.on('console', message => {
        const detail = `${message.text()} ${JSON.stringify(message.location())}`;
        if (message.type() === 'error') record('console.error', detail);
        if (message.type() === 'warning') log.warnings.push(detail);
      });
      page.on('pageerror', error => record('pageerror', error.stack || error.message));
      page.on('websocket', socket => log.websockets.push(socket.url()));
    };
    context.on('page', watch);
    context.pages().forEach(watch);
    context.on('request', request => log.requests.push({
      url: request.url(), method: request.method(), resourceType: request.resourceType(),
    }));
    context.on('requestfailed', request => record('requestfailed',
      `${request.method()} ${request.url()} ${request.failure()?.errorText || 'unknown failure'}`));
    context.on('response', response => {
      if (response.status() >= 400) record('HTTP >= 400', `${response.status()} ${response.url()}`);
    });
    // The Node-side binding retains failures across reloads and route changes.
    await context.exposeBinding('__auditUnhandledRejection', (_source, detail: string) =>
      record('unhandledrejection', detail));
    await context.addInitScript(() => {
      window.addEventListener('unhandledrejection', event => {
        const reason = event.reason;
        let detail: string;
        try { detail = reason instanceof Error ? (reason.stack || reason.message) : String(reason); }
        catch { detail = 'Unserializable rejection reason'; }
        void (window as any).__auditUnhandledRejection(detail);
      });
    });
    await use(log);
    await testInfo.attach('runtime-and-network-diagnostics', {
      body: Buffer.from(JSON.stringify(log, null, 2)), contentType: 'application/json',
    });
    expect(log.unexpected, 'Every unexpected console/error/network event is a release failure')
      .toEqual([]);
  }, { auto: true }],
});

function address(route: string): string {
  const result = new URL(BASE_URL);
  result.hash = route;
  return result.href;
}

async function open(page: Page, route: Route) {
  const response = await page.goto(address(route), { waitUntil: 'load' });
  expect(response, 'A document response is required').not.toBeNull();
  expect(response!.status(), 'Main document must return 200').toBe(200);
  await expect(page.locator('#page-title')).toHaveText(ROUTES[route]);
  await expect(page.locator('#fatal-error')).toBeHidden();
  return response!;
}

async function navigate(page: Page, route: Route) {
  await page.locator(`nav a[href="#${route}"]`).click();
  await expect(page).toHaveURL(address(route));
  await expect(page.locator('#page-title')).toHaveText(ROUTES[route]);
  await expect(page.locator(`nav a[href="#${route}"]`)).toHaveAttribute('aria-current', 'page');
}

function numeric(text: string): number {
  const match = text.replace(/[−–]/g, '-').match(/-?\d[\d,]*(?:\.\d+)?/);
  if (!match) throw new Error(`No number in ${JSON.stringify(text)}`);
  const value = Number(match[0].replace(/,/g, ''));
  expect(Number.isFinite(value), text).toBe(true);
  return value;
}

async function result(page: Page, offer: number, revenue?: number) {
  await expect.poll(async () => numeric(await page.locator('#optimal-offer').innerText()),
    { message: `Wait for the calculated ${offer} MW result` }).toBeCloseTo(offer, 2);
  await expect(page.locator('#lab-stale')).toBeHidden();
  await expect(page.locator('#lab-error')).toBeHidden();
  if (revenue !== undefined) {
    await expect.poll(async () => Math.abs(numeric(await page.locator('#expected-revenue').innerText()) - revenue))
      .toBeLessThanOrEqual(0.0051); // UI rounds DKK to two decimal places.
  }
}

async function fillLab(page: Page, fields: Record<string, string | number>) {
  for (const [id, value] of Object.entries(fields)) await page.locator(`#${id}`).fill(String(value));
}

async function calculate(page: Page) {
  await page.locator('#lab-form button[type="submit"]').click();
}

async function customDate(page: Page, from = '2024-12-15', to = from) {
  await page.locator('[data-period="custom"]').click();
  await page.locator('#from-date').fill(from);
  await page.locator('#to-date').fill(to);
  await page.locator('#apply-dates').click();
  await expect(page.locator('#filter-error')).toBeHidden();
  await expect(page.locator('[data-period="custom"]')).toHaveAttribute('aria-pressed', 'true');
}

async function cleanNumericOutput(page: Page) {
  const output = await page.locator(
    '.kpi-value, #optimal-offer, #expected-revenue, .metric-triple strong, td.number, .model-bar-row strong',
  ).allTextContents();
  for (const text of output) expect(text).not.toMatch(/\b(?:NaN|Infinity|undefined)\b/);
}

async function noRootOverflow(page: Page) {
  const bounds = await page.evaluate(() => ({
    viewport: document.documentElement.clientWidth,
    root: document.documentElement.scrollWidth,
    body: document.body.scrollWidth,
  }));
  expect(bounds.root).toBeLessThanOrEqual(bounds.viewport + 1);
  expect(bounds.body).toBeLessThanOrEqual(bounds.viewport + 1);
}

async function fitsViewport(locator: Locator, page: Page) {
  const box = await locator.boundingBox();
  expect(box).not.toBeNull();
  const size = page.viewportSize()!;
  expect(box!.x).toBeGreaterThanOrEqual(-1);
  expect(box!.y).toBeGreaterThanOrEqual(-1);
  expect(box!.x + box!.width).toBeLessThanOrEqual(size.width + 1);
  expect(box!.y + box!.height).toBeLessThanOrEqual(size.height + 1);
}

async function download(page: Page, selector: string, info: TestInfo) {
  const pending = page.waitForEvent('download'); // Arm before the click.
  await page.locator(selector).click();
  const item = await pending;
  const stream = await item.createReadStream();
  expect(stream, 'A real readable download is required').not.toBeNull();
  const chunks: Buffer[] = [];
  for await (const chunk of stream!) chunks.push(Buffer.from(chunk));
  const bytes = Buffer.concat(chunks);
  expect(await item.failure()).toBeNull();
  expect(bytes.length).toBeGreaterThan(0);
  await info.attach(item.suggestedFilename(), {
    body: bytes, contentType: item.suggestedFilename().endsWith('.json') ? 'application/json' : 'text/csv',
  });
  return { name: item.suggestedFilename(), bytes, text: bytes.toString('utf8').replace(/^\uFEFF/, '') };
}

/** RFC-style CSV reader: checks real bytes, quoted cells, escaped quotes and CRLF. */
function csv(text: string): Record<string, string>[] {
  const rows: string[][] = [];
  let row: string[] = [], cell = '', quoted = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { cell += '"'; i++; } else quoted = !quoted;
    } else if (c === ',' && !quoted) { row.push(cell); cell = ''; }
    else if ((c === '\r' || c === '\n') && !quoted) {
      if (c === '\r' && text[i + 1] === '\n') i++;
      row.push(cell); rows.push(row); row = []; cell = '';
    } else cell += c;
  }
  expect(quoted, 'CSV must not contain an unterminated quote').toBe(false);
  if (cell || row.length) { row.push(cell); rows.push(row); }
  const header = rows.shift();
  expect(header).toBeDefined();
  expect(new Set(header!).size).toBe(header!.length);
  return rows.map(values => {
    expect(values.length, `CSV row width: ${values}`).toBe(header!.length);
    return Object.fromEntries(header!.map((key, i) => [key, values[i]]));
  });
}

function value(row: Record<string, string>, key: string): number {
  expect(row, `CSV field ${key}`).toHaveProperty(key);
  expect(row[key].trim()).not.toBe('');
  const result = Number(row[key]);
  expect(Number.isFinite(result), `${key}=${row[key]}`).toBe(true);
  return result;
}

function validateDataRows(rows: Record<string, string>[], model: string, count = 24) {
  expect(rows).toHaveLength(count);
  const timestamps = rows.map(row => row.timestamp_utc);
  expect(new Set(timestamps).size).toBe(count);
  expect(timestamps).toEqual([...timestamps].sort());
  for (const row of rows) {
    expect(row.data_kind).toBe('synthetic_research');
    expect(row.strategy).toBe(model);
    expect(row.farm_id).toBe('bornholm_ronne_coastal');
    expect(row.timestamp_utc).toMatch(/^2024-12-15T\d{2}:00:00Z$/);
    expect(value(row, 'interval_hours')).toBe(1);
    expect(value(row, 'capacity_mw')).toBe(30);
    const actual = value(row, 'actual_mw'), offer = value(row, 'offer_mw');
    expect(actual).toBeGreaterThanOrEqual(0); expect(actual).toBeLessThanOrEqual(30);
    expect(offer).toBeGreaterThanOrEqual(0); expect(offer).toBeLessThanOrEqual(30);
    const da = value(row, 'day_ahead_dkk_mwh'), up = value(row, 'up_dkk_mwh');
    const down = value(row, 'down_dkk_mwh');
    expect(down).toBeLessThanOrEqual(da); expect(da).toBeLessThanOrEqual(up);
    const expected = da * offer + down * Math.max(actual - offer, 0) - up * Math.max(offer - actual, 0);
    expect(Math.abs(value(row, 'revenue_dkk') - expected)).toBeLessThan(1e-7);
  }
}

function expectedRevenue(input: LabInput, offer: number): number {
  const weights = input.probabilities.length ? input.probabilities : input.scenarios.map(() => 1 / input.scenarios.length);
  return input.scenarios.reduce((sum, output, index) => sum + weights[index] * input.hours *
    (input.da * offer + input.down * Math.max(output - offer, 0) - input.up * Math.max(offer - output, 0)), 0);
}

async function colourContrast(page: Page, selector: string, border = false) {
  return page.locator(selector).evaluateAll((elements, isBorder) => {
    type RGBA = [number, number, number, number];
    const canvas = document.createElement('canvas'); canvas.width = canvas.height = 1;
    const ctx = canvas.getContext('2d', { willReadFrequently: true })!;
    const resolve = (colour: string): RGBA => {
      ctx.clearRect(0, 0, 1, 1); ctx.fillStyle = colour; ctx.fillRect(0, 0, 1, 1);
      const p = ctx.getImageData(0, 0, 1, 1).data;
      return [p[0], p[1], p[2], p[3] / 255];
    };
    const over = (top: RGBA, bottom: RGBA): RGBA => {
      const a = top[3] + bottom[3] * (1 - top[3]);
      return [0, 1, 2].map(i => a ? (top[i] * top[3] + bottom[i] * bottom[3] * (1 - top[3])) / a : 0)
        .concat(a) as RGBA;
    };
    const chain = (el: Element) => { const list = []; for (let n: Element | null = el; n; n = n.parentElement) list.unshift(n); return list; };
    const background = (el: Element) => chain(el).reduce((base, node) =>
      over(resolve(getComputedStyle(node).backgroundColor), base), [255, 255, 255, 1] as RGBA);
    const luminance = (rgba: RGBA) => rgba.slice(0, 3).map(x => x / 255)
      .map(x => x <= 0.04045 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4)
      .reduce((sum, x, i) => sum + x * [0.2126, 0.7152, 0.0722][i], 0);
    return elements.map(el => {
      const css = getComputedStyle(el), panel = el.closest('.panel');
      if (isBorder && !panel) throw new Error('Border comparison requires a panel');
      const backdrop = background(isBorder ? panel! : el);
      const ink = resolve(isBorder ? css.borderTopColor : css.color);
      ink[3] *= Number(css.opacity);
      const painted = over(ink, backdrop), a = luminance(painted), b = luminance(backdrop);
      return { text: el.textContent, contrast: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05),
        foreground: painted, background: backdrop, opacity: Number(css.opacity),
        ancestorOpacities: chain(el).slice(0, -1).map(node => Number(getComputedStyle(node).opacity)) };
    });
  }, border);
}

async function inspectChart(page: Page, selector: string, compact: boolean) {
  const chart = page.locator(selector);
  await expect(chart).toBeVisible();
  if (compact) await expect(chart).toHaveClass(/chart-compact/);
  const checks = await chart.evaluate((el: SVGSVGElement) => {
    const panel = el.closest('.panel')!.getBoundingClientRect();
    const geometry = [...el.querySelectorAll('*')].flatMap(node =>
      [...node.attributes].filter(a => ['d', 'points', 'x', 'y', 'x1', 'x2', 'y1', 'y2', 'cx', 'cy', 'r'].includes(a.name))
        .map(a => `${a.name}=${a.value}`));
    const labels = [...el.querySelectorAll('text')].map(text => {
      const m = text.getScreenCTM(); if (!m) throw new Error('SVG text lacks a screen transform');
      const box = text.getBoundingClientRect();
      const clips = [];
      for (let node: Element | null = text.parentElement; node; node = node.parentElement) {
        const css = getComputedStyle(node);
        if (/hidden|clip|scroll|auto/.test(`${css.overflowX} ${css.overflowY}`)) {
          const r = node.getBoundingClientRect();
          clips.push({ left: r.left, top: r.top, right: r.right, bottom: r.bottom,
            x: /hidden|clip|scroll|auto/.test(css.overflowX), y: /hidden|clip|scroll|auto/.test(css.overflowY) });
        }
      }
      return { text: text.textContent, font: parseFloat(getComputedStyle(text).fontSize) * Math.hypot(m.c, m.d),
        box: { left: box.left, top: box.top, right: box.right, bottom: box.bottom, width: box.width, height: box.height }, clips };
    });
    return { geometry, labels, panel: { left: panel.left, top: panel.top, right: panel.right, bottom: panel.bottom } };
  });
  expect(checks.geometry.length).toBeGreaterThan(0);
  for (const geometry of checks.geometry) {
    expect(geometry).not.toMatch(/NaN|Infinity|undefined/);
    for (const token of geometry.split('=')[1].match(/[-+]?(?:\d*\.)?\d+(?:e[-+]?\d+)?/gi) || [])
      expect(Number.isFinite(Number(token))).toBe(true);
  }
  expect(checks.labels.length).toBeGreaterThan(0);
  for (const label of checks.labels) {
    expect(Number.isFinite(label.font)).toBe(true);
    if (compact) expect(label.font, `${label.text}: effective CSS font size`).toBeGreaterThanOrEqual(11);
    expect(label.box.width).toBeGreaterThan(0); expect(label.box.height).toBeGreaterThan(0);
    expect(label.box.left).toBeGreaterThanOrEqual(checks.panel.left - 2);
    expect(label.box.right).toBeLessThanOrEqual(checks.panel.right + 2);
    expect(label.box.top).toBeGreaterThanOrEqual(checks.panel.top - 2);
    expect(label.box.bottom).toBeLessThanOrEqual(checks.panel.bottom + 2);
    for (const clip of label.clips) {
      if (clip.x) { expect(label.box.left).toBeGreaterThanOrEqual(clip.left - 2); expect(label.box.right).toBeLessThanOrEqual(clip.right + 2); }
      if (clip.y) { expect(label.box.top).toBeGreaterThanOrEqual(clip.top - 2); expect(label.box.bottom).toBeLessThanOrEqual(clip.bottom + 2); }
    }
  }
}

test('Release gate: exact document, HTTPS security headers and both CSP script directives', async ({ page }, info) => {
  const response = await open(page, 'overview');
  const endpoint = new URL(response.url());
  const loopback = ['localhost', '127.0.0.1', '[::1]'].includes(endpoint.hostname);
  expect(endpoint.protocol === 'https:' || (loopback && endpoint.protocol === 'http:')).toBe(true);
  info.annotations.push({ type: 'transport', description: loopback ?
    'Loopback fixture: HTTPS transport itself is not verified in this run.' : 'Real HTTPS navigation; certificate errors are not ignored.' });
  expect(RELEASE_SHA).toMatch(/^[a-f0-9]{64}$/);
  const body = await response.body();
  expect(createHash('sha256').update(body).digest('hex')).toBe(RELEASE_SHA);
  const headers = await response.allHeaders();
  await info.attach('document-response-headers', { body: Buffer.from(JSON.stringify(headers, null, 2)), contentType: 'application/json' });
  expect(headers['content-type']).toMatch(/text\/html/i);
  expect(headers['x-content-type-options']).toBe('nosniff');
  expect(headers['x-frame-options']).toMatch(/^DENY$/i);
  expect(headers['referrer-policy']).toBe('strict-origin-when-cross-origin');
  for (const feature of ['camera', 'microphone', 'geolocation'])
    expect(headers['permissions-policy']).toMatch(new RegExp(`${feature}=\\(\\)`));
  const hsts = headers['strict-transport-security'];
  expect(hsts).toBeTruthy();
  expect(Number(hsts.match(/max-age=(\d+)/i)?.[1])).toBeGreaterThanOrEqual(31_536_000);
  expect(hsts).toMatch(/includeSubDomains/i);
  const csp = headers['content-security-policy']; expect(csp).toBeTruthy();
  const directives = new Map<string, string[]>();
  for (const section of csp.split(';').map(x => x.trim()).filter(Boolean)) {
    const [name, ...tokens] = section.split(/\s+/);
    expect(directives.has(name), `Duplicate CSP directive ${name}`).toBe(false);
    directives.set(name, tokens);
  }
  const scripts = [...body.toString('utf8').matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script\s*>/gi)];
  expect(scripts).toHaveLength(3);
  expect(scripts.every(match => !/\bsrc\s*=/i.test(match[1]))).toBe(true);
  for (const name of ['script-src', 'script-src-elem']) {
    const tokens = directives.get(name); expect(tokens, `Missing ${name}`).toBeDefined();
    expect(tokens).not.toContain("'unsafe-inline'"); expect(tokens).not.toContain("'unsafe-eval'");
    for (const script of scripts) {
      const hash = createHash('sha256').update(script[2].replace(/\r\n?/g, '\n')).digest('base64');
      expect(tokens, `${name} must authorize the exact delivered script`).toContain(`'sha256-${hash}'`);
    }
    expect(tokens!.some(token => /cloudflareinsights|\*/i.test(token))).toBe(false);
  }
  for (const [directive, required] of Object.entries({
    'default-src': "'self'", 'object-src': "'none'", 'base-uri': "'self'",
    'frame-ancestors': "'none'", 'form-action': "'self'", 'connect-src': "'self'",
  })) expect(directives.get(directive)).toEqual([required]);
});

for (const [route, heading] of Object.entries(ROUTES)) {
  test(`Route: direct #${route} renders its heading and selected navigation`, async ({ page }) => {
    await open(page, route as Route);
    await expect(page.getByRole('heading', { level: 1, name: heading, exact: true })).toHaveCount(1);
    await expect(page.locator(`nav a[href="#${route}"]`)).toHaveAttribute('aria-current', 'page');
    await expect(page).toHaveTitle(new RegExp('ZephyrTrade Champion'));
    await cleanNumericOutput(page);
  });
}

for (const viewport of VIEWPORTS) {
  test(`Responsive routes and dialogs fit ${viewport.width}×${viewport.height}`, async ({ page }, info) => {
    test.setTimeout(90_000);
    await page.setViewportSize(viewport);
    await open(page, 'overview');
    for (const theme of ['dark', 'light']) {
      if (theme === 'light') await page.locator('#theme-top').click();
      await expect(page.locator('html')).toHaveAttribute('data-theme', theme);
      for (const route of Object.keys(ROUTES) as Route[]) {
        await navigate(page, route); await noRootOverflow(page); await cleanNumericOutput(page);
      }
    }
    await page.locator('#help-button').click();
    await expect(page.locator('#guide-dialog')).toBeVisible();
    await fitsViewport(page.locator('#guide-dialog'), page);
    await page.keyboard.press('Escape');
    await navigate(page, 'lab');
    await page.locator('#save-scenario').click();
    await expect(page.locator('#save-dialog')).toBeVisible();
    await fitsViewport(page.locator('#save-dialog'), page);
    await page.locator('#save-dialog').getByRole('button', { name: 'Cancel', exact: true }).click();
    await expect(page.locator('#save-dialog')).toBeHidden();
    await info.attach(`lab-${viewport.width}`, { body: await page.screenshot({ fullPage: true }), contentType: 'image/png' });
  });
}

test('ISS-001: default calculation retains 9 MW and DKK 4,902.86', async ({ page }) => {
  await open(page, 'lab'); await calculate(page); await result(page, 9, 4902.857142857143);
});

const malformed = [
  ['leading comma', ',0,30', ',0.2,0.8'], ['trailing comma', '0,30,', '0.2,0.8,'],
  ['repeated comma', '0,,30', '0.2,,0.8'], ['leading semicolon', ';0;30', ';0.2;0.8'],
  ['trailing semicolon', '0;30;', '0.2;0.8;'], ['repeated semicolon', '0;;30', '0.2;;0.8'],
  ['empty mixed field', '0, ;30', '0.2, ;0.8'],
];
for (const field of ['scenarios', 'probabilities']) {
  for (const [label, scenarios, probabilities] of malformed) {
    test(`ISS-001: rejects ${field} with ${label} without changing the last result`, async ({ page }) => {
      await open(page, 'lab');
      await fillLab(page, { scenarios: '0,30', probabilities: '0.2,0.8' });
      await calculate(page); await result(page, 30, 8940);
      const before = await page.locator('#expected-revenue').innerText();
      await page.locator(`#${field}`).fill(field === 'scenarios' ? scenarios : probabilities);
      await calculate(page);
      await expect(page.locator('#lab-error')).toContainText('Remove empty values');
      await expect(page.locator('#lab-stale')).toBeVisible();
      await expect(page.locator('#expected-revenue')).toHaveText(before);
      await expect(page.locator('#export-scenario')).toBeDisabled();
    });
  }
}

test('ISS-001: whitespace lists and blank equal probabilities are valid', async ({ page }) => {
  await open(page, 'lab');
  await fillLab(page, { scenarios: ' 0 \n 30\t', probabilities: ' 0.2   0.8 ' });
  await calculate(page); await result(page, 30, 8940);
  await fillLab(page, { scenarios: '0; 30', probabilities: '   ' });
  await calculate(page); await result(page, 0, 4650);
  await fillLab(page, { scenarios: '2, 5; 9\n13 18\t24,28', probabilities: '' });
  await calculate(page); await result(page, 9, 4902.857142857143);
});

test('Lab rejects bounded numeric violations, bad price ordering and invalid distributions', async ({ page }) => {
  await open(page, 'lab');
  const cases: [string, string][] = [
    ['capacity', '0'], ['capacity', '10001'], ['hours', '0.24'], ['hours', '24.01'],
    ['da', '-10001'], ['da', '100001'], ['up', '100001'], ['down', '-10001'],
    ['da', '620'], ['up', '300'], ['down', '500'],
    ['scenarios', ''], ['scenarios', '-1,10'], ['scenarios', '0,31'],
    ['scenarios', Array(101).fill('1').join(',')], ['scenarios', '2,unknown,9'],
    ['probabilities', '0.5,0.5'], ['probabilities', '-1,0,0,0,0,0,2'],
    ['probabilities', '0,0,0,0,0,0,0'],
  ];
  for (const [field, bad] of cases) {
    await test.step(`${field}=${bad.slice(0, 40)}`, async () => {
      await fillLab(page, { capacity: 30, hours: 1, da: 420, up: 610, down: 310,
        scenarios: DEFAULT_INPUT.scenarios.join(','), probabilities: '' });
      await page.locator(`#${field}`).fill(bad); await calculate(page);
      await expect(page.locator('#lab-error')).toBeVisible();
      await expect(page.locator('#lab-error')).not.toHaveText('');
      await expect(page.locator('#save-scenario')).toBeDisabled();
    });
  }
});

for (const [preset, offer] of [['balanced', 13], ['shortfall', 5], ['surplus', 24]] as const) {
  test(`Lab preset ${preset} calculates ${offer} MW`, async ({ page }) => {
    await open(page, 'lab'); await page.locator(`[data-preset="${preset}"]`).click();
    await result(page, offer); await expect(page.locator('#save-scenario')).toBeEnabled();
  });
}

test('Stale lab drafts survive routing and disable saving and every result export', async ({ page }) => {
  await open(page, 'lab'); await page.locator('#scenarios').fill('3, 7, 11');
  for (const id of ['save-scenario', 'export-scenario', 'export-curve', 'verify-python'])
    await expect(page.locator(`#${id}`)).toBeDisabled();
  await expect(page.locator('#lab-result-state')).toHaveText('INPUTS CHANGED');
  await navigate(page, 'overview'); await navigate(page, 'lab');
  await expect(page.locator('#scenarios')).toHaveValue('3, 7, 11');
  await expect(page.locator('#lab-stale')).toBeVisible();
  await calculate(page); await result(page, 7);
  for (const id of ['save-scenario', 'export-scenario', 'export-curve', 'verify-python'])
    await expect(page.locator(`#${id}`)).toBeEnabled();
});

test('ISS-004: rejected schema-1 capacity-zero import preserves the complete unsaved draft', async ({ page }) => {
  await open(page, 'lab'); await page.locator('#scenarios').fill('1, 4, 11');
  const before = await page.locator('#lab-form input, #lab-form textarea').evaluateAll(nodes =>
    Object.fromEntries(nodes.map(node => [(node as HTMLInputElement).id, (node as HTMLInputElement).value])));
  await page.locator('#scenario-file').setInputFiles({ name: 'audit-invalid-capacity.json', mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({ schema_version: 1, input: { ...DEFAULT_INPUT, capacity: 0 } })) });
  await expect(page.locator('#toast')).toContainText('Import failed: Capacity must be');
  await navigate(page, 'method'); await navigate(page, 'lab');
  for (const [id, text] of Object.entries(before)) await expect(page.locator(`#${id}`)).toHaveValue(text);
  await expect(page.locator('#lab-stale')).toBeVisible();
  await expect(page.locator('#save-scenario')).toBeDisabled();
  expect(numeric(await page.locator('#optimal-offer').innerText())).toBe(9);
});

test('Import button accepts valid JSON and rejects malformed, unsupported and oversized files', async ({ page }) => {
  await open(page, 'lab');
  const chooserPromise = page.waitForEvent('filechooser');
  await page.locator('#import-scenario').click();
  const chooser = await chooserPromise;
  const input = { ...DEFAULT_INPUT, scenarios: [0, 30], probabilities: [0.2, 0.8] };
  await chooser.setFiles({ name: 'audit-valid.json', mimeType: 'application/json',
    buffer: Buffer.from(JSON.stringify({ schema_version: 1, input })) });
  await result(page, 30, 8940);
  await expect(page.locator('#scenarios')).toHaveValue('0, 30');
  for (const [name, content, message] of [
    ['malformed.json', '{broken', 'Import failed:'],
    ['schema.json', JSON.stringify({ schema_version: 2, input }), 'Unsupported scenario schema'],
    ['oversized.json', ' '.repeat(32769), 'smaller than 32 KB'],
  ]) {
    await page.locator('#scenario-file').setInputFiles({ name, mimeType: 'application/json', buffer: Buffer.from(content) });
    await expect(page.locator('#toast')).toContainText(message);
    await result(page, 30, 8940);
  }
});

test('ISS-005: extreme in-bounds CDF case selects the true 10,000 MW maximum', async ({ page }, info) => {
  await open(page, 'lab');
  const input = { capacity: 10000, hours: 24, da: 45000.000000055, up: 100000, down: -10000,
    scenarios: [0, 10000], probabilities: [0.5, 0.5] };
  await fillLab(page, { ...input, scenarios: '0,10000', probabilities: '0.5,0.5' });
  await calculate(page); await result(page, 10000, expectedRevenue(input, 10000));
  const json = JSON.parse((await download(page, '#export-scenario', info)).text);
  expect(json.calculated.offer_mw).toBe(10000);
  expect(Math.abs(json.calculated.expected_revenue_dkk - expectedRevenue(input, 10000))).toBeLessThan(1e-5);
  expect(json.calculated.expected_revenue_dkk).toBeGreaterThan(expectedRevenue(input, 0));
});

test('Date controls select 168, 714, 3,888 and 24 retained hours; invalid ranges retain prior data', async ({ page }) => {
  await open(page, 'overview');
  const intervals = page.locator('.kpi').filter({ hasText: 'Retained test intervals' }).locator('.kpi-value');
  for (const [period, hours] of [['7', 168], ['30', 714], ['all', 3888]] as const) {
    await page.locator(`[data-period="${period}"]`).click();
    expect(numeric(await intervals.innerText())).toBe(hours);
  }
  await customDate(page); expect(numeric(await intervals.innerText())).toBe(24);
  for (const [from, to] of [['2024-12-16', '2024-12-15'], ['2024-07-19', '2024-12-15'], ['', '2024-12-15']]) {
    await page.locator('#from-date').fill(from); await page.locator('#to-date').fill(to);
    await page.locator('#apply-dates').click();
    await expect(page.locator('#filter-error')).toContainText('Choose valid dates');
    expect(numeric(await intervals.innerText())).toBe(24);
  }
});

test('ISS-003: custom December 15 range and 24 hours persist across reload and shared routes', async ({ page }) => {
  await open(page, 'overview'); await customDate(page);
  await page.reload({ waitUntil: 'load' });
  await expect(page.locator('[data-period="custom"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('#from-date')).toHaveValue('2024-12-15');
  await expect(page.locator('#to-date')).toHaveValue('2024-12-15');
  expect(numeric(await page.locator('.kpi').filter({ hasText: 'Retained test intervals' }).locator('.kpi-value').innerText())).toBe(24);
  await navigate(page, 'models'); await expect(page.locator('.panel-header p').first()).toContainText('24 retained hourly records');
  await navigate(page, 'data'); await expect(page.locator('#page-content tbody tr')).toHaveCount(24);
  await expect(page.locator('.pagination')).toContainText('Page 1 / 1');
});

test('ISS-002: case-insensitive search exports the identical 24 timestamps and numeric rows', async ({ page }, info) => {
  await open(page, 'data'); await page.locator('#data-search').fill('2024-12-15t');
  await expect(page.locator('#page-content tbody tr')).toHaveCount(24);
  await expect(page.locator('#export-filtered')).toHaveText('Export 24 matching rows');
  const shown = await page.locator('#page-content tbody tr td:first-child').allTextContents();
  const file = await download(page, '#export-filtered', info);
  expect(file.name).toMatch(/\.csv$/);
  const rows = csv(file.text); validateDataRows(rows, 'direct_regression');
  expect(rows.map(row => row.timestamp_utc.slice(0, 16).replace('T', ' '))).toEqual(shown);
  const cells = await page.locator('#page-content tbody tr').evaluateAll(nodes =>
    nodes.map(row => [...row.querySelectorAll('td')].map(cell => cell.textContent || '')));
  const fields = ['actual_mw', 'offer_mw', 'day_ahead_dkk_mwh', 'up_dkk_mwh', 'down_dkk_mwh', 'revenue_dkk'];
  rows.forEach((row, i) => fields.forEach((field, j) =>
    expect(Math.abs(value(row, field) - numeric(cells[i][j + 1]))).toBeLessThanOrEqual(j < 2 ? 0.00051 : 0.0051)));
});

test('ISS-010: persistent polite search status announces counts and no matches while focus stays in search', async ({ page }) => {
  await open(page, 'data');
  const status = page.locator('#data-search-status'), handle = await status.elementHandle();
  expect(handle).not.toBeNull();
  await expect(status).toHaveAttribute('role', 'status');
  await expect(status).toHaveAttribute('aria-live', 'polite');
  await expect(status).toHaveAttribute('aria-atomic', 'true');
  await expect(page.locator('#data-search')).toHaveAttribute('aria-describedby', 'data-search-status');
  await page.locator('#data-search').fill('2024-12-15t');
  await expect(status).toHaveText('24 matching records.');
  await expect(page.locator('#data-search')).toBeFocused();
  await page.locator('#data-search').fill('audit-no-such-timestamp');
  await expect(status).toHaveText('No matching records.');
  await expect(page.locator('#page-content tbody')).toContainText('No matching records.');
  await expect(page.locator('#data-search')).toBeFocused();
  expect(await handle!.evaluate(el => el.isConnected && el === document.getElementById('data-search-status'))).toBe(true);
  await page.locator('#export-filtered').click();
  await expect(page.locator('#toast')).toHaveText('No rows match this selection.');
});

test('Ledger traverses all 156 pages with 3,888 unique ordered timestamps and bounded controls', async ({ page }) => {
  test.setTimeout(180_000);
  await open(page, 'data');
  await expect(page.locator('[data-paginate="-1"]')).toBeDisabled();
  const timestamps: string[] = []; let pages = 0, completed = false;
  while (pages < 200) {
    pages++;
    await expect(page.locator('.pagination')).toContainText(`Page ${pages} / 156`);
    const current = await page.locator('#page-content tbody tr td:first-child').allTextContents();
    expect(current).toHaveLength(pages < 156 ? 25 : 13);
    for (const stamp of current) expect(stamp).toMatch(/^2024-\d{2}-\d{2} \d{2}:00$/);
    timestamps.push(...current); await cleanNumericOutput(page);
    const next = page.locator('[data-paginate="1"]');
    if (await next.isDisabled()) { completed = true; break; }
    await next.click();
  }
  expect(completed, 'Pagination must terminate before the 200-page safety bound').toBe(true);
  expect(pages).toBe(156); expect(timestamps).toHaveLength(3888);
  expect(new Set(timestamps).size).toBe(3888); expect(timestamps).toEqual([...timestamps].sort());
  expect(timestamps[0]).toBe('2024-07-20 18:00'); expect(timestamps.at(-1)).toBe('2024-12-31 22:00');
  const millis = timestamps.map(t => Date.parse(t.replace(' ', 'T') + ':00Z'));
  const absent = millis.slice(1).reduce((sum, t, i) => sum + (t - millis[i]) / 3_600_000 - 1, 0);
  expect(absent).toBe(53);
  await expect(page.locator('[data-paginate="1"]')).toBeDisabled();
  await page.locator('[data-paginate="-1"]').click();
  await expect(page.locator('.pagination')).toContainText('Page 155 / 156');
});

test('All nine strategies select and Inspect correctly; comparison CSV reconciles to actual exported rows', async ({ page }, info) => {
  test.setTimeout(120_000);
  await open(page, 'overview'); await customDate(page);
  await expect(page.locator('#model-select option')).toHaveCount(9);
  const options = await page.locator('#model-select option').evaluateAll(nodes => nodes.map(node => (node as HTMLOptionElement).value));
  expect([...options].sort()).toEqual([...MODELS].sort());
  const totals = new Map<string, { revenue: number; oracle: number; rmse: number; mae: number; imbalance: number }>();
  for (const model of MODELS) {
    await page.locator('#model-select').selectOption(model);
    await expect(page.locator('#model-select')).toHaveValue(model); await cleanNumericOutput(page);
    const rows = csv((await download(page, '#export-top', info)).text); validateDataRows(rows, model);
    const differences = rows.map(row => value(row, 'actual_mw') - value(row, 'offer_mw'));
    const imbalance = differences.reduce((sum, x) => sum + Math.abs(x), 0);
    totals.set(model, { revenue: rows.reduce((s, r) => s + value(r, 'revenue_dkk'), 0),
      oracle: rows.reduce((s, r) => s + value(r, 'actual_mw') * value(r, 'day_ahead_dkk_mwh'), 0),
      rmse: Math.sqrt(differences.reduce((s, x) => s + x * x, 0) / 24), mae: imbalance / 24, imbalance });
    await navigate(page, 'models'); await expect(page.locator('#page-content tbody tr')).toHaveCount(9);
    await page.locator(`[data-select-model="${model}"]`).click();
    await expect(page.locator('#page-title')).toHaveText(ROUTES.overview);
    await expect(page.locator('#model-select')).toHaveValue(model);
  }
  await navigate(page, 'models');
  const exported = await download(page, '#export-models', info);
  expect(exported.name).toBe('ZephyrTrade-model-comparison.csv');
  const rows = csv(exported.text); expect(rows).toHaveLength(9);
  expect(rows.map(r => r.strategy).sort()).toEqual([...MODELS].sort());
  let prior = Infinity;
  for (const row of rows) {
    const expected = totals.get(row.strategy)!;
    expect(row.data_kind).toBe('synthetic_research'); expect(value(row, 'hours')).toBe(24);
    expect(row.start_utc).toBe('2024-12-15T00:00:00Z'); expect(row.end_utc).toBe('2024-12-15T23:00:00Z');
    expect(value(row, 'revenue_dkk')).toBeLessThanOrEqual(prior); prior = value(row, 'revenue_dkk');
    for (const [field, actual] of Object.entries({ revenue_dkk: expected.revenue,
      capture_pct: 100 * expected.revenue / expected.oracle, regret_dkk: expected.oracle - expected.revenue,
      offer_rmse_mw: expected.rmse, offer_mae_mw: expected.mae, absolute_imbalance_mwh: expected.imbalance }))
      expect(Math.abs(value(row, field) - actual)).toBeLessThan(1e-7);
  }
});

test('All three chart measures render the correct accessible chart and finite output', async ({ page }) => {
  await open(page, 'overview');
  for (const [mode, title] of [
    ['power', 'Actual synthetic wind output and selected strategy offer'],
    ['revenue', 'Cumulative synthetic revenue, selected offer and perfect-foresight benchmark'],
    ['prices', 'Synthetic day-ahead and balancing settlement prices'],
  ]) {
    await page.locator(`[data-chart="${mode}"]`).click();
    await expect(page.locator(`[data-chart="${mode}"]`)).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('#overview-plot svg')).toHaveAttribute('aria-label', title);
    await inspectChart(page, '#overview-plot svg', false); await cleanNumericOutput(page);
  }
});

test('Overview shortcuts and brand navigation open their intended routes', async ({ page }) => {
  await open(page, 'overview');
  for (const route of ['lab', 'models'] as Route[]) {
    await page.locator(`[data-go="${route}"]`).click();
    await expect(page).toHaveURL(address(route));
    await expect(page.locator('#page-title')).toHaveText(ROUTES[route]);
    await page.locator('a.brand[href="#overview"]').click();
    await expect(page.locator('#page-title')).toHaveText(ROUTES.overview);
  }
});

test('ISS-006: keyboard skip link preserves current route, heading and lab draft', async ({ page }) => {
  await open(page, 'method');
  for (const route of ['method', 'lab', 'data'] as Route[]) {
    await navigate(page, route);
    if (route === 'lab') await page.locator('#scenarios').fill('3, 7, 11');
    await page.locator('.skip-link').focus(); await page.keyboard.press('Enter');
    await expect(page).toHaveURL(address(route));
    await expect(page.locator('#page-title')).toHaveText(ROUTES[route]);
    await expect(page.locator('#workspace')).toBeFocused();
    if (route === 'lab') await expect(page.locator('#scenarios')).toHaveValue('3, 7, 11');
  }
});

test('ISS-007: Enter preserves Revenue, Next and preset focus after rerender', async ({ page }) => {
  await open(page, 'overview');
  await page.locator('[data-chart="revenue"]').focus(); await page.keyboard.press('Enter');
  await expect(page.locator('[data-chart="revenue"]')).toHaveAttribute('aria-pressed', 'true');
  await expect(page.locator('[data-chart="revenue"]')).toBeFocused();
  await navigate(page, 'data');
  await page.locator('[data-paginate="1"]').focus(); await page.keyboard.press('Enter');
  await expect(page.locator('.pagination')).toContainText('26–50 of 3,888 rows');
  await expect(page.locator('[data-paginate="1"]')).toBeFocused();
  await customDate(page, '2024-12-15', '2024-12-16');
  await page.locator('[data-paginate="1"]').focus(); await page.keyboard.press('Enter');
  await expect(page.locator('[data-paginate="1"]')).toBeDisabled();
  await expect(page.locator('[data-paginate="-1"]')).toBeFocused();
  await navigate(page, 'lab');
  await page.locator('[data-preset="balanced"]').focus(); await page.keyboard.press('Enter');
  await result(page, 13); await expect(page.locator('[data-preset="balanced"]')).toBeFocused();
});

test('ISS-008: normal and active light navigation indices have at least 4.5:1 contrast', async ({ page }, info) => {
  await open(page, 'overview'); await page.locator('#theme-top').click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await expect(page.locator('.nav-index').first()).toBeVisible();
  const measurements = await colourContrast(page, '.nav-index'); expect(measurements).toHaveLength(5);
  for (const measurement of measurements) {
    expect(measurement.ancestorOpacities.every(x => x === 1), 'Ancestor group opacity requires a revised compositing model').toBe(true);
    expect(measurement.contrast).toBeGreaterThanOrEqual(4.5);
  }
  await info.attach('nav-contrast', { body: Buffer.from(JSON.stringify(measurements, null, 2)), contentType: 'application/json' });
});

for (const theme of ['dark', 'light']) {
  test(`ISS-009: unfocused empty textarea border has at least 3:1 contrast in ${theme}`, async ({ page }, info) => {
    await open(page, 'lab'); if (theme === 'light') await page.locator('#theme-top').click();
    await page.locator('#scenarios').fill(''); await page.locator('#probabilities').focus();
    await expect(page.locator('#scenarios')).not.toBeFocused();
    const measurements = await colourContrast(page, '#scenarios', true); expect(measurements).toHaveLength(1);
    expect(measurements[0].ancestorOpacities.every(x => x === 1)).toBe(true);
    expect(measurements[0].contrast).toBeGreaterThanOrEqual(3);
    await info.attach(`textarea-${theme}-contrast`, { body: Buffer.from(JSON.stringify(measurements)), contentType: 'application/json' });
  });
}

for (const viewport of VIEWPORTS.filter(v => v.width <= 768)) {
  test(`ISS-011: compact chart text is at least 11 CSS px with finite unclipped geometry at ${viewport.width}`, async ({ page }) => {
    await page.setViewportSize(viewport); await open(page, 'overview');
    for (const mode of ['power', 'revenue', 'prices']) {
      await page.locator(`[data-chart="${mode}"]`).click();
      await inspectChart(page, '#overview-plot svg', true);
    }
    await navigate(page, 'lab'); await inspectChart(page, '#offer-plot svg', true); await noRootOverflow(page);
  });
}

test('ISS-011: wide desktop chart parameters remain 800×238 and 720×210', async ({ page }) => {
  await page.setViewportSize(VIEWPORTS[0]); await open(page, 'overview');
  expect(await page.locator('#overview-plot').evaluate(el => el.clientWidth)).toBeGreaterThanOrEqual(600);
  await expect(page.locator('#overview-plot svg')).toHaveAttribute('viewBox', '0 0 800 238');
  await expect(page.locator('#overview-plot .grid-line').first()).toHaveAttribute('x1', '50');
  expect(await page.locator('#overview-plot text').first().evaluate(el => getComputedStyle(el).fontSize)).toBe('10px');
  await navigate(page, 'lab');
  expect(await page.locator('#offer-plot').evaluate(el => el.clientWidth)).toBeGreaterThanOrEqual(600);
  await expect(page.locator('#offer-plot svg')).toHaveAttribute('viewBox', '0 0 720 210');
  await expect(page.locator('#offer-plot .grid-line').first()).toHaveAttribute('x1', '62');
});

test('Repeated Custom selection validates edited dates before committing state', async ({ page }) => {
  await open(page, 'overview');
  await customDate(page);
  await page.locator('#from-date').fill('2024-12-20');
  await page.locator('#to-date').fill('2024-12-15');
  await page.locator('[data-period="custom"]').click();
  await expect(page.locator('#filter-error')).toBeVisible();
  expect(await page.evaluate(() => (window as any).ZephyrApp.getVisibleMetrics().rows)).toBe(24);
});

test('Deleting the last saved scenario restores focus to Save scenario', async ({ page }) => {
  await open(page, 'lab');
  await page.locator('#save-scenario').click();
  await page.locator('#scenario-name').fill('Keyboard deletion regression');
  await page.locator('#save-dialog button[type="submit"]').click();
  await expect(page.locator('#saved-list .saved-item')).toHaveCount(1);
  page.once('dialog', dialog => dialog.accept());
  await page.locator('[data-delete-saved="0"]').focus();
  await page.keyboard.press('Enter');
  await expect(page.locator('#saved-list .saved-item')).toHaveCount(0);
  await expect(page.locator('#save-scenario')).toBeFocused();
});

test('Saved scenario lifecycle is isolated, persists, loads with focus, and handles cancel/accept deletion', async ({ page }) => {
  await open(page, 'lab');
  const name = 'Audit verification 2026-10-20 <literal>';
  await page.locator('[data-preset="balanced"]').click(); await result(page, 13);
  await page.locator('#save-scenario').click();
  await page.locator('#save-dialog button[type="submit"]').click();
  await expect(page.locator('#save-dialog')).toBeVisible();
  expect(await page.locator('#scenario-name').evaluate((el: HTMLInputElement) => el.validity.valueMissing)).toBe(true);
  await page.locator('#scenario-name').fill(name);
  await page.locator('#save-dialog button[type="submit"]').click();
  await expect(page.locator('#save-dialog')).toBeHidden();
  await expect(page.locator('#saved-list .saved-item strong')).toHaveText(name);
  await page.reload({ waitUntil: 'load' });
  await expect(page.locator('#saved-list .saved-item')).toHaveCount(1);
  await page.locator('[data-preset="shortfall"]').click(); await result(page, 5);
  await page.locator('[data-load-saved="0"]').focus(); await page.keyboard.press('Enter');
  await result(page, 13); await expect(page.locator('[data-load-saved="0"]')).toBeFocused();
  await expect(page.locator('#da')).toHaveValue('450'); await expect(page.locator('#up')).toHaveValue('600');
  for (const accept of [false, true]) {
    const pending = page.waitForEvent('dialog');
    const clicked = page.locator('[data-delete-saved="0"]').click();
    const dialog = await pending;
    expect(dialog.type()).toBe('confirm'); expect(dialog.message()).toContain(name);
    if (accept) await dialog.accept(); else await dialog.dismiss();
    await clicked;
    await expect(page.locator('#saved-list .saved-item')).toHaveCount(accept ? 0 : 1);
  }
  expect(await page.evaluate(() => JSON.parse(localStorage.getItem('zephyr-scenarios-v1') || 'null'))).toEqual([]);
});

test('Guide closes via Escape, Close guide and Open the workspace; Escape restores opener focus', async ({ page }) => {
  await open(page, 'overview');
  await page.locator('#help-button').focus(); await page.keyboard.press('Enter');
  await expect(page.locator('#guide-dialog')).toBeVisible();
  await page.keyboard.press('Escape');
  await expect(page.locator('#guide-dialog')).toBeHidden(); await expect(page.locator('#help-button')).toBeFocused();
  await page.locator('#help-button').click(); await page.getByRole('button', { name: 'Close guide', exact: true }).click();
  await expect(page.locator('#guide-dialog')).toBeHidden();
  await page.locator('#help-button').click(); await page.getByRole('button', { name: 'Open the workspace', exact: true }).click();
  await expect(page.locator('#guide-dialog')).toBeHidden();
  await navigate(page, 'lab'); await page.locator('#save-scenario').click();
  await page.getByRole('button', { name: 'Close save dialog', exact: true }).click();
  await expect(page.locator('#save-dialog')).toBeHidden();
});

test('Both theme controls persist the selected theme after reload', async ({ page }) => {
  await open(page, 'overview'); await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.locator('#theme-top').click(); await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.reload({ waitUntil: 'load' }); await expect(page.locator('html')).toHaveAttribute('data-theme', 'light');
  await page.locator('#theme-toggle').click(); await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await page.reload({ waitUntil: 'load' }); await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});

test('Scenario JSON and curve CSV contain complete assumptions and independently checked numbers', async ({ page }, info) => {
  await open(page, 'lab');
  const scenario = await download(page, '#export-scenario', info);
  expect(scenario.name).toBe('ZephyrTrade-scenario.json');
  const document = JSON.parse(scenario.text);
  expect(document.schema_version).toBe(1); expect(document.application).toBe('ZephyrTrade Champion');
  expect(document.data_kind).toBe('user_assumptions_not_live'); expect(document.input).toEqual(DEFAULT_INPUT);
  expect(document.calculated.offer_mw).toBe(9);
  expect(Math.abs(document.calculated.expected_revenue_dkk - expectedRevenue(DEFAULT_INPUT, 9))).toBeLessThan(1e-8);
  expect(document.calculated.critical_quantile).toBeCloseTo(110 / 300, 12);
  const curve = await download(page, '#export-curve', info);
  expect(curve.name).toBe('ZephyrTrade-revenue-curve.csv');
  const rows = csv(curve.text), offers = rows.map(row => value(row, 'offer_mw'));
  expect(offers).toEqual([0, ...DEFAULT_INPUT.scenarios, 30]);
  for (const row of rows) {
    expect(row.data_kind).toBe('user_assumptions'); expect(value(row, 'interval_hours')).toBe(1);
    expect(Math.abs(value(row, 'expected_revenue_dkk') - expectedRevenue(DEFAULT_INPUT, value(row, 'offer_mw')))).toBeLessThan(1e-8);
  }
  expect(Math.max(...rows.map(row => value(row, 'expected_revenue_dkk')))).toBeCloseTo(document.calculated.expected_revenue_dkk, 8);
});

test('ISS-012: privacy disclosure, provenance bytes and served script inventory agree', async ({ page, audit }, info) => {
  await open(page, 'method');
  const content = await page.locator('#page-content').innerText();
  expect(content).not.toMatch(/no remote fonts|no analytics|no CDNs/i);
  expect(content).toContain('hosted site is delivered through Cloudflare');
  expect(content).toContain('network-error reporting policy');
  expect(content).toContain('configuration alone does not establish that a report was sent');
  await expect(page.locator('script[src]')).toHaveCount(0);
  expect(audit.requests.filter(request => /cloudflareinsights|beacon\.min\.js/i.test(request.url))).toEqual([]);
  const exported = await download(page, '#export-provenance', info);
  expect(exported.name).toBe('ZephyrTrade-provenance.json');
  const document = JSON.parse(exported.text);
  expect(document.data_kind).toBe('Supplied synthetic research backtest');
  expect(Number.isFinite(Date.parse(document.source_generated_at))).toBe(true);
  expect(document.quality.rows).toBe(3888); expect(document.quality.excluded_hours_between_endpoints).toBe(53);
  expect(document.quality.revenue_values_checked).toBe(34992); expect(document.sources).toHaveLength(2);
  for (const source of document.sources) {
    expect(source.path).toMatch(/^artifacts\/phase[23]\/.*\.csv\.gz$/);
    expect(source.sha256).toMatch(/^[a-f0-9]{64}$/);
    await expect(page.locator('#page-content')).toContainText(source.path);
    await expect(page.locator('#page-content')).toContainText(source.sha256);
  }
});

test('Python setup control opens Method without application API or WebSocket traffic', async ({ page, audit }) => {
  await open(page, 'lab'); await page.locator('#verify-python').click();
  await expect(page).toHaveURL(address('method'));
  await expect(page.locator('#page-title')).toHaveText(ROUTES.method);
  await expect(page.locator('#python-setup')).toBeVisible();
  expect(audit.requests.filter(request => new URL(request.url).pathname.startsWith('/api/'))).toEqual([]);
  expect(audit.websockets).toEqual([]);
});

test('Rapid route switching settles on Data with finite results and one selected navigation item', async ({ page }) => {
  await open(page, 'overview');
  for (const route of ['lab', 'models', 'method', 'overview', 'data', 'lab', 'method', 'models', 'overview', 'data'])
    await page.locator(`nav a[href="#${route}"]`).click();
  await expect(page).toHaveURL(address('data')); await expect(page.locator('#page-title')).toHaveText(ROUTES.data);
  await expect(page.locator('nav [aria-current="page"]')).toHaveCount(1);
  await expect(page.locator('#page-content tbody tr')).toHaveCount(25); await cleanNumericOutput(page);
});

test('Already-loaded application still navigates and calculates after the context goes offline', async ({ page, context }) => {
  await open(page, 'overview'); await context.setOffline(true);
  try {
    for (const route of ['models', 'data', 'method', 'lab'] as Route[]) await navigate(page, route);
    await fillLab(page, { scenarios: '0,30', probabilities: '0.2,0.8' });
    await calculate(page); await result(page, 30, 8940); await navigate(page, 'overview'); await cleanNumericOutput(page);
  } finally { await context.setOffline(false); }
});
