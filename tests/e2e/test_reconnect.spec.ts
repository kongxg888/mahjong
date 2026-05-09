import { test, expect } from '@playwright/test';

/**
 * Minimal reconnect tests.
 */

test.describe('Reconnection', () => {

  test('player can reconnect to same game', async ({ browser, request }) => {
    // Create and start game
    const createRes = await request.post('http://localhost:8765/api/rooms', {
      data: { name: 'Reconnect Test' },
    });
    const room = await createRes.json();
    const roomId = room.room_id || room.id;
    const playerId = 'e2e_rec_' + Date.now();

    await request.post(`http://localhost:8765/api/rooms/${roomId}/join`, {
      data: { player_id: playerId },
    });
    await request.post(`http://localhost:8765/api/rooms/${roomId}/start`);

    // First connection
    const context = await browser.newContext();
    const page = await context.newPage();
    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`,
      { waitUntil: 'domcontentloaded' }
    );
    await page.waitForSelector('#my-hand .tile', { timeout: 8000 });
    const initialTiles = await page.locator('#my-hand .tile').count();
    await page.close();
    await context.close();

    // Reconnect with same player
    const context2 = await browser.newContext();
    const page2 = await context2.newPage();
    await page2.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`,
      { waitUntil: 'domcontentloaded' }
    );
    await page2.waitForSelector('#my-hand .tile', { timeout: 8000 });
    const reconnectTiles = await page2.locator('#my-hand .tile').count();
    expect(reconnectTiles).toBeGreaterThanOrEqual(13);
    await page2.close();
    await context2.close();
  });
});
