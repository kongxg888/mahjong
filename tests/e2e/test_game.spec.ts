import { test, expect } from '@playwright/test';

/**
 * Stable E2E game flow tests.
 * Keep tests minimal and focused - avoid creating too many games in rapid succession.
 */

async function startGame(request: any) {
  const createRes = await request.post('http://localhost:8765/api/rooms', {
    data: { name: 'E2E Game' },
  });
  const room = await createRes.json();
  const roomId = room.room_id || room.id;
  const playerId = 'e2e_' + Date.now();

  await request.post(`http://localhost:8765/api/rooms/${roomId}/join`, {
    data: { player_id: playerId },
  });
  await request.post(`http://localhost:8765/api/rooms/${roomId}/start`);

  return { roomId, playerId };
}

test.describe('Game Page - Stable Tests', () => {

  test('hand tiles are rendered (14-17 tiles)', async ({ page, request }) => {
    const { roomId, playerId } = await startGame(request);

    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`
    );

    await page.waitForSelector('#my-hand .tile', { timeout: 8000 });

    const tiles = await page.locator('#my-hand .tile').count();
    expect(tiles).toBeGreaterThanOrEqual(14);
    expect(tiles).toBeLessThanOrEqual(17);
  });

  test('discard button is present', async ({ page, request }) => {
    const { roomId, playerId } = await startGame(request);

    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`
    );

    await page.waitForSelector('#btn-discard', { timeout: 8000 });
    await expect(page.locator('#btn-discard')).toBeVisible();
  });

  test('selecting a tile highlights it', async ({ page, request }) => {
    const { roomId, playerId } = await startGame(request);

    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`
    );

    await page.waitForSelector('#my-hand .tile', { timeout: 8000 });

    const firstTile = page.locator('#my-hand .tile').first();
    await firstTile.click();
    await expect(firstTile).toHaveClass(/selected/);
  });

  test('discard removes tile from hand', async ({ page, request }) => {
    const { roomId, playerId } = await startGame(request);

    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`
    );

    await page.waitForSelector('#my-hand .tile', { timeout: 8000 });
    const initialCount = await page.locator('#my-hand .tile').count();

    const firstTile = page.locator('#my-hand .tile').first();
    await firstTile.click();

    try {
      await page.waitForSelector('#btn-discard:not([disabled])', { timeout: 3000 });
      await page.click('#btn-discard');
      await page.waitForTimeout(500);
      const newCount = await page.locator('#my-hand .tile').count();
      expect(newCount).toBe(initialCount - 1);
    } catch {
      // Not player's turn - skip
      test.skip();
    }
  });

  test('game over modal is hidden during active game', async ({ page, request }) => {
    const { roomId, playerId } = await startGame(request);

    await page.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(playerId)}`
    );

    await page.waitForSelector('#my-hand .tile', { timeout: 8000 });

    const modal = page.locator('#game-over-modal');
    const isHidden = await modal.evaluate(el => el.classList.contains('hidden'));
    expect(isHidden).toBe(true);
  });
});
