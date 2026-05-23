import { test } from '@playwright/test';

// Screenshot du dashboard Grafana auto-provisionné (données live via Prometheus).
test('grafana hardware dashboard', async ({ page }) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 1500, height: 950 });

  // Login Grafana (admin/admin)
  await page.goto('http://localhost:3001/login');
  await page.fill('input[name="user"]', 'admin');
  await page.fill('input[name="password"]', 'admin');
  await page.click('button[type="submit"]');
  await page.waitForTimeout(3000);

  // Skip "change password" si proposé
  const skip = page.getByText(/^Skip$/i).first();
  if (await skip.isVisible().catch(() => false)) {
    await skip.click().catch(() => {});
  }
  await page.waitForTimeout(2000);

  // Ouvrir le dashboard provisionné
  await page.goto('http://localhost:3001/d/nexus9-hardware/nexus9-hardware?refresh=5s&from=now-15m&to=now');
  // Laisser les panels requêter + quelques refreshs
  await page.waitForTimeout(22000);
  await page.screenshot({ path: 'e2e/grafana-hardware.png', fullPage: true });
});
