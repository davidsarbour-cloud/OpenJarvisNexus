import { test } from '@playwright/test';

// Screenshot LIVE du Command Center (vraies valeurs depuis le backend :8000).
test('command center hardware HUD', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem('openjarvis-settings', JSON.stringify({ apiUrl: 'http://localhost:8000' }));
    localStorage.setItem('openjarvis-optin-seen', 'true');
  });

  await page.goto('/');
  // Laisser ~5 cycles de poll (2s) pour remplir les sparklines.
  await page.waitForTimeout(11000);

  // Capture directe de la grille HARDWARE (celle qui contient Resource Monitor).
  const grid = page.locator('div.grid').filter({ has: page.getByText('RESOURCE MONITOR') }).first();
  await grid.scrollIntoViewIfNeeded();
  await page.waitForTimeout(800);
  await grid.screenshot({ path: 'e2e/hardware-hud.png' });
});
