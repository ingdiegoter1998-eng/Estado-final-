import { test as setup } from '@playwright/test';
import fs from 'fs';
import path from 'path';
import { prepareVentanillaFlow } from './helpers/django-e2e';

const authDir = path.join(__dirname, '.auth');
const authFile = path.join(authDir, 'ventanilla.json');

const username = process.env.E2E_VENTANILLA_USER || 'e2e_ventanilla';
const password = process.env.E2E_VENTANILLA_PASSWORD || process.env.E2E_TEST_PASSWORD || 'test123';

setup('autenticar usuario ventanilla', async ({ page }) => {
  if (!process.env.E2E_SKIP_PREPARE_AUTH) {
    prepareVentanillaFlow();
  }

  await page.goto('/registros/login/');
  await page.locator('#id_username').fill(username);
  await page.locator('#id_password').fill(password);
  await page.getByRole('button', { name: 'Ingresar al sistema' }).click();

  try {
    await page.waitForURL(
      (url) => !/\/registros\/login\/?$/.test(url.pathname),
      { timeout: 15_000 }
    );
  } catch {
    const errText = await page.locator('.alert-danger, .errorlist li').first().textContent().catch(() => null);
    throw new Error(
      `Login E2E falló para "${username}". ` +
      `Define E2E_VENTANILLA_USER y E2E_VENTANILLA_PASSWORD. ` +
      (errText ? `Mensaje: ${errText.trim()}` : 'Credenciales incorrectas o usuario sin grupo Ventanilla.')
    );
  }
  fs.mkdirSync(authDir, { recursive: true });
  await page.context().storageState({ path: authFile });
});
