import { type Page, expect } from '@playwright/test';

export class VentanillaPage {
  constructor(private readonly page: Page) {}

  async gotoDashboard() {
    await this.page.goto('/registros/correspondencia/ventanilla/dashboard/');
    await expect(this.page).toHaveURL(/ventanilla\/dashboard/);
    await expect(this.page.locator('body')).not.toContainText('Server Error');
  }

  async gotoCorreosPendientes() {
    await this.page.goto('/registros/correspondencia/ventanilla/correos-pendientes/');
    await expect(this.page).toHaveURL(/correos-pendientes/);
    await expect(this.page.locator('body')).not.toContainText('Server Error');
  }

  async buscarCorreo(texto: string) {
    const form = this.page.locator('form').filter({ has: this.page.locator('#id_q') });
    await expect(form).toBeVisible();
    await form.locator('#id_q').fill(texto);
    await form.getByRole('button', { name: /Aplicar Filtros|Buscar/i }).click();
  }

  async abrirFiltrosSiCerrados() {
    const panel = this.page.locator('#filtrosCorreos');
    if ((await panel.count()) > 0 && !(await panel.isVisible())) {
      await this.page.locator('[data-bs-target="#filtrosCorreos"]').click();
      await expect(panel).toBeVisible();
    }
  }

  async tablaVisible() {
    await expect(this.page.locator('table').first()).toBeVisible();
  }

  async gotoControlSincronizacion() {
    await this.page.goto('/registros/correspondencia/ventanilla/control-sincronizacion/');
    await expect(this.page).toHaveURL(/control-sincronizacion/);
    await expect(this.page.locator('body')).toContainText(/Gmail|sincroniz/i);
  }

  async gotoSeguimientoEntrega() {
    await this.page.goto('/registros/correspondencia/ventanilla/seguimiento-entrega/');
    await expect(this.page).toHaveURL(/seguimiento-entrega/);
    await expect(this.page.locator('body')).toContainText(/Trazabilidad|Postmark|Entrega/i);
  }

  async gotoRespuestasPendientes(tab: 'pendientes' | 'aprobadas' = 'pendientes') {
    const qs = tab === 'aprobadas' ? '?tab=aprobadas' : '';
    await this.page.goto(`/registros/correspondencia/ventanilla/respuestas-pendientes/${qs}`);
    await expect(this.page).toHaveURL(/respuestas-pendientes/);
    await expect(this.page.locator('body')).not.toContainText('Server Error');
  }

  async gotoRevisarRespuesta(respuestaId: number) {
    await this.page.goto(`/registros/correspondencia/ventanilla/respuesta/${respuestaId}/revisar/`);
    await expect(this.page).toHaveURL(new RegExp(`/respuesta/${respuestaId}/revisar`));
  }
}
