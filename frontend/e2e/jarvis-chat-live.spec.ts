import { test } from '@playwright/test';

// Round-trip réel : envoie un message, capture pendant la réponse + à la fin.
test('jarvis chat round-trip', async ({ page }) => {
  test.setTimeout(120000);
  await page.setViewportSize({ width: 1440, height: 900 });
  await page.addInitScript(() => {
    localStorage.setItem('openjarvis-settings', JSON.stringify({ apiUrl: 'http://localhost:8000' }));
    localStorage.setItem('openjarvis-optin-seen', 'true');
  });

  await page.goto('/chat');
  await page.waitForTimeout(2000);

  const input = page.getByPlaceholder(/Message/i).first();
  await input.fill('Dis bonjour en une courte phrase.');
  await input.press('Enter');

  // Pendant la réponse (orbe en header + "JARVIS RÉPOND")
  await page.waitForTimeout(6000);
  await page.screenshot({ path: 'e2e/jarvis-chat-responding.png' });

  // Réponse complète (Ollama qwen3:14b peut être lent)
  await page.waitForTimeout(45000);
  await page.screenshot({ path: 'e2e/jarvis-chat-done.png' });
});
