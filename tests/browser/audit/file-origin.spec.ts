import { test, expect } from 'playwright/test';
import { resolve } from 'node:path';
import { pathToFileURL } from 'node:url';

const standalone = pathToFileURL(resolve(__dirname, '../../..', 'ZephyrTrade-Champion.html')).href;

test('portable file origin calculates and navigates offline without external traffic', async ({ page, context }) => {
  const pageErrors: string[] = [];
  const remoteRequests: string[] = [];
  page.on('pageerror', error => pageErrors.push(error.message));
  page.on('request', request => {
    const protocol = new URL(request.url()).protocol;
    if (!['file:', 'data:', 'blob:'].includes(protocol))
      remoteRequests.push(request.method() + ' ' + request.url());
  });
  await page.goto(standalone, { waitUntil: 'load' });
  await expect(page.locator('#fatal-error')).toBeHidden();
  await expect(page.locator('#page-title')).toHaveText('From wind to value.');
  await page.locator('nav a[href="#lab"]').click();
  await expect(page.locator('#optimal-offer')).toContainText('9.00');
  await page.locator('#scenarios').fill('0, 30');
  await page.locator('#probabilities').fill('0.2,0.8');
  await page.locator('#lab-form button[type="submit"]').click();
  await expect(page.locator('#lab-error')).toBeHidden();
  await expect(page.locator('#optimal-offer')).toContainText('30.00');
  await expect(page.locator('#expected-revenue')).toContainText('8,940.00');
  await context.setOffline(true);
  try {
    await page.locator('nav a[href="#models"]').click();
    await expect(page.locator('#page-title')).toHaveText('Let the evidence lead.');
    await page.locator('nav a[href="#lab"]').click();
    await expect(page.locator('#optimal-offer')).toContainText('30.00');
    await page.locator('#probabilities').fill('0.5,0.5');
    await page.locator('#lab-form button[type="submit"]').click();
    await expect(page.locator('#lab-error')).toBeHidden();
    await expect(page.locator('#optimal-offer')).toContainText('0.00');
  } finally {
    await context.setOffline(false);
  }
  expect(pageErrors).toEqual([]);
  expect(remoteRequests).toEqual([]);
});
