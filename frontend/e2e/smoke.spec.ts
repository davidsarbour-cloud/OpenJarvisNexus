import { test, expect } from '@playwright/test';

// Smoke tests Phase 6 — vérifient que le Command Center et l'Orbital View
// montent sans crash, et capturent une preuve visuelle.

test('Command Center (/) monte', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('/', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#root')).toBeVisible();
  // Ferme la modale OptInModal ("Share Your Savings") si présente
  await page.getByText('No Thanks').click({ timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(1500);
  await page.screenshot({ path: 'e2e/screenshots/command-center.png', fullPage: true });
  expect(errors, `erreurs JS: ${errors.join(' | ')}`).toHaveLength(0);
});

test('Orbital View (/orbital) monte', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(String(e)));
  await page.goto('/orbital', { waitUntil: 'domcontentloaded' });
  await expect(page.locator('#root')).toBeVisible();
  // Ferme la modale OptInModal ("Share Your Savings") si présente
  await page.getByText('No Thanks').click({ timeout: 4000 }).catch(() => {});
  await page.waitForTimeout(2500); // laisse le canvas R3F s'initialiser
  await page.screenshot({ path: 'e2e/screenshots/orbital.png', fullPage: true });
  expect(errors, `erreurs JS: ${errors.join(' | ')}`).toHaveLength(0);
});
