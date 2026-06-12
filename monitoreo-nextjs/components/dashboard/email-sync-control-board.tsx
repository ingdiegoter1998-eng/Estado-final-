"use client";

import { useState, useCallback, useEffect, type ReactNode } from "react";
import useSWR from "swr";
import api from "@/lib/axios";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  RefreshCw,
  AlertTriangle,
  Search,
  Activity,
  Bug,
  DatabaseBackup,
  Play,
  Zap,
  Trash2,
  StopCircle,
  Mail,
  ActivitySquare,
  ClipboardCheck,
} from "lucide-react";
const fetcher = (url: string) => api.get(url).then((r) => r.data);

export type ControlRun = {
  id: number;
  tipo_operacion: string;
  tipo_operacion_label: string;
  estado: "PENDING" | "RUNNING" | "SUCCESS" | "WARN" | "FAIL";
  estado_label?: string;
  creado_en: string | null;
  iniciado_en?: string | null;
  finalizado_en: string | null;
  task_id?: string;
  ejecutado_por: string;
  error: string;
  salida_preview: string;
  salida?: string;
  parametros: Record<string, string | number>;
  resumen: Record<string, unknown>;
  metrics: {
    total_encontrados?: number | null;
    total_nuevos?: number | null;
    total_guardados?: number | null;
    total_rechazados?: number | null;
    total_adjuntos?: number | null;
    total_duplicados?: number | null;
    total_sospechosos?: number | null;
    total_errores?: number | null;
  };
};

export type EmailSyncBoardData = {
  ingestion_provider: "imap" | "gmail_api" | string;
  gmail_status?: {
    ultimo_history_id?: string;
    watch_expira_en?: string;
    sync_estado?: string;
    watch_expires_soon?: boolean;
    watch_missing?: boolean;
    outbound_email_address?: string;
    gmail_profile_email?: string;
    gmail_profile_error?: string;
    cuenta_institucional_pendiente?: boolean;
    database_engine?: string;
    database_name?: string;
    database_host?: string;
    is_production_database?: boolean;
    django_settings_module?: string;
    django_debug?: boolean;
  } | null;
  ultimo_fetch?: string | null;
  ultimo_correo_bd?: {
    id: number;
    remitente: string;
    fecha_lectura_imap?: string | null;
  } | null;
  sync_state?: {
    estado: string;
    ultimo_inicio?: string | null;
    ultimo_fin?: string | null;
    ultimo_error?: string;
  } | null;
  problematicos_pendientes?: number;
  control_panel?: {
    active_runs_count: number;
    heavy_operation_in_progress: boolean;
    latest_verify?: ControlRun | null;
    latest_diagnose?: ControlRun | null;
    recent_runs: ControlRun[];
  };
};

type ActionTier = "daily" | "support";

type ActionDef = {
  key: string;
  label: string;
  description: string;
  icon: typeof Search;
  tier: ActionTier;
  heavy?: boolean;
};

const TIER_META: Record<ActionTier, { title: string; hint: string }> = {
  daily: {
    title: "Uso frecuente",
    hint: "Verifique, recupere si hace falta y sincronice el buzon.",
  },
  support: {
    title: "Revision y soporte",
    hint: "Use cuando algo no cuadra o necesite auditar el sistema.",
  },
};

const SHARED_ACTIONS: ActionDef[] = [
  {
    key: "VERIFY",
    label: "Verificar cobertura",
    description: "Compara Gmail contra la base de datos antes de recuperar.",
    icon: Search,
    tier: "daily",
    heavy: true,
  },
  {
    key: "RECOVER",
    label: "Recuperar faltantes",
    description: "Importa correos faltantes del rango seleccionado.",
    icon: DatabaseBackup,
    tier: "daily",
    heavy: true,
  },
  {
    key: "DUPLICATES",
    label: "Verificar duplicados",
    description: "Detecta correos repetidos o sospechosos.",
    icon: Activity,
    tier: "support",
  },
  {
    key: "DIAGNOSE",
    label: "Diagnostico operativo",
    description: "Revisa Celery, locks y estado operativo.",
    icon: Bug,
    tier: "support",
  },
];

const IMAP_ACTIONS: ActionDef[] = [
  {
    key: "SYNC_NOW",
    label: "Sincronizar ahora",
    description: "Encola una corrida inmediata del pipeline IMAP.",
    icon: Play,
    tier: "daily",
    heavy: true,
  },
];

const GMAIL_ACTIONS: ActionDef[] = [
  {
    key: "GMAIL_PIPELINE_TICK",
    label: "Sincronizar Gmail",
    description: "Renueva watch si hace falta y trae correos nuevos.",
    icon: Zap,
    tier: "daily",
    heavy: true,
  },
];

const STATUS_BADGE: Record<string, "secondary" | "success" | "warning" | "danger"> = {
  PENDING: "secondary",
  RUNNING: "warning",
  SUCCESS: "success",
  WARN: "warning",
  FAIL: "danger",
};

const SYNC_STATE_LABELS: Record<string, string> = {
  SUCCESS: "Exitosa",
  RUNNING: "En ejecucion",
  FAIL: "Fallida",
  UNKNOWN: "Sin registro",
};

const inputClassName =
  "h-9 w-full rounded-md border border-input bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-1 focus:ring-ring";

function getActionsForProvider(provider: string): ActionDef[] {
  const mode = provider === "gmail_api" ? "gmail_api" : "imap";
  return [...SHARED_ACTIONS, ...(mode === "gmail_api" ? GMAIL_ACTIONS : IMAP_ACTIONS)];
}

function groupActionsByTier(actions: ActionDef[]) {
  const order: ActionTier[] = ["daily", "support"];
  return order
    .map((tier) => ({
      tier,
      items: actions.filter((action) => action.tier === tier),
    }))
    .filter((section) => section.items.length > 0);
}

function FeedbackBanner({
  message,
  error,
  onDismiss,
}: {
  message: string | null;
  error: string | null;
  onDismiss: () => void;
}) {
  if (!message && !error) return null;

  return (
    <div
      className={cn(
        "rounded-lg border px-4 py-3 text-sm flex items-start justify-between gap-3",
        error
          ? "border-destructive/30 bg-destructive/10 text-destructive"
          : "border-emerald-500/30 bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
      )}
    >
      <span>{error || message}</span>
      <button
        type="button"
        onClick={onDismiss}
        className="shrink-0 text-xs underline underline-offset-2 opacity-80 hover:opacity-100"
      >
        Cerrar
      </button>
    </div>
  );
}

function formatAbsoluteDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("es-CO", {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function formatTableDate(value?: string | null) {
  if (!value) return "-";
  return new Date(value).toLocaleString("es-CO", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function FilterField({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="space-y-1.5 block">
      <span className="text-xs font-medium text-muted-foreground">{label}</span>
      {children}
    </label>
  );
}

function ActionButton({
  action,
  disabled,
  busy,
  onClick,
}: {
  action: ActionDef;
  disabled: boolean;
  busy: boolean;
  onClick: () => void;
}) {
  const Icon = action.icon;
  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "rounded-lg border border-border bg-card p-3 text-left transition-colors w-full",
        "hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring",
        "disabled:cursor-not-allowed disabled:opacity-50"
      )}
    >
      <div className="flex items-start gap-3">
        <span className="rounded-md bg-muted p-2 shrink-0">
          <Icon className="h-4 w-4 text-primary" />
        </span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold text-foreground">{action.label}</p>
          <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
            {action.description}
          </p>
        </div>
        {busy ? (
          <RefreshCw className="h-4 w-4 animate-spin shrink-0 text-muted-foreground" />
        ) : null}
      </div>
    </button>
  );
}

function KpiCard({
  label,
  value,
  hint,
  badge,
}: {
  label: string;
  value: ReactNode;
  hint: ReactNode;
  badge?: ReactNode;
}) {
  return (
    <div className="rounded-lg border border-border bg-card p-4 h-full">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-medium uppercase tracking-wide text-muted-foreground">
            {label}
          </p>
          <div className="mt-2 text-lg font-semibold text-foreground">{value}</div>
          <div className="mt-1 text-xs text-muted-foreground">{hint}</div>
        </div>
        {badge}
      </div>
    </div>
  );
}

function RunDetailPanel({
  run,
  loading,
  onCancel,
  onDelete,
  cancelBusy,
  deleteBusy,
}: {
  run: ControlRun | null;
  loading: boolean;
  onCancel: (id: number) => void;
  onDelete: (id: number) => void;
  cancelBusy: boolean;
  deleteBusy: boolean;
}) {
  if (loading) {
    return (
      <div className="rounded-lg border border-border bg-card p-6 text-sm text-muted-foreground">
        <RefreshCw className="h-4 w-4 animate-spin inline mr-2" />
        Cargando detalle…
      </div>
    );
  }

  if (!run) {
    return (
      <div className="rounded-lg border border-dashed border-border bg-card p-6 text-sm text-muted-foreground">
        Seleccione una ejecucion del historial para inspeccionar su detalle.
      </div>
    );
  }

  const canCancel = run.estado === "PENDING" || run.estado === "RUNNING";

  return (
    <div className="rounded-lg border border-border bg-card p-4 space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="info">{run.tipo_operacion_label}</Badge>
        <Badge variant={STATUS_BADGE[run.estado] || "secondary"}>{run.estado}</Badge>
        {run.task_id ? (
          <Badge variant="outline" className="font-mono text-[10px]">
            Task {run.task_id}
          </Badge>
        ) : null}
      </div>

      <div className="flex flex-wrap gap-2">
        {canCancel ? (
          <button
            type="button"
            disabled={cancelBusy || deleteBusy}
            onClick={() => onCancel(run.id)}
            className="inline-flex h-8 items-center gap-1 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 text-xs font-medium text-amber-700 dark:text-amber-200 hover:bg-amber-500/15 disabled:opacity-50"
          >
            {cancelBusy ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <StopCircle className="h-3.5 w-3.5" />
            )}
            Cancelar ejecucion
          </button>
        ) : null}
        <button
          type="button"
          disabled={cancelBusy || deleteBusy}
          onClick={() => onDelete(run.id)}
          className="inline-flex h-8 items-center gap-1 rounded-md border border-destructive/30 bg-destructive/10 px-3 text-xs font-medium text-destructive hover:bg-destructive/15 disabled:opacity-50"
        >
          {deleteBusy ? (
            <RefreshCw className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Trash2 className="h-3.5 w-3.5" />
          )}
          Eliminar ejecucion
        </button>
      </div>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-md border border-border p-3">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Totales</p>
          <div className="mt-2 space-y-1 text-xs text-muted-foreground">
            <p>Encontrados Gmail: <span className="text-foreground">{run.metrics.total_encontrados ?? "-"}</span></p>
            <p>Faltantes detectados: <span className="text-foreground">{run.metrics.total_nuevos ?? "-"}</span></p>
            <p>Guardados: <span className="text-foreground">{run.metrics.total_guardados ?? "-"}</span></p>
            <p>Adjuntos: <span className="text-foreground">{run.metrics.total_adjuntos ?? "-"}</span></p>
          </div>
        </div>
        <div className="rounded-md border border-border p-3">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Integridad</p>
          <div className="mt-2 space-y-1 text-xs text-muted-foreground">
            <p>Duplicados reales: <span className="text-foreground">{run.metrics.total_duplicados ?? "-"}</span></p>
            <p>Sospechosos: <span className="text-foreground">{run.metrics.total_sospechosos ?? "-"}</span></p>
            <p>Rechazados: <span className="text-foreground">{run.metrics.total_rechazados ?? "-"}</span></p>
            <p>Errores: <span className="text-foreground">{run.metrics.total_errores ?? "-"}</span></p>
          </div>
        </div>
        <div className="rounded-md border border-border p-3">
          <p className="text-[11px] uppercase tracking-wide text-muted-foreground">Ejecucion</p>
          <div className="mt-2 space-y-1 text-xs text-muted-foreground">
            <p>Creada: <span className="text-foreground">{formatTableDate(run.creado_en)}</span></p>
            <p>Inicio: <span className="text-foreground">{formatTableDate(run.iniciado_en)}</span></p>
            <p>Fin: <span className="text-foreground">{formatTableDate(run.finalizado_en)}</span></p>
            <p>Usuario: <span className="text-foreground">{run.ejecutado_por}</span></p>
          </div>
        </div>
      </div>

      <div>
        <h6 className="text-sm font-semibold text-foreground mb-2">Parametros</h6>
        <pre className="max-h-32 overflow-auto rounded-md border border-border bg-muted/40 p-3 text-[11px] text-muted-foreground">
          {JSON.stringify(run.parametros || {}, null, 2)}
        </pre>
      </div>

      <div>
        <h6 className="text-sm font-semibold text-foreground mb-2">Resumen estructurado</h6>
        <pre className="max-h-40 overflow-auto rounded-md border border-border bg-muted/40 p-3 text-[11px] text-muted-foreground">
          {JSON.stringify(run.resumen || {}, null, 2)}
        </pre>
      </div>

      {run.error ? (
        <div className="rounded-md border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          <strong>Error:</strong> {run.error}
        </div>
      ) : null}

      <div>
        <h6 className="text-sm font-semibold text-foreground mb-2">Salida detallada</h6>
        <pre className="max-h-[28rem] overflow-auto whitespace-pre-wrap rounded-md border border-border bg-muted/60 p-3 text-[11px] text-foreground">
          {run.salida || run.salida_preview || "Sin salida registrada todavia."}
        </pre>
      </div>
    </div>
  );
}

export default function EmailSyncControlBoard({
  data,
  mutate,
}: {
  data: EmailSyncBoardData;
  mutate: () => Promise<unknown>;
}) {
  const provider = data.ingestion_provider ?? "imap";
  const isGmailApi = provider === "gmail_api";
  const gmailStatus = data.gmail_status;
  const runs = data.control_panel?.recent_runs ?? [];
  const heavyBusy = data.control_panel?.heavy_operation_in_progress ?? false;
  const latestDiagnose = data.control_panel?.latest_diagnose;
  const latestVerify = data.control_panel?.latest_verify;
  const syncState = data.sync_state;
  const actions = getActionsForProvider(provider);
  const actionSections = groupActionsByTier(actions);

  const [days, setDays] = useState("7");
  const [since, setSince] = useState("");
  const [until, setUntil] = useState("");
  const [pendingAction, setPendingAction] = useState<string | null>(null);
  const [cancelBusyId, setCancelBusyId] = useState<number | null>(null);
  const [deleteBusyId, setDeleteBusyId] = useState<number | null>(null);
  const [actionMessage, setActionMessage] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [selectedRunId, setSelectedRunId] = useState<number | null>(null);

  const clearFeedback = useCallback(() => {
    setActionMessage(null);
    setActionError(null);
  }, []);

  useEffect(() => {
    if (runs.length === 0) {
      setSelectedRunId(null);
      return;
    }
    if (!selectedRunId || !runs.some((run) => run.id === selectedRunId)) {
      setSelectedRunId(runs[0].id);
    }
  }, [runs, selectedRunId]);

  const { data: selectedRun, isLoading: runLoading, mutate: mutateRun } = useSWR<ControlRun>(
    selectedRunId ? `/api/monitoreo/email-sync/runs/${selectedRunId}` : null,
    fetcher,
    { refreshInterval: selectedRunId ? 5000 : 0 }
  );

  const runAction = useCallback(
    async (action: string) => {
      setPendingAction(action);
      setActionMessage(null);
      setActionError(null);

      try {
        const payload: Record<string, string | number> = { action, days: Number(days) };
        if (since) payload.since = since;
        if (until) payload.until = until;
        const response = await api.post("/api/monitoreo/email-sync", payload);
        setActionMessage(response.data?.detail || "Operacion encolada.");
        if (response.data?.run?.id) {
          setSelectedRunId(response.data.run.id);
        }
        await mutate();
        await mutateRun();
      } catch (err: any) {
        const detail = err?.response?.data?.detail || "No fue posible lanzar la operacion.";
        setActionError(detail);
        if (err?.response?.data?.run?.id) {
          setSelectedRunId(err.response.data.run.id);
        }
        await mutate();
      } finally {
        setPendingAction(null);
      }
    },
    [days, since, until, mutate, mutateRun]
  );

  const cancelRun = useCallback(
    async (runId: number) => {
      setCancelBusyId(runId);
      clearFeedback();
      try {
        const response = await api.post(`/api/monitoreo/email-sync/runs/${runId}`, {
          admin_action: "cancel_run",
        });
        setActionMessage(response.data?.detail || "Ejecucion cancelada.");
        await mutate();
        await mutateRun();
      } catch (err: any) {
        setActionError(err?.response?.data?.detail || "No fue posible cancelar la ejecucion.");
      } finally {
        setCancelBusyId(null);
      }
    },
    [clearFeedback, mutate, mutateRun]
  );

  const deleteRun = useCallback(
    async (runId: number) => {
      if (!window.confirm("Eliminar esta ejecucion del historial?")) return;
      setDeleteBusyId(runId);
      clearFeedback();
      try {
        const response = await api.delete(`/api/monitoreo/email-sync/runs/${runId}`);
        setActionMessage(response.data?.detail || "Ejecucion eliminada.");
        if (selectedRunId === runId) {
          setSelectedRunId(null);
        }
        await mutate();
        await mutateRun();
      } catch (err: any) {
        setActionError(err?.response?.data?.detail || "No fue posible eliminar la ejecucion.");
      } finally {
        setDeleteBusyId(null);
      }
    },
    [clearFeedback, mutate, mutateRun, selectedRunId]
  );

  const syncEstado = syncState?.estado || "UNKNOWN";

  return (
    <div className="space-y-6">
      <FeedbackBanner
        message={actionMessage}
        error={actionError}
        onDismiss={clearFeedback}
      />

      <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
        <KpiCard
          label={isGmailApi ? "Sincronizacion Gmail" : "Sincronizacion IMAP"}
          value={SYNC_STATE_LABELS[syncEstado] || syncEstado}
          hint={
            syncState?.ultimo_fin
              ? `Ultimo fin: ${formatTableDate(syncState.ultimo_fin)}`
              : "Sin ejecucion finalizada registrada"
          }
          badge={
            <Badge variant={STATUS_BADGE[syncEstado] || "secondary"}>
              {syncEstado}
            </Badge>
          }
        />
        <KpiCard
          label="Ultimo correo en BD"
          value={
            data.ultimo_fetch
              ? formatTableDate(data.ultimo_fetch)
              : "Sin datos"
          }
          hint={
            data.ultimo_correo_bd
              ? `ID ${data.ultimo_correo_bd.id} · ${data.ultimo_correo_bd.remitente}`
              : "No hay correos almacenados todavia."
          }
        />
        <KpiCard
          label="Operaciones activas"
          value={data.control_panel?.active_runs_count ?? 0}
          hint="Pendientes o ejecutandose desde este panel."
        />
        <KpiCard
          label="Ultima verificacion"
          value={
            latestVerify?.creado_en
              ? formatAbsoluteDate(latestVerify.creado_en)
              : "Sin corridas"
          }
          hint={
            latestVerify
              ? `Estado ${latestVerify.estado}`
              : "Aun no se ha ejecutado una auditoria desde el panel."
          }
        />
      </div>

      {syncState?.estado === "RUNNING" ? (
        <div className="flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-4 py-3 text-sm text-amber-900 dark:text-amber-100">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
          <div>
            <p className="font-semibold">La sincronizacion principal figura en ejecucion.</p>
            <p className="text-xs mt-1 opacity-90">
              Inicio registrado: {formatTableDate(syncState.ultimo_inicio)}. Use el diagnostico
              operativo para confirmar si realmente sigue viva o quedo pegada.
            </p>
          </div>
        </div>
      ) : null}

      <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <div className="space-y-4">
          <div className="rounded-lg border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h5 className="text-sm font-semibold text-foreground">Acciones operativas</h5>
            </div>
            <div className="p-4 space-y-4">
              <div className="flex flex-wrap items-center gap-2">
                <Badge variant={heavyBusy ? "warning" : "success"}>
                  {heavyBusy ? "Operacion en curso" : "Listo para usar"}
                </Badge>
                {(data.problematicos_pendientes ?? 0) > 0 ? (
                  <Badge variant="warning">
                    {data.problematicos_pendientes} problematicos pendientes
                  </Badge>
                ) : null}
              </div>

              <FilterField label="Ventana de revision">
                <select value={days} onChange={(e) => setDays(e.target.value)} className={inputClassName}>
                  <option value="1">Ultimo dia</option>
                  <option value="3">Ultimos 3 dias</option>
                  <option value="7">Ultimos 7 dias</option>
                  <option value="30">Ultimos 30 dias</option>
                  <option value="60">Ultimos 60 dias</option>
                </select>
                <p className="text-[11px] text-muted-foreground mt-1">
                  Si define fechas exactas abajo, ese rango tendra prioridad.
                </p>
              </FilterField>

              <FilterField label="Desde fecha y hora exacta">
                <input
                  type="datetime-local"
                  value={since}
                  onChange={(e) => setSince(e.target.value)}
                  className={inputClassName}
                />
              </FilterField>

              <FilterField label="Hasta fecha y hora exacta">
                <input
                  type="datetime-local"
                  value={until}
                  onChange={(e) => setUntil(e.target.value)}
                  className={inputClassName}
                />
              </FilterField>

              <Separator />

              {actionSections.map(({ tier, items }) => {
                const meta = TIER_META[tier];
                return (
                  <section key={tier} className="space-y-2">
                    <div>
                      <p className="text-xs font-semibold text-foreground">{meta.title}</p>
                      <p className="text-[11px] text-muted-foreground">{meta.hint}</p>
                    </div>
                    <div className="space-y-2">
                      {items.map((action) => (
                        <ActionButton
                          key={action.key}
                          action={action}
                          disabled={Boolean(pendingAction || (heavyBusy && action.heavy))}
                          busy={pendingAction === action.key}
                          onClick={() => runAction(action.key)}
                        />
                      ))}
                    </div>
                  </section>
                );
              })}

            </div>
          </div>

          <div className="rounded-lg border border-border bg-card">
            <div className="border-b border-border px-4 py-3">
              <h5 className="text-sm font-semibold text-foreground">Ultimo diagnostico</h5>
            </div>
            <div className="p-4 text-sm space-y-2">
              {latestDiagnose ? (
                <>
                  <p>
                    <span className="text-muted-foreground">Fecha:</span>{" "}
                    {formatTableDate(latestDiagnose.creado_en)}
                  </p>
                  <p>
                    <span className="text-muted-foreground">Estado:</span>{" "}
                    {latestDiagnose.estado}
                  </p>
                  {latestDiagnose.error ? (
                    <p className="text-destructive">
                      <span className="font-medium">Error:</span> {latestDiagnose.error}
                    </p>
                  ) : (
                    <p className="text-muted-foreground text-xs">
                      Seleccione el diagnostico en el historial para ver el detalle completo.
                    </p>
                  )}
                </>
              ) : (
                <p className="text-muted-foreground">
                  Todavia no hay diagnosticos ejecutados desde este panel.
                </p>
              )}
            </div>
          </div>

          {isGmailApi && gmailStatus ? (
            <div className="rounded-lg border border-border bg-card p-4 space-y-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-foreground">
                <Mail className="h-4 w-4 text-primary" />
                Estado Gmail
              </div>
              {!gmailStatus.is_production_database ? (
                <p className="text-xs text-amber-800 dark:text-amber-200 rounded-md border border-amber-500/30 bg-amber-500/10 px-3 py-2">
                  Base de datos de desarrollo ({gmailStatus.database_engine || "sqlite"}).
                  Use el sitio en puerto 80 (/monitoreo) para operar contra SQL Server de producción.
                </p>
              ) : null}
              <div className="grid gap-2 text-xs">
                <div className="rounded-md bg-muted/40 px-3 py-2">
                  <span className="text-muted-foreground">Cuenta OAuth Gmail:</span>{" "}
                  <span className="font-mono text-foreground">
                    {gmailStatus.gmail_profile_email || "Sin consultar"}
                  </span>
                </div>
                <div className="rounded-md bg-muted/40 px-3 py-2">
                  <span className="text-muted-foreground">Remitente configurado:</span>{" "}
                  <span className="font-mono text-foreground">
                    {gmailStatus.outbound_email_address || "-"}
                  </span>
                </div>
                {gmailStatus.cuenta_institucional_pendiente ? (
                  <p className="text-xs text-amber-700 dark:text-amber-200">
                    La configuración no coincide con la cuenta institucional esperada del hospital.
                  </p>
                ) : null}
                {gmailStatus.gmail_profile_error ? (
                  <p className="text-xs text-destructive">{gmailStatus.gmail_profile_error}</p>
                ) : null}
                <div className="rounded-md bg-muted/40 px-3 py-2">
                  <span className="text-muted-foreground">History ID:</span>{" "}
                  <span className="font-mono text-foreground">
                    {gmailStatus.ultimo_history_id || "Sin registrar"}
                  </span>
                </div>
                <div className="rounded-md bg-muted/40 px-3 py-2">
                  <span className="text-muted-foreground">Watch expira:</span>{" "}
                  <span className="text-foreground">
                    {gmailStatus.watch_expira_en
                      ? formatAbsoluteDate(gmailStatus.watch_expira_en)
                      : "Sin watch"}
                  </span>
                </div>
              </div>
              {gmailStatus.watch_missing ? (
                <p className="text-xs text-amber-700 dark:text-amber-200">
                  La suscripcion con Gmail no esta activa. Use &quot;Sincronizar Gmail&quot;.
                </p>
              ) : null}
              {gmailStatus.watch_expires_soon && !gmailStatus.watch_missing ? (
                <p className="text-xs text-amber-700 dark:text-amber-200">
                  La suscripcion expira pronto. Use &quot;Sincronizar Gmail&quot;.
                </p>
              ) : null}
            </div>
          ) : null}

          {syncState?.ultimo_error ? (
            <div className="flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 px-3 py-2 text-sm text-destructive">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{syncState.ultimo_error}</span>
            </div>
          ) : null}
        </div>

        <div className="space-y-4 min-w-0">
          <div className="rounded-lg border border-border bg-card overflow-hidden">
            <div className="border-b border-border px-4 py-3 flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <ActivitySquare className="h-4 w-4 text-primary" />
                <h5 className="text-sm font-semibold text-foreground">Historial reciente</h5>
              </div>
              <span className="text-xs text-muted-foreground">Ultimas 15 ejecuciones</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="bg-muted/40 text-xs text-muted-foreground">
                  <tr>
                    <th className="px-4 py-2 text-left font-medium">Fecha</th>
                    <th className="px-4 py-2 text-left font-medium">Operacion</th>
                    <th className="px-4 py-2 text-left font-medium">Estado</th>
                    <th className="px-4 py-2 text-left font-medium">Usuario</th>
                    <th className="px-4 py-2 text-right font-medium">Accion</th>
                  </tr>
                </thead>
                <tbody>
                  {runs.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-4 py-8 text-center text-muted-foreground">
                        Aun no hay operaciones registradas.
                      </td>
                    </tr>
                  ) : (
                    runs.map((run) => {
                      const isSelected = selectedRunId === run.id;
                      const canCancel = run.estado === "PENDING" || run.estado === "RUNNING";
                      return (
                        <tr
                          key={run.id}
                          className={cn(
                            "border-t border-border",
                            isSelected ? "bg-muted/40" : "hover:bg-muted/20"
                          )}
                        >
                          <td className="px-4 py-3 text-xs whitespace-nowrap">
                            {formatTableDate(run.creado_en)}
                          </td>
                          <td className="px-4 py-3 text-xs">{run.tipo_operacion_label}</td>
                          <td className="px-4 py-3">
                            <Badge variant={STATUS_BADGE[run.estado] || "secondary"}>
                              {run.estado}
                            </Badge>
                          </td>
                          <td className="px-4 py-3 text-xs">{run.ejecutado_por}</td>
                          <td className="px-4 py-3">
                            <div className="flex justify-end gap-1">
                              <button
                                type="button"
                                onClick={() => setSelectedRunId(run.id)}
                                className="h-7 px-2 rounded-md border border-input bg-background text-[11px] hover:bg-muted"
                              >
                                Ver
                              </button>
                              {canCancel ? (
                                <button
                                  type="button"
                                  disabled={cancelBusyId !== null || deleteBusyId !== null}
                                  onClick={() => cancelRun(run.id)}
                                  className="h-7 px-2 rounded-md border border-amber-500/30 bg-amber-500/10 text-[11px] text-amber-700 dark:text-amber-200 hover:bg-amber-500/15 disabled:opacity-50"
                                >
                                  {cancelBusyId === run.id ? "..." : "Cancelar"}
                                </button>
                              ) : null}
                              <button
                                type="button"
                                disabled={cancelBusyId !== null || deleteBusyId !== null}
                                onClick={() => deleteRun(run.id)}
                                className="h-7 px-2 rounded-md border border-destructive/30 bg-destructive/10 text-[11px] text-destructive hover:bg-destructive/15 disabled:opacity-50"
                              >
                                {deleteBusyId === run.id ? "..." : "Eliminar"}
                              </button>
                            </div>
                          </td>
                        </tr>
                      );
                    })
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div>
            <div className="flex items-center gap-2 mb-3">
              <ClipboardCheck className="h-4 w-4 text-primary" />
              <h5 className="text-sm font-semibold text-foreground">Detalle de ejecucion</h5>
            </div>
            <RunDetailPanel
              run={selectedRun ?? null}
              loading={Boolean(selectedRunId && runLoading && !selectedRun)}
              onCancel={cancelRun}
              onDelete={deleteRun}
              cancelBusy={cancelBusyId === selectedRunId}
              deleteBusy={deleteBusyId === selectedRunId}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
