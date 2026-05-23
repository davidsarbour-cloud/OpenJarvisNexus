import { test } from '@playwright/test';

// Screenshot de la page conversation JARVIS (orbe + nav du haut uniforme).
test('jarvis chat page', async ({ page }) => {
  test.setTimeout(60000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem('openjarvis-optin-seen', 'true');
  });
  await page.goto('/chat');
  await page.waitForTimeout(2500);
  await page.screenshot({ path: 'e2e/jarvis-chat.png' });
});
