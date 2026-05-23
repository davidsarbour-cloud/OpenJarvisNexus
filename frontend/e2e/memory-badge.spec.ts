import { test } from '@playwright/test';

// Rendu seul : on injecte une conversation avec telemetry.memory dans le store
// (localStorage) puis on screenshot le badge — pas besoin de backend/Ollama.
test('memory badge renders in XRayFooter', async ({ page }) => {
  await page.addInitScript(() => {
    const now = Date.now();
    const conv = {
      id: 'conv_demo',
      title: 'Memory demo',
      createdAt: now,
      updatedAt: now,
      model: 'qwen3:14b',
      messages: [
        {
          id: 'm1',
          role: 'user',
          content:
            "J'ai une erreur traceback exception dans mon pipeline forge, peux-tu analyser l'architecture et me dire d'ou vient le bug ?",
          timestamp: now,
        },
        {
          id: 'm2',
          role: 'assistant',
          content:
            "D'apres le brain, le bug vient de la resolution OLLAMA_HOST (::1 sur Windows). Voici l'analyse complete et le correctif recommande.",
          timestamp: now + 1,
          usage: { prompt_tokens: 1240, completion_tokens: 320, total_tokens: 1560 },
          telemetry: {
            engine: 'ollama',
            model_id: 'qwen3:14b',
            total_ms: 1840,
            tokens_per_sec: 44,
            memory: { retrieved: true, fragments: 3, ms: 42, confidence: 87 },
          },
        },
      ],
    };
    localStorage.setItem(
      'openjarvis-conversations',
      JSON.stringify({ version: 1, conversations: { conv_demo: conv }, activeId: 'conv_demo' }),
    );
    localStorage.setItem('openjarvis-optin-seen', 'true');
  });

  await page.goto('/chat');
  await page.waitForTimeout(1500);

  // Capture repliée
  await page.screenshot({ path: 'e2e/memory-badge-collapsed.png', fullPage: true });

  // Etendre le footer X-ray (le resume contient "vault fragments")
  const footer = page.getByText(/vault fragments/i).first();
  await footer.click({ timeout: 5000 }).catch(() => {});
  await page.waitForTimeout(500);
  await page.screenshot({ path: 'e2e/memory-badge-expanded.png', fullPage: true });
});
