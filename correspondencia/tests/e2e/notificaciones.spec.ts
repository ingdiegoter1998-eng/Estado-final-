import { test, expect } from '@playwright/test';

test.describe('Notificaciones del header', () => {
  test('abre el panel y muestra estructura del centro de avisos', async ({ page }) => {
    await page.goto('/registros/welcome/');

    const trigger = page.locator('#notificationsDropdown');
    await expect(trigger).toBeVisible();
    await trigger.click();

    const panel = page.locator('.notifications-panel');
    await expect(panel).toBeVisible();
    await expect(page.locator('#notificationPanelCount')).toBeVisible();
    await expect(page.locator('#notificationsContent')).toBeVisible();
    await expect(panel.getByText('Notificaciones')).toBeVisible();
  });

  test('consulta el endpoint de notificaciones', async ({ page }) => {
    await page.goto('/registros/welcome/');

    const response = await page.request.get(
      '/registros/correspondencia/notificaciones/obtener/'
    );
    expect(response.ok()).toBeTruthy();

    const data = await response.json();
    expect(data).toMatchObject({
      success: true,
      no_leidas: expect.any(Array),
      leidas: expect.any(Array),
      total_no_leidas: expect.any(Number),
    });
  });
});
