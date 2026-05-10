import { test, expect, Page } from '@playwright/test';

/**
 * 全自动 AI vs AI 对战测试
 * 通过 DOM 操作（选牌+点击按钮）实现全自动游戏，不依赖 WebSocket 劫持
 */

async function createGame(request: any) {
  const roomRes = await request.post('http://localhost:8765/api/rooms', {
    data: { name: 'Auto AI Game' },
  });
  const room = await roomRes.json();
  const roomId = room.room_id || room.id;
  const p1 = 'ai1_' + Date.now();
  const p2 = 'ai2_' + Date.now();

  await request.post(`http://localhost:8765/api/rooms/${roomId}/join`, {
    data: { player_id: p1 },
  });
  await request.post(`http://localhost:8765/api/rooms/${roomId}/join`, {
    data: { player_id: p2 },
  });
  await request.post(`http://localhost:8765/api/rooms/${roomId}/start`);

  return { roomId, p1, p2 };
}

/**
 * 注入自动游戏脚本到页面
 * 通过轮询检测是否轮到自己，然后自动选牌+出牌
 */
function injectAutoPlayer() {
  // 轮询间隔（毫秒）
  const POLL_MS = 1200;
  let interval: ReturnType<typeof setInterval> | null = null;

  function log(msg: string) {
    console.log('[AutoPlayer]', msg);
  }

  function safeQuerySelector(selector: string): HTMLElement | null {
    try {
      return document.querySelector(selector) as HTMLElement | null;
    } catch {
      return null;
    }
  }

  function tryDiscard(): boolean {
    try {
      // 检查是否轮到自己（discard 按钮可点击）
      const discardBtn = safeQuerySelector('#btn-discard') as HTMLButtonElement | null;
      if (!discardBtn || discardBtn.disabled) return false;

      // 检查是否在自己的出牌阶段
      const centerPhase = safeQuerySelector('#center-phase');
      const phaseText = centerPhase ? centerPhase.textContent.trim().toLowerCase() : '';
      if (!phaseText.includes('discard') && !phaseText.includes('出牌')) {
        // 也可能是自动阶段，不在出牌
      }

      // 选第一张手牌
      const firstTile = safeQuerySelector('#my-hand .tile');
      if (!firstTile) return false;
      (firstTile as HTMLElement).click();

      // 等待一小会儿再点出牌
      setTimeout(() => {
        const btn = safeQuerySelector('#btn-discard') as HTMLButtonElement | null;
        if (btn && !btn.disabled) btn.click();
      }, 150);

      return true;
    } catch (e) {
      return false;
    }
  }

  function trySkip(): boolean {
    try {
      // 检查是否有声索窗口（claim overlay 可见）
      const overlay = safeQuerySelector('#claim-overlay');
      if (!overlay) return false;
      const isHidden = overlay.classList.contains('hidden');
      if (isHidden) return false;

      // 有声索窗口，点击过（skip）按钮
      // 先找 btn-skip，如果没有就点 overlay 里的任意按钮
      const skipBtn = safeQuerySelector('#btn-skip') as HTMLButtonElement | null;
      if (skipBtn && !skipBtn.disabled) {
        skipBtn.click();
        return true;
      }

      // 找到声索窗口里的任意按钮并点击（通常是"过"）
      const buttons = overlay.querySelectorAll('button');
      for (const btn of Array.from(buttons)) {
        const b = btn as HTMLButtonElement;
        if (!b.disabled && b.offsetParent !== null) {
          // 跳过 WIN 按钮（不主动荣和）
          if (b.textContent && b.textContent.includes('胡')) continue;
          b.click();
          return true;
        }
      }
      return false;
    } catch {
      return false;
    }
  }

  function tryClaimChow(): boolean {
    try {
      const overlay = safeQuerySelector('#claim-overlay');
      if (!overlay || overlay.classList.contains('hidden')) return false;

      // 找吃按钮
      const chowBtn = safeQuerySelector('#btn-chow') as HTMLButtonElement | null;
      if (chowBtn && !chowBtn.disabled) {
        chowBtn.click();
        return true;
      }
      return false;
    } catch {
      return false;
    }
  }

  function isGameEnded(): boolean {
    try {
      const overlay = safeQuerySelector('#game-over-modal');
      return !!overlay && !overlay.classList.contains('hidden');
    } catch {
      return false;
    }
  }

  function start() {
    log('AutoPlayer started');
    let stepCount = 0;
    const MAX_STEPS = 400; // 约 8 分钟

    interval = setInterval(() => {
      stepCount++;
      if (stepCount > MAX_STEPS) {
        log('Max steps reached, stopping');
        if (interval) clearInterval(interval);
        return;
      }

      if (isGameEnded()) {
        log('Game ended, stopping');
        if (interval) clearInterval(interval);
        return;
      }

      // 优先级：1. 声索窗口 2. 出牌
      const skipped = trySkip();
      if (!skipped) {
        tryClaimChow();
      }
      tryDiscard();

    }, POLL_MS);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
}

test.describe('全自动 AI vs AI 游戏流程', () => {

  test.setTimeout(300000); // 5 分钟超时

  test('AI vs AI 完整游戏自动跑完', async ({ browser, request }) => {
    const { roomId, p1, p2 } = await createGame(request);

    const ctx = await browser.newContext();
    const page1 = await ctx.newPage();
    const page2 = await ctx.newPage();

    await page1.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(p1)}`,
      { waitUntil: 'domcontentloaded' }
    );
    await page2.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(p2)}`,
      { waitUntil: 'domcontentloaded' }
    );

    // 等待游戏页面加载完成
    await page1.waitForSelector('#my-hand .tile', { timeout: 15000 });
    await page2.waitForSelector('#my-hand .tile', { timeout: 15000 });

    // 等待 discard 按钮可用（不等特定文字，直接等按钮 enabled）
    await page1.waitForFunction(
      () => { const b = document.querySelector('#btn-discard'); return b && !b.disabled; },
      { timeout: 30000 }
    );

    // 递归 auto-player：不依赖 phase 文字，直接等 btn-discard enabled
    const autoScript = `
    async function autoStep() {
      try {
        // 声索窗口处理
        const ov = document.querySelector('#claim-overlay');
        if (ov && !ov.classList.contains('hidden')) {
          const btns = Array.from(ov.querySelectorAll('button'));
          for (const btn of btns) {
            const b = btn;
            if (!b.disabled && b.offsetParent !== null && b.textContent && !b.textContent.includes('胡')) {
              b.click(); return;
            }
          }
          // 声索窗口打开但没有可点的（除胡外），跳过
          return;
        }
        // 等 discard 按钮可用
        const btn = document.querySelector('#btn-discard');
        if (!btn || btn.disabled) {
          setTimeout(autoStep, 300); return;
        }
        // 选牌
        let tile = document.querySelector('#my-hand .tile.selected') ||
                    document.querySelector('#my-hand .tile');
        if (!tile) { setTimeout(autoStep, 300); return; }
        tile.click();
        // 等 DOM 更新
        await new Promise(r => setTimeout(r, 200));
        const b2 = document.querySelector('#btn-discard');
        if (b2 && !b2.disabled) b2.click();
      } catch(e) {}
      setTimeout(autoStep, 300);
    }
    (window as any).__autoPlayerStop = () => {};
    autoStep();
    `;

    await page1.evaluate(autoScript);
    await page2.evaluate(autoScript);

    // 等待游戏结束（最多 4 分钟）
    await page1.waitForFunction(
      "document.querySelector('#game-over-modal') && !document.querySelector('#game-over-modal').classList.contains('hidden')",
      { timeout: 240000 }
    );

    const modalVisible = await page1.evaluate(
      () => !!document.querySelector('#game-over-modal:not(.hidden)')
    );
    expect(modalVisible).toBe(true);

    const winner = await page1.locator('#winner-name').textContent();
    console.log(`游戏结束！赢家: ${winner}`);

    await ctx.close();
  });

  test('游戏过程中手牌数保持在合理范围', async ({ browser, request }) => {
    const { roomId, p1, p2 } = await createGame(request);

    const ctx = await browser.newContext();
    const page1 = await ctx.newPage();

    await page1.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(p1)}`,
      { waitUntil: 'domcontentloaded' }
    );
    await page1.waitForSelector('#my-hand .tile', { timeout: 15000 });

    // 等待进入"出牌"阶段
    await page1.waitForFunction(
      () => { const p = document.querySelector('#center-phase'); return p && /discard|出牌|draw|摸牌/i.test(p.textContent || ''); },
      { timeout: 20000 }
    );

    const autoScript = `
    async function autoStep() {
      try {
        const ov = document.querySelector('#claim-overlay');
        if (ov && !ov.classList.contains('hidden')) {
          const btns = ov.querySelectorAll('button');
          for (const btn of Array.from(btns)) {
            const b = btn;
            if (!b.disabled && b.offsetParent !== null && b.textContent && !b.textContent.includes('胡')) {
              b.click(); return;
            }
          }
        }
        const phase = document.querySelector('#center-phase');
        if (!phase || !/(discard|出牌|draw|摸牌)/i.test(phase.textContent || '')) {
          setTimeout(autoStep, 200); return;
        }
        const btn = document.querySelector('#btn-discard');
        if (!btn || btn.disabled) {
          setTimeout(autoStep, 200); return;
        }
        let tile = document.querySelector('#my-hand .tile.selected') ||
                    document.querySelector('#my-hand .tile');
        if (!tile) { setTimeout(autoStep, 200); return; }
        tile.click();
        await new Promise(r => setTimeout(r, 150));
        const b2 = document.querySelector('#btn-discard');
        if (b2 && !b2.disabled) b2.click();
      } catch(e) {}
      setTimeout(autoStep, 200);
    }
    autoStep();
    `;

    await page1.evaluate(autoScript);

    // 等待几轮，收集手牌数据
    const handCounts: number[] = [];
    for (let i = 0; i < 15; i++) {
      await page1.waitForTimeout(4000);
      const count = await page1.locator('#my-hand .tile').count();
      handCounts.push(count);

      const ended = await page1.evaluate(
        () => !!document.querySelector('#game-over-modal:not(.hidden)')
      );
      if (ended) {
        console.log(`游戏在第 ${i + 1} 轮结束`);
        break;
      }
    }

    console.log(`手牌变化: ${handCounts.join(' -> ')}`);
    for (const c of handCounts) {
      expect(c).toBeGreaterThanOrEqual(13);
      expect(c).toBeLessThanOrEqual(18);
    }

    await ctx.close();
  });

  test('游戏结束后展示完整结算', async ({ browser, request }) => {
    const { roomId, p1, p2 } = await createGame(request);

    const ctx = await browser.newContext();
    const page1 = await ctx.newPage();

    await page1.goto(
      `http://localhost:8765/static/game.html?room=${encodeURIComponent(roomId)}&player=${encodeURIComponent(p1)}`,
      { waitUntil: 'domcontentloaded' }
    );
    await page1.waitForSelector('#my-hand .tile', { timeout: 15000 });

    // 等待进入"出牌"阶段
    await page1.waitForFunction(
      () => { const p = document.querySelector('#center-phase'); return p && /discard|出牌|draw|摸牌/i.test(p.textContent || ''); },
      { timeout: 20000 }
    );

    const autoScript3 = `
    async function autoStep() {
      try {
        const ov = document.querySelector('#claim-overlay');
        if (ov && !ov.classList.contains('hidden')) {
          const btns = ov.querySelectorAll('button');
          for (const btn of Array.from(btns)) {
            const b = btn;
            if (!b.disabled && b.offsetParent !== null && b.textContent && !b.textContent.includes('胡')) {
              b.click(); return;
            }
          }
        }
        const phase = document.querySelector('#center-phase');
        if (!phase || !/(discard|出牌|draw|摸牌)/i.test(phase.textContent || '')) {
          setTimeout(autoStep, 200); return;
        }
        const btn = document.querySelector('#btn-discard');
        if (!btn || btn.disabled) {
          setTimeout(autoStep, 200); return;
        }
        let tile = document.querySelector('#my-hand .tile.selected') ||
                    document.querySelector('#my-hand .tile');
        if (!tile) { setTimeout(autoStep, 200); return; }
        tile.click();
        await new Promise(r => setTimeout(r, 150));
        const b2 = document.querySelector('#btn-discard');
        if (b2 && !b2.disabled) b2.click();
      } catch(e) {}
      setTimeout(autoStep, 200);
    }
    autoStep();
    `;

    await page1.evaluate(autoScript3);

    await page1.waitForFunction(
      "document.querySelector('#game-over-modal') && !document.querySelector('#game-over-modal').classList.contains('hidden')",
      { timeout: 540000 }
    );

    await expect(page1.locator('#winner-name')).toBeVisible();
    await expect(page1.locator('.scores-table')).toBeVisible();
    const scores = await page1.locator('#my-player-score').textContent();
    expect(scores).toBeTruthy();
    console.log(`结算分数: ${scores}`);

    await ctx.close();
  });
});
