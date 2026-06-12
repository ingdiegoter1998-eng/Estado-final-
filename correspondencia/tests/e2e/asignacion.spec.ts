import { test, expect } from '@playwright/test';

test.describe('Asignación de correspondencia', () => {
  test('accede al formulario de asignar cuando hay pendientes', async ({ page }) => {
    await page.goto('/registros/correspondencia/pendientes-distribuir/');

    const asignarLink = page.getByRole('link', { name: /Asignar/i }).first();
    const total = await asignarLink.count();

    if (total === 0) {
      test.skip(true, 'No hay radicados pendientes en la base de datos de prueba.');
      return;
    }

    await asignarLink.click();
    await expect(page.getByRole('button', { name: /Asignar correspondencia/i })).toBeVisible();
    await expect(page.locator('select, input[type="radio"]').first()).toBeVisible();
  });

  test('bloquea acceso sin sesión', async ({ browser }) => {
    const context = await browser.newContext();
    const page = await context.newPage();

    await page.goto('/registros/correspondencia/pendientes-distribuir/');
    await expect(page).toHaveURL(/login|welcome/);

    await context.close();
  });
});
