import { test, expect } from '@playwright/test';
import { VentanillaPage } from './pages/ventanilla.page';

test.describe('@smoke ventanilla', () => {
  test('dashboard carga y no muestra error 500', async ({ page }) => {
    const ventanilla = new VentanillaPage(page);

    await ventanilla.gotoDashboard();

    await expect(page.locator('body')).toContainText(/Dashboard Ventanilla|Ventanilla/i);
  });

  test('correos pendientes permite abrir filtros y buscar', async ({ page }) => {
    const ventanilla = new VentanillaPage(page);

    await ventanilla.gotoCorreosPendientes();
    await ventanilla.abrirFiltrosSiCerrados();
    await ventanilla.buscarCorreo('e2e');

    await expect(page.locator('body')).not.toContainText('Server Error');
  });

  test('control de sincronización Gmail está accesible', async ({ page }) => {
    const ventanilla = new VentanillaPage(page);

    await ventanilla.gotoControlSincronizacion();
  });

  test('seguimiento de entrega Postmark está accesible', async ({ page }) => {
    const ventanilla = new VentanillaPage(page);

    await ventanilla.gotoSeguimientoEntrega();
  });
});
