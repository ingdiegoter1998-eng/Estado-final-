import { test, expect } from '@playwright/test';
import { cleanupVentanillaFlow, prepareVentanillaFlow, type VentanillaFlowE2E } from './helpers/django-e2e';
import { VentanillaPage } from './pages/ventanilla.page';

test.describe('@ventanilla flujo radicación/respuesta', () => {
  let flow: VentanillaFlowE2E;

  test.beforeAll(() => {
    cleanupVentanillaFlow();
    flow = prepareVentanillaFlow();
  });

  test.afterAll(() => {
    if (!process.env.E2E_KEEP_DATA) {
      cleanupVentanillaFlow();
    }
  });

  test('muestra el radicado de prueba y su respuesta pendiente', async ({ page }) => {
    const ventanilla = new VentanillaPage(page);

    await page.goto(flow.entrada_path);
    await expect(page.locator('body')).toContainText(flow.numero_radicado);
    await expect(page.locator('body')).toContainText(/\[E2E\]/);

    await ventanilla.gotoRespuestasPendientes();
    await expect(page.locator('body')).toContainText(flow.numero_radicado);
    await expect(page.locator('body')).toContainText(/\[E2E\] Respuesta Playwright/);
  });

  test('aprueba y envía respuesta sin llamar correo real', async ({ page }) => {
    test.skip(
      !!process.env.E2E_LIVE_EMAIL,
      'Este flujo protegido usa captura local. Para envío real cree un spec separado con E2E_LIVE_EMAIL=1.'
    );

    const ventanilla = new VentanillaPage(page);
    await ventanilla.gotoRevisarRespuesta(flow.salida_id);

    await expect(page.getByText(flow.numero_radicado_salida).first()).toBeVisible();
    await page.getByRole('button', { name: /Aprobar y Enviar Respuesta/i }).click();

    await expect(page).toHaveURL(/respuestas-pendientes/);
    await expect(page.locator('.alert-success, .messages .success, [role="alert"]').first()).toContainText(
      /Respuesta enviada a \d+ destinatarios?|enviada a \d+ destinatario/i
    );

    await ventanilla.gotoRespuestasPendientes('aprobadas');
    const body = page.locator('body');
    await expect(body).toContainText(flow.numero_radicado);
    await expect(body).toContainText(/\[E2E\] Respuesta Playwright/);
    await expect(body).toContainText(/Enviada|ENVIADA|Aprobada|APROBADA/i);
  });

  test('abre una segunda pestaña con seguimiento de entrega', async ({ context }) => {
    const seguimiento = await context.newPage();

    await seguimiento.goto('/registros/correspondencia/ventanilla/seguimiento-entrega/');
    await expect(seguimiento.locator('body')).toContainText(/Trazabilidad|Postmark|Entrega/i);

    await seguimiento.close();
  });
});
