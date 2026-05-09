import { test as base, Page } from '@playwright/test';

/**
 * Custom fixture that provides a player ID and helpers for room management.
 * The backend is automatically started by playwright.config.ts webServer.
 */
class PlayerFixtures {
  constructor(
    public playerId: string,
  ) {}

  async createRoom(page: Page, name = 'E2E Test Room') {
    // Navigate to lobby
    await page.goto('http://localhost:8765/static/index.html');

    // Wait for lobby to load
    await page.waitForSelector('#btn-create-room');

    // Click create room (which uses prompt - we intercept it)
    page.on('dialog', dialog => dialog.accept(name));
    await page.click('#btn-create-room');

    // Wait for redirect to game page
    await page.waitForURL(/\/game\.html\?room=/);
  }

  async joinRoom(page: Page, roomId: string) {
    await page.goto(`http://localhost:8765/static/index.html`);
    await page.waitForSelector('#rooms-tbody');

    // Find and click join button for the room
    const joinBtn = page.locator(`button:has-text("Join")`).first();
    await joinBtn.click();

    await page.waitForURL(/\/game\.html\?room=/);
  }
}

// Extend Playwright's test type
export { PlayerFixtures };
