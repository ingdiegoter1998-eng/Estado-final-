import { execSync } from 'node:child_process';
import path from 'node:path';

const PROJECT_ROOT = path.resolve(__dirname, '../../../../');
const PYTHON = path.join(PROJECT_ROOT, 'venv/bin/python');

export type VentanillaFlowE2E = {
  ventanilla_user: string;
  redactor_user: string;
  password: string;
  entrada_id: number;
  numero_radicado: string;
  salida_id: number;
  numero_radicado_salida: string;
  dashboard_path: string;
  entrada_path: string;
  revisar_path: string;
  respuestas_path: string;
};

function shellQuote(value: string): string {
  return `'${value.replace(/'/g, `'\\''`)}'`;
}

export function runManage(args: string, extraEnv: Record<string, string> = {}): string {
  return execSync(`${shellQuote(PYTHON)} manage.py ${args}`, {
    cwd: PROJECT_ROOT,
    encoding: 'utf8',
    env: {
      ...process.env,
      DJANGO_SETTINGS_MODULE:
        process.env.E2E_DJANGO_SETTINGS_MODULE || process.env.DJANGO_SETTINGS_MODULE || 'hospital_document_management.settings',
      E2E_ALLOW_MUTATIONS: '1',
      E2E_CAPTURE_EMAIL: process.env.E2E_LIVE_EMAIL ? '0' : '1',
      ...extraEnv,
    },
    stdio: ['pipe', 'pipe', 'pipe'],
  }).trim();
}

export function prepareVentanillaFlow(): VentanillaFlowE2E {
  const mailTo = process.env.E2E_MAIL_TO || '';
  const destArg = mailTo ? `--destinatario-email ${shellQuote(mailTo)}` : '';
  const out = runManage(`e2e_prepare_ventanilla_flow --stdout-json ${destArg}`.trim());
  const line = out.split('\n').filter((l) => l.startsWith('{')).pop() || '{}';
  return JSON.parse(line) as VentanillaFlowE2E;
}

export function cleanupVentanillaFlow(): void {
  runManage('e2e_prepare_ventanilla_flow --cleanup');
}
