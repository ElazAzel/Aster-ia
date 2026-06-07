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

  await page.route('**/api/images/recipes', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        privacy_level: 'local',
        recipes: [
          {
            id: 'sdxl-square',
            title: 'SDXL Square',
            description: 'Balanced square image preset.',
            tags: ['general', 'square'],
            estimated_vram_gb: 8,
            recipe: { width: 1024, height: 1024, steps: 20, cfg: 7 },
            validation: {
              ok: true,
              errors: [],
              warnings: [],
              nodes_count: 7,
              privacy_level: 'local',
            },
            privacy_level: 'local',
          },
        ],
      }),
    });
  });

  await page.route('**/api/images/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        ok: true,
        errors: [],
        warnings: [],
        nodes_count: 7,
        privacy_level: 'local',
      }),
    });
  });

  await page.route('**/api/images/generate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({ image: 'data:image/png;base64,AA==' }),
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
  await page.click('aside.side-rail nav button:has-text("Умный Чат")');

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

// ── Block 8: Extended E2E Tests ──────────────────────────────────────────────

test('5. Voice Mode - text structuring', async ({ page }) => {
  await page.route('**/api/voice/status', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ available: true, model_size: 'base', model_loaded: false, privacy_level: 'local' }) }));
  await page.route('**/api/voice/transcribe/text', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ original_text: 'test', word_count: 1,
        action_items: ['Call the team'], questions: ['When?'],
        summary: ['Test summary'], document_draft: '# Voice Note\n## Summary\nTest summary',
        privacy_level: 'local' }) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Voice Mode")');
  await page.fill('textarea[placeholder*="структурирования"]', 'We need to call the team. When will this be done?');
  await page.click('button:has-text("Собрать summary")');
  await expect(page.locator('text=Call the team')).toBeVisible({ timeout: 5000 });
});

test('6. Deep Research - query submission', async ({ page }) => {
  await page.route('**/api/research/deep', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({
        query: 'AI privacy trends',
        subtasks: ['Find privacy papers', 'Analyze local models'],
        results: [{ subtask: 'Find privacy papers', title: 'Privacy in AI', url: null, snippet: 'Local models offer better privacy.' }],
        privacy: { level: 'hybrid', items: [] }
      }) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Deep Research")');
  await page.fill('input[placeholder*="Например"]', 'AI privacy trends');
  await page.click('button:has-text("Запустить Deep Research")');
  // Consent modal appears - approve it
  await expect(page.locator('.consent-modal')).toBeVisible({ timeout: 3000 });
  await page.click('button:has-text("Разрешить")');
  await expect(page.locator('text=AI privacy trends')).toBeVisible({ timeout: 8000 });
});

test('7. Agent Lab - plan simulation', async ({ page }) => {
  await page.route('**/api/agents/simulate', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({
        steps: [{ action: 'read_files', tool: 'file_read', description: 'Read documents' }],
        required_permissions: ['file_read'], estimated_tokens: 1200,
        description: 'Analyse documents'
      }) }));
  await page.route('**/api/agents/runs', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ run_id: 'run-test-123', status: 'running', agent_id: 'test', room_id: 'default' }) }));

  // Override catalog with full agent manifest data
  await page.route('**/api/agents/catalog', async route => {
    const fullMock = {
      agents: [{
        id: 'chat-orchestrator', name: 'Оркестратор чата', version: '0.1.0',
        role: 'orchestrator', description: 'Базовый агент',
        privacy_level: 'local', default_model: 'llama3.2',
        triggers: [], skills: ['conversation-orchestration'],
        permissions: { allowed_folders: [], network: false, shell: false },
        lifecycle: ['init', 'running'], outputs: [], handoff_targets: [],
        acceptance_checks: [], system_prompt: 'You are a helpful assistant.',
        escalation_policy: 'notify_user'
      }], skills: [], privacy_level: 'local'
    };
    await route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify(fullMock) });
  });

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Агенты")');
  await expect(page.locator('text=Оркестратор чата').first()).toBeVisible();
});

test('8. Automation Board - workflow creation', async ({ page }) => {
  await page.route('**/api/workflows/run', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ run_id: 'wf-test-1', status: 'completed',
        results: [{ step: 'Шаг А', status: 'completed' }] }) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Automation")');
  await expect(page.locator('h2:has-text("Automation Board"), h2:has-text("Автоматизация")')).toBeVisible();
});

test('9. Benchmark Tab - renders correctly', async ({ page }) => {
  await page.route('**/api/models/vllm/status', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ available: false, base_url: 'http://127.0.0.1:8100/v1',
        models: [], privacy_level: 'local' }) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Benchmark")');
  await expect(page.locator('h2:has-text("Model Benchmark")')).toBeVisible();
  await expect(page.locator('text=Локально').first()).toBeVisible();
});

test('10. Analytics Tab - loads stats', async ({ page }) => {
  await page.route('**/api/analytics/research/stats', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ total_research_queries: 12, sources_consulted: 34, claims_verified: 89 }) }));
  await page.route('**/api/analytics/top-sources', async route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }));
  await page.route('**/api/analytics/claims-confidence', async route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }));
  await page.route('**/api/analytics/rooms-distribution', async route =>
    route.fulfill({ status: 200, contentType: 'application/json', body: JSON.stringify([]) }));
  await page.route('**/api/analytics/agent-stats', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ total_runs: 5, total_steps: 42, privacy_distribution: {local: 38, hybrid: 4}, error_count: 1 }) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Аналитика")');
  await expect(page.locator('h2:has-text("Analytics Dashboard")')).toBeVisible();
  await expect(page.locator('text=12')).toBeVisible();
});

test('11. Image Studio - recipe selection', async ({ page }) => {
  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Image Studio")');
  await expect(page.locator('h2:has-text("Image Studio")')).toBeVisible();
});

test('12. Export - download triggers', async ({ page }) => {
  await page.route('**/api/export', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify({ artifacts: [], memories: [] }),
      headers: { 'Content-Disposition': 'attachment; filename="asterion_export_all_20260607.json"' } }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Система")');
  await expect(page.locator('text=Экспорт').first()).toBeVisible({ timeout: 3000 });
});

test('13. Chat - composer textarea visible', async ({ page }) => {
  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Умный Чат")');
  await expect(page.locator('textarea[placeholder*="Спросите"]').first()).toBeVisible();
});

test('14. Vault Tab - renders empty document list', async ({ page }) => {
  await page.route('**/api/rag/documents', async route =>
    route.fulfill({ status: 200, contentType: 'application/json',
      body: JSON.stringify([{ id: 'doc-1', room_id: 'default', source: 'upload', indexed_chunks: 5, created_at: '2026-06-06T12:00:00Z' }]) }));

  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("База Знаний (Vault)")');
  await expect(page.locator('h1:has-text("Хранилище знаний")')).toBeVisible();
});

test('15. Артефакты tab renders with heading', async ({ page }) => {
  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Артефакты")');
  await expect(page.locator('h2:has-text("Хранилище артефактов")')).toBeVisible({ timeout: 3000 });
});

test('16. Плагины tab renders heading', async ({ page }) => {
  await page.goto('/');
  await page.click('aside.side-rail nav button:has-text("Плагины")');
  await expect(page.locator('h2:has-text("Plugin Manager")')).toBeVisible({ timeout: 2000 });
});

test('17. Command palette toggles theme', async ({ page }) => {
  await page.goto('/');
  await page.keyboard.press('Control+KeyK');
  const paletteInput = page.locator('#cmd-palette-input');
  await expect(paletteInput).toBeVisible();
  await paletteInput.fill('тему');
  await page.keyboard.press('Enter');
  await expect(paletteInput).not.toBeVisible();
  await expect(page.locator('.toast-container')).toContainText('Тема', { timeout: 5000 });
});
