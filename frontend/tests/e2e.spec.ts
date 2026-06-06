import { test, expect } from '@playwright/test';

test.beforeEach(async ({ page }, testInfo) => {
  // Set onboarding as completed by default
  if (!testInfo.title.includes('Onboarding wizard')) {
    await page.addInitScript(() => {
      window.localStorage.setItem('asterion_onboarding_completed', 'true');
    });
  }

  // Mock all API calls
  await page.route('**/api/health', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        status: 'ok',
        app: 'asterion-backend',
        uptime_seconds: 123.45,
        database: { status: 'connected' },
        ollama: { status: 'connected' },
        schema_version: 3,
        privacy: { level: 'local' },
      }),
    });
  });

  await page.route('**/api/models', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        models: [{ name: 'llama3.2', size: 2000000000, modified_at: '2026-06-06T12:00:00Z' }],
        privacy_level: 'local',
      }),
    });
  });

  await page.route('**/api/rooms', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-room',
          name: 'Кодинг',
          color: '#7c6dfa',
          allowed_models: [],
          memory_policy: 'session',
          retention_days: 30,
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'default',
            name: 'Общая комната',
            color: '#7c6dfa',
            allowed_models: [],
            memory_policy: 'session',
            retention_days: 30,
          },
        ]),
      });
    }
  });

  await page.route('**/api/memory/**', async (route) => {
    if (route.request().method() === 'POST') {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          id: 'test-mem-id',
          room_id: 'default',
          content: 'Использовать Svelte 5',
          source: 'manual',
          created_at: '2026-06-06T12:00:00Z',
        }),
      });
    } else {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: 'mem-1',
            room_id: 'default',
            content: 'Использовать Svelte 5',
            source: 'manual',
            created_at: '2026-06-06T12:00:00Z',
          },
        ]),
      });
    }
  });

  await page.route('**/api/chat/conversations', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'conv-1',
          room_id: 'default',
          title: 'Тестовый диалог',
          created_at: '2026-06-06T12:00:00Z',
          message_count: 2,
        },
      ]),
    });
  });

  await page.route('**/api/chat/conversations/conv-1/messages', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([
        {
          id: 'msg-1',
          conv_id: 'conv-1',
          role: 'user',
          content: 'Привет, модель!',
          ts: '2026-06-06T12:00:01Z',
        },
        {
          id: 'msg-2',
          conv_id: 'conv-1',
          role: 'assistant',
          content: 'Привет! Я локальная модель.',
          ts: '2026-06-06T12:00:02Z',
        },
      ]),
    });
  });

  await page.route('**/api/agents/catalog', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        agents: [
          {
            id: 'chat-orchestrator',
            name: 'Оркестратор чата',
            description: 'Базовый агент',
            privacy_level: 'local',
          },
        ],
        skills: [],
      }),
    });
  });

  await page.route('**/api/agents/catalog/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ valid: true, errors: [] }),
    });
  });

  await page.route('**/api/plugins', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/artifacts', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/audit/logs', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify([]),
    });
  });

  await page.route('**/api/privacy/analyze', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ level: 'green', items: [] }),
    });
  });
});

test('1. App shell navigation', async ({ page }) => {
  await page.goto('/');

  // Verify Sidecar status indicator is shown
  await expect(page.locator('.system-meter')).toContainText('Sidecar: ok');

  // Go to Vault tab
  await page.click('aside.side-rail nav button:has-text("База Знаний (Vault)")');
  await expect(page.locator('h1')).toContainText('Хранилище знаний');

  // Go to System tab
  await page.click('aside.side-rail nav button:has-text("Система")');
  await expect(page.locator('h1')).toContainText('Консоль конфигураций');

  // Go back to Chat
  await page.click('aside.side-rail nav button:has-text("Умный Чат")');
  await expect(page.locator('h1')).toContainText('Интерактивный чат');
});

test('2. Command palette overlay and shortcuts', async ({ page }) => {
  await page.goto('/');

  // Press Ctrl+K to open Command Palette
  await page.keyboard.press('Control+KeyK');

  // Verify command palette is open
  const paletteInput = page.locator('#cmd-palette-input');
  await expect(paletteInput).toBeVisible();

  // Search for "тему"
  await paletteInput.fill('тему');
  const themeItem = page.locator('#cmd-item-cmd-theme');
  await expect(themeItem).toBeVisible();

  // Press enter to execute
  await page.keyboard.press('Enter');

  // Palette should close and theme toggled toast should be visible
  await expect(paletteInput).not.toBeVisible();
  await expect(page.locator('.toast-container')).toContainText('Тема оформления переключена');
});

test('3. Room creation and memory insertion', async ({ page }) => {
  await page.goto('/');

  // Left Context Panel should be visible
  await expect(page.locator('aside.left-panel')).toBeVisible();

  // Create room
  const roomInput = page.locator('aside.left-panel input[placeholder="Название..."]');
  await roomInput.fill('Кодинг');
  await roomInput.press('Enter');

  // Toast should show room created
  await expect(page.locator('.toast-container')).toContainText('Комната "Кодинг" создана');

  // Insert memory
  const memoryInput = page.locator('aside.left-panel input[placeholder="Запомнить..."]');
  await memoryInput.fill('Использовать Svelte 5');
  await memoryInput.press('Enter');

  // Memory should be displayed in the list
  await expect(page.locator('.memory-ledger')).toContainText('Использовать Svelte 5');
});

test('4. Onboarding wizard walkthrough', async ({ page }) => {
  // Clear localStorage before load so onboarding appears
  await page.goto('/');
  await page.evaluate(() => window.localStorage.clear());
  await page.reload();

  const wizard = page.locator('.onboarding-overlay');
  await expect(wizard).toBeVisible();

  // Step 1: Welcome. Click "Продолжить"
  await wizard.locator('button:has-text("Продолжить")').click();

  // Step 2: System configuration. Click "Продолжить"
  await wizard.locator('button:has-text("Продолжить")').click();

  // Step 3: Room configuration. Click "Создать комнату"
  await wizard.locator('button:has-text("Создать комнату")').click();

  // Step 4: Finished. Click "Начать работу"
  await wizard.locator('button:has-text("Начать работу")').click();

  // Wizard should close
  await expect(wizard).not.toBeVisible();
});
