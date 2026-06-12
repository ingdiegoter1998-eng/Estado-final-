import { test, expect } from '@playwright/test';

test.describe('Radicación - Dashboard y Modal', () => {
  test('bloquea dashboard sin login', async ({ page, baseURL }) => {
    await page.goto(`${baseURL}/registros/correspondencia/ventanilla/dashboard/`);
    await expect(page).toHaveURL(/login|welcome/);
  });
});


