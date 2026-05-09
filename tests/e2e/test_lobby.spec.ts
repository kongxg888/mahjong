import { test, expect } from '@playwright/test';

/**
 * Lobby E2E tests - minimal reliable set.
 */

test.describe('Lobby Page', () => {

  test('lobby page loads with title', async ({ page }) => {
    await page.goto('http://localhost:8765/static/index.html', { waitUntil: 'domcontentloaded' });
    const heading = page.locator('h1');
    await expect(heading).toBeVisible({ timeout: 10000 });
    await expect(heading).toContainText('麻將');
  });

  test('create room button is present', async ({ page }) => {
    await page.goto('http://localhost:8765/static/index.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#btn-create-room')).toBeVisible({ timeout: 10000 });
  });

  test('rooms table is present', async ({ page }) => {
    await page.goto('http://localhost:8765/static/index.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('.rooms-table')).toBeVisible({ timeout: 10000 });
  });

  test('player ID is displayed', async ({ page }) => {
    await page.goto('http://localhost:8765/static/index.html', { waitUntil: 'domcontentloaded' });
    await expect(page.locator('#player-id-display')).toBeVisible({ timeout: 10000 });
    const text = await page.locator('#player-id-display').textContent();
    expect(text).toMatch(/^p_/);
  });
});
