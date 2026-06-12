import { test, expect } from '@playwright/test';

test.describe('Pendientes por asignar', () => {
  test('muestra título, filtros y listado', async ({ page }) => {
    await page.goto('/registros/correspondencia/pendientes-distribuir/');

    await expect(
      page.getByRole('heading', { name: /Correspondencia Pendiente de Asignar/i })
    ).toBeVisible();

    await expect(page.getByRole('heading', { name: 'Filtros de búsqueda' })).toBeVisible();
    await expect(page.locator('#id_search_term')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Listado' })).toBeVisible();
    await expect(page.locator('.pendientes-count')).toContainText(/pendiente/i);
  });

  test('aplica filtro de búsqueda sin error', async ({ page }) => {
    await page.goto('/registros/correspondencia/pendientes-distribuir/');
    await page.locator('#id_search_term').fill('test-e2e');
    await page.getByRole('button', { name: 'Buscar' }).click();
    await expect(page).toHaveURL(/search_term=test-e2e/);
    await expect(page.getByRole('heading', { name: 'Listado' })).toBeVisible();
  });
});
