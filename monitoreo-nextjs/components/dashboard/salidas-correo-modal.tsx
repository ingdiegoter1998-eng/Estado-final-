"use client";

import { useCallback, useMemo, useState } from "react";
import type { ReactNode } from "react";
import useSWR from "swr";
import {
  ArrowLeft,
  ArrowRight,
  Clipboard,
  ExternalLink,
  FileText,
  History,
  Loader2,
  MailCheck,
  Paperclip,
  RefreshCw,
  Search,
} from "lucide-react";
import api from "@/lib/axios";
import { cn } from "@/lib/utils";
import { useRangoParams } from "@/hooks/use-rango";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

const PAGE_SIZE = 50;

const fetcher = (url: string) => api.get(url).then((r) => r.data);

type MessageIdsFields = {
  outbound_provider?: string;
  provider_id_label?: string;
  provider_message_id?: string;
  rfc_message_id?: string;
  message_id?: string;
  postmark_message_id?: string;
  postmark_url?: string;
};

type SalidaCorreo = MessageIdsFields & {
  id: number;
  salida_id: number;
  radicado: string;
  oficina_nombre: string;
  usuario_nombre: string;
  hora: string;
  estado: "ENVIADO" | "FALLO" | "REBOTE" | string;
  estado_label: string;
  destinatario_email: string;
  destinatario_nombre: string;
  postmark_estado: string;
  postmark_record_type: string;
  postmark_recibido_at: string;
  postmark_detalle: string;
  detalle_error: string;
  smtp_code: string;
  dsn_status: string;
};

type ResumenEstado = {
  estado: string;
  total: number;
};

type ResumenOficina = {
  oficina: string;
  total: number;
};

type ArchivoDetalle = {
  id: number;
  nombre: string;
  tipo_mime: string;
  fecha_carga: string;
  url: string;
};

type EventoPostmarkDetalle = {
  id: number;
  record_type: string;
  recipient: string;
  postmark_message_id: string;
  recibido_at: string;
  procesado: boolean;
  resultado: string;
  detalle: string;
  bounce_type: string;
  inactive: boolean;
};

type DestinatarioDetalle = MessageIdsFields & {
  id: number;
  nombre: string;
  email: string;
  estado: string;
  estado_label: string;
  fecha_envio: string;
  postmark_estado: string;
  postmark_url?: string;
  detalle_error: string;
  motivo_resumen: string;
  smtp_code: string;
  dsn_status: string;
  ultimo_evento_at: string;
  eventos_postmark: EventoPostmarkDetalle[];
};

type HistorialDetalle = {
  id: number;
  tipo: string;
  tipo_label: string;
  descripcion: string;
  fecha_hora: string;
  usuario: string;
};

type SalidaCorreoDetalle = MessageIdsFields & {
  id: number;
  radicado: string;
  estado: string;
  estado_label: string;
  asunto: string;
  cuerpo: string;
  tipo_respuesta_label: string;
  motivo_respuesta_discrecional: string;
  motivo_rechazo: string;
  fecha_creacion: string;
  fecha_ultima_modificacion: string;
  fecha_aprobacion: string;
  fecha_envio: string;
  postmark_url?: string;
  oficina: { id: number | null; nombre: string };
  redactor: { id: number | null; nombre: string; cargo: string };
  aprobador: { id: number | null; nombre: string };
  funcionario_envia: string;
  destinatario_principal: { nombre: string; email: string };
  envio: {
    tipo: string;
    grupo: string;
    total_destinatarios_snapshot: number | null;
    detalle_snapshot: string;
  };
  resumen_entrega: {
    total_destinatarios: number;
    enviados: number;
    fallos: number;
    rebotes: number;
  };
  destinatarios: DestinatarioDetalle[];
  eventos_postmark: EventoPostmarkDetalle[];
  adjuntos: ArchivoDetalle[];
  evidencia_respuesta: ArchivoDetalle | null;
  historial: HistorialDetalle[];
  correspondencia_original: {
    id: number;
    radicado: string;
    asunto: string;
    remitente: string;
    oficina_destino: string;
    url: string;
  } | null;
  django_detail_url: string;
};

function formatFecha(iso: string) {
  if (!iso) return "-";
  return new Date(iso).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function estadoVariant(estado: string) {
  if (estado === "ENVIADO") return "success";
  if (estado === "REBOTE") return "danger";
  if (estado === "FALLO") return "warning";
  return "secondary";
}

function estadoLabel(estado: string) {
  if (estado === "ENVIADO") return "Enviado";
  if (estado === "REBOTE") return "Rebote";
  if (estado === "FALLO") return "Fallo";
  return estado || "Otro";
}

function RadicadoLink({
  item,
  onSelect,
}: {
  item: SalidaCorreo;
  onSelect: (salidaId: number) => void;
}) {
  if (!item.radicado) return <span className="text-muted-foreground">-</span>;

  return (
    <button
      type="button"
      className="inline-flex items-center gap-1 text-left font-semibold text-blue-400 underline underline-offset-2 hover:text-blue-300"
      onClick={() => onSelect(item.salida_id)}
    >
      {item.radicado}
      <FileText className="h-3 w-3 shrink-0" />
    </button>
  );
}

function CopyButton({ value, label }: { value: string; label: string }) {
  if (!value) return null;

  return (
    <button
      type="button"
      onClick={() => navigator.clipboard?.writeText(value)}
      className="inline-flex items-center gap-1 rounded-md border border-border/70 px-2 py-1 text-[10px] font-semibold text-muted-foreground hover:bg-muted hover:text-foreground"
      title={`Copiar ${label}`}
    >
      <Clipboard className="h-3 w-3" />
      Copiar
    </button>
  );
}

function resolveProviderIdLabel(item: MessageIdsFields) {
  if (item.provider_id_label) return item.provider_id_label;
  if (item.outbound_provider === "gmail_api") return "ID Gmail";
  if (item.outbound_provider === "postmark") return "ID Postmark";
  return "ID proveedor";
}

function MessageIdsBlock({ item, compact = false }: { item: MessageIdsFields; compact?: boolean }) {
  const providerId = (item.provider_message_id || item.postmark_message_id || "").trim();
  const rfcId = (item.rfc_message_id || item.message_id || "").trim();
  const providerLabel = resolveProviderIdLabel(item);
  const codeClass = compact
    ? "block max-w-[240px] truncate rounded bg-muted/70 px-1.5 py-1 text-[10px]"
    : "max-w-[260px] truncate rounded-md bg-muted/70 px-2 py-1 text-[11px]";

  if (!providerId && !rfcId) {
    return <div className="text-xs text-muted-foreground">Sin IDs persistidos.</div>;
  }

  return (
    <div className="space-y-2">
      {providerId ? (
        <div className="space-y-0.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            {providerLabel}
          </p>
          <div className="flex flex-wrap items-start gap-2">
            <code className={codeClass}>{providerId}</code>
            <CopyButton value={providerId} label={providerLabel} />
            {item.postmark_url && item.outbound_provider === "postmark" && (
              <a
                href={item.postmark_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 rounded-md border border-blue-500/30 px-2 py-1 text-[10px] font-semibold text-blue-400 hover:bg-blue-500/10"
              >
                Postmark
                <ExternalLink className="h-3 w-3" />
              </a>
            )}
          </div>
        </div>
      ) : null}
      {rfcId ? (
        <div className="space-y-0.5">
          <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
            Message-ID RFC
          </p>
          <div className="flex flex-wrap items-start gap-2">
            <code className={codeClass}>{rfcId}</code>
            <CopyButton value={rfcId} label="Message-ID RFC" />
          </div>
          {item.outbound_provider === "gmail_api" && (
            <p className="text-[10px] text-muted-foreground">
              Usado para cruzar rebotes DSN que vuelven al buzón entrante.
            </p>
          )}
        </div>
      ) : null}
    </div>
  );
}

function DetailField({
  label,
  value,
}: {
  label: string;
  value?: string | number | null;
}) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/60 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
        {label}
      </p>
      <p className="mt-1 text-sm font-medium text-foreground/90">
        {value || "-"}
      </p>
    </div>
  );
}

function DetailSection({
  title,
  icon,
  children,
}: {
  title: string;
  icon?: ReactNode;
  children: ReactNode;
}) {
  return (
    <section className="rounded-xl border border-border/60 bg-card/40 p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold">
        {icon}
        {title}
      </h3>
      {children}
    </section>
  );
}

function SalidaCorreoDetailPanel({
  salidaId,
  onBack,
}: {
  salidaId: number;
  onBack: () => void;
}) {
  const { data, error, isLoading, mutate } = useSWR<SalidaCorreoDetalle>(
    `/api/monitoreo/salidas-correo/${salidaId}/detalle`,
    fetcher
  );

  if (isLoading) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-lg border border-border/60 bg-card/30 text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Cargando detalle de correspondencia...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 rounded-lg border border-border/60 bg-card/30 px-6 text-center text-sm">
        <p className="font-semibold text-amber-400">
          No se pudo cargar el detalle de la salida.
        </p>
        <p className="text-muted-foreground">
          Verifique que el endpoint Django esté desplegado y que la sesión siga activa como superusuario.
        </p>
        <div className="flex flex-wrap justify-center gap-2">
          <button
            type="button"
            onClick={onBack}
            className="inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-xs font-semibold hover:bg-muted"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            Volver
          </button>
          <button
            type="button"
            onClick={() => mutate()}
            className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-1.5 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Reintentar
          </button>
        </div>
      </div>
    );
  }

  const archivos = data.evidencia_respuesta
    ? [...data.adjuntos, data.evidencia_respuesta]
    : data.adjuntos;

  return (
    <div className="min-h-0 flex-1 overflow-auto rounded-lg border border-border/60 bg-background/30">
      <div className="sticky top-0 z-20 border-b border-border/60 bg-background/95 p-4 backdrop-blur">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <button
              type="button"
              onClick={onBack}
              className="mb-2 inline-flex items-center gap-1 text-xs font-semibold text-muted-foreground hover:text-foreground"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Volver al flujo
            </button>
            <div className="flex flex-wrap items-center gap-2">
              <h2 className="text-xl font-semibold">{data.radicado || "Sin radicado"}</h2>
              <Badge variant={estadoVariant(data.estado)}>{data.estado_label}</Badge>
            </div>
            <p className="mt-1 max-w-3xl text-sm text-muted-foreground">
              {data.asunto || "Sin asunto registrado"}
            </p>
          </div>
          <a
            href={data.django_detail_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-blue-500/30 px-3 py-1.5 text-xs font-semibold text-blue-400 hover:bg-blue-500/10"
          >
            Detalle Django
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <div className="space-y-4">
          <DetailSection title="Resumen de la salida" icon={<MailCheck className="h-4 w-4 text-blue-400" />}>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <DetailField label="Creación" value={formatFecha(data.fecha_creacion)} />
              <DetailField label="Aprobación" value={formatFecha(data.fecha_aprobacion)} />
              <DetailField label="Envío" value={formatFecha(data.fecha_envio)} />
              <DetailField label="Tipo" value={data.tipo_respuesta_label} />
            </div>
            <div className="mt-3 grid gap-3 md:grid-cols-2">
              <DetailField label="Oficina emisora" value={data.oficina.nombre || "Sin oficina"} />
              <DetailField label="Redactor" value={data.redactor.cargo ? `${data.redactor.nombre} · ${data.redactor.cargo}` : data.redactor.nombre} />
              <DetailField label="Aprobador" value={data.aprobador.nombre || "Sin aprobador"} />
              <DetailField label="Funcionario que envía" value={data.funcionario_envia || "No registrado"} />
            </div>
            <div className="mt-4 rounded-lg border border-border/60 bg-background/60 p-3">
              <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">
                Identificadores de trazabilidad
              </p>
              <MessageIdsBlock item={data} />
            </div>
          </DetailSection>

          <DetailSection title="Entrega y destinatarios" icon={<MailCheck className="h-4 w-4 text-emerald-400" />}>
            <div className="mb-3 grid gap-3 sm:grid-cols-4">
              <DetailField label="Destinatarios" value={data.resumen_entrega.total_destinatarios} />
              <DetailField label="Enviados" value={data.resumen_entrega.enviados} />
              <DetailField label="Fallos" value={data.resumen_entrega.fallos} />
              <DetailField label="Rebotes" value={data.resumen_entrega.rebotes} />
            </div>
            <div className="overflow-hidden rounded-lg border border-border/60">
              <div className="max-h-[360px] overflow-auto">
                <table className="w-full border-collapse text-xs">
                  <thead className="sticky top-0 bg-muted/95 text-left text-[10px] uppercase tracking-wide text-muted-foreground">
                    <tr>
                      <th className="px-3 py-2">Destinatario</th>
                      <th className="px-3 py-2">Estado</th>
                      <th className="px-3 py-2">Entrega</th>
                      <th className="px-3 py-2">Evento</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.destinatarios.map((destinatario) => (
                      <tr key={destinatario.id} className="border-t border-border/40">
                        <td className="px-3 py-2 align-top">
                          <p className="font-semibold">{destinatario.nombre || destinatario.email || "-"}</p>
                          {destinatario.nombre && (
                            <p className="text-muted-foreground">{destinatario.email}</p>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <Badge variant={estadoVariant(destinatario.estado)} className="px-2 py-0 text-[10px]">
                            {destinatario.estado_label || estadoLabel(destinatario.estado)}
                          </Badge>
                          <p className="mt-1 text-muted-foreground">
                            {formatFecha(destinatario.fecha_envio || destinatario.ultimo_evento_at)}
                          </p>
                        </td>
                        <td className="px-3 py-2 align-top">
                          <p className="font-medium">{destinatario.postmark_estado}</p>
                          <div className="mt-1">
                            <MessageIdsBlock item={destinatario} compact />
                          </div>
                        </td>
                        <td className="px-3 py-2 align-top text-muted-foreground">
                          {destinatario.motivo_resumen || destinatario.eventos_postmark[0]?.detalle || "-"}
                          {(destinatario.smtp_code || destinatario.dsn_status) && (
                            <p className="mt-1 font-mono text-[10px] text-amber-400">
                              SMTP {destinatario.smtp_code || "-"} · DSN {destinatario.dsn_status || "-"}
                            </p>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </DetailSection>

          <DetailSection title="Cuerpo / respuesta" icon={<FileText className="h-4 w-4 text-blue-400" />}>
            <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm leading-relaxed text-foreground/85">
              {data.cuerpo || "Sin cuerpo registrado."}
            </pre>
            {(data.motivo_rechazo || data.motivo_respuesta_discrecional) && (
              <div className="mt-3 rounded-lg border border-amber-500/25 bg-amber-500/10 p-3 text-sm text-amber-200">
                {data.motivo_rechazo || data.motivo_respuesta_discrecional}
              </div>
            )}
          </DetailSection>
        </div>

        <div className="space-y-4">
          <DetailSection title="Origen y fallback" icon={<ExternalLink className="h-4 w-4 text-blue-400" />}>
            {data.correspondencia_original ? (
              <div className="space-y-2 text-sm">
                <DetailField label="Radicado original" value={data.correspondencia_original.radicado} />
                <p className="text-muted-foreground">{data.correspondencia_original.asunto}</p>
                <a
                  href={data.correspondencia_original.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:underline"
                >
                  Ver correspondencia original
                  <ExternalLink className="h-3 w-3" />
                </a>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Salida independiente sin correspondencia original asociada.</p>
            )}
          </DetailSection>

          <DetailSection title="Adjuntos y evidencias" icon={<Paperclip className="h-4 w-4 text-blue-400" />}>
            {archivos.length === 0 ? (
              <p className="text-sm text-muted-foreground">No hay adjuntos ni evidencias registradas.</p>
            ) : (
              <div className="space-y-2">
                {archivos.map((archivo) => (
                  <div key={`${archivo.id}-${archivo.nombre}`} className="rounded-lg border border-border/60 bg-background/60 p-3 text-sm">
                    <p className="font-medium">{archivo.nombre}</p>
                    <p className="text-xs text-muted-foreground">{archivo.tipo_mime || "Archivo"} · {formatFecha(archivo.fecha_carga)}</p>
                    {archivo.url && (
                      <a
                        href={archivo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-blue-400 hover:underline"
                      >
                        Abrir archivo
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </DetailSection>

          <DetailSection title="Eventos webhook locales" icon={<MailCheck className="h-4 w-4 text-blue-400" />}>
            {data.eventos_postmark.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin webhooks locales registrados para estos MessageID.</p>
            ) : (
              <div className="space-y-2">
                {data.eventos_postmark.map((evento) => (
                  <div key={evento.id} className="rounded-lg border border-border/60 bg-background/60 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <Badge variant={evento.record_type === "Delivery" ? "success" : evento.record_type === "Bounce" ? "danger" : "info"}>
                        {evento.record_type}
                      </Badge>
                      <span className="text-xs text-muted-foreground">{formatFecha(evento.recibido_at)}</span>
                    </div>
                    <p className="mt-2 text-muted-foreground">{evento.detalle || evento.resultado || "Evento recibido"}</p>
                    {evento.recipient && <p className="mt-1 text-xs text-muted-foreground">{evento.recipient}</p>}
                  </div>
                ))}
              </div>
            )}
          </DetailSection>

          <DetailSection title="Historial de la salida" icon={<History className="h-4 w-4 text-blue-400" />}>
            {data.historial.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin eventos registrados.</p>
            ) : (
              <div className="space-y-2">
                {data.historial.map((evento) => (
                  <div key={evento.id} className="rounded-lg border border-border/60 bg-background/60 p-3 text-sm">
                    <p className="font-semibold">{evento.tipo_label}</p>
                    <p className="text-xs text-muted-foreground">
                      {evento.usuario} · {formatFecha(evento.fecha_hora)}
                    </p>
                    {evento.descripcion && (
                      <p className="mt-1 text-muted-foreground">{evento.descripcion}</p>
                    )}
                  </div>
                ))}
              </div>
            )}
          </DetailSection>
        </div>
      </div>
    </div>
  );
}

function SalidasCorreoContent() {
  const rangoParams = useRangoParams();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [estado, setEstado] = useState("");
  const [oficina, setOficina] = useState("");
  const [selectedSalidaId, setSelectedSalidaId] = useState<number | null>(null);

  const params = useMemo(() => {
    const search = new URLSearchParams();
    search.set("page", String(page));
    search.set("page_size", String(PAGE_SIZE));
    if (query) search.set("q", query);
    if (estado) search.set("estado", estado);
    if (oficina) search.set("oficina", oficina);
    if (rangoParams) {
      const extra = new URLSearchParams(rangoParams);
      extra.forEach((v, k) => search.set(k, v));
    }
    return search.toString();
  }, [estado, oficina, page, query, rangoParams]);

  const { data, error, isLoading, mutate } = useSWR(
    `/api/monitoreo/salidas-correo?${params}`,
    fetcher,
    { keepPreviousData: true }
  );

  const registros: SalidaCorreo[] = data?.registros ?? [];
  const resumenEstados: ResumenEstado[] = data?.resumen_estados ?? [];
  const resumenOficinas: ResumenOficina[] = data?.resumen_oficinas ?? [];
  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;
  const from = total === 0 ? 0 : (page - 1) * PAGE_SIZE + 1;
  const to = Math.min(page * PAGE_SIZE, total);

  const resetPaging = useCallback(() => setPage(1), []);
  const handleSearch = useCallback(() => {
    setQuery(searchInput.trim());
    resetPaging();
  }, [resetPaging, searchInput]);

  return (
    <div className="flex min-h-0 flex-1 flex-col gap-3 overflow-hidden">
      <div className="shrink-0 space-y-3 border-b border-border/60 pb-3">
        <div className="flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => {
              setEstado("");
              resetPaging();
            }}
            className={cn(
              "rounded-full px-3 py-1 text-xs font-semibold transition-colors",
              !estado
                ? "bg-primary text-primary-foreground"
                : "bg-muted/60 text-muted-foreground hover:bg-muted"
            )}
          >
            Todos ({total})
          </button>
          {resumenEstados.map((item) => (
            <button
              key={item.estado}
              type="button"
              onClick={() => {
                setEstado(item.estado === estado ? "" : item.estado);
                resetPaging();
              }}
              className={cn(
                "rounded-full px-3 py-1 text-xs font-semibold transition-colors",
                estado === item.estado
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted"
              )}
            >
              {estadoLabel(item.estado)} ({item.total})
            </button>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {resumenOficinas.length > 0 && (
            <select
              value={oficina}
              onChange={(event) => {
                setOficina(event.target.value);
                resetPaging();
              }}
              className="h-9 min-w-[220px] rounded-md border border-input bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            >
              <option value="">Todas las oficinas</option>
              {resumenOficinas.map((item) => (
                <option key={item.oficina} value={item.oficina}>
                  {item.oficina} ({item.total})
                </option>
              ))}
            </select>
          )}

          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(event) => setSearchInput(event.target.value)}
              onKeyDown={(event) => event.key === "Enter" && handleSearch()}
              placeholder="Buscar radicado, oficina, usuario, correo o MessageID..."
              className="h-9 w-full rounded-md border border-input bg-background pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>

          <button
            type="button"
            onClick={handleSearch}
            className="h-9 rounded-md bg-primary px-4 text-xs font-semibold text-primary-foreground transition-colors hover:bg-primary/90"
          >
            Buscar
          </button>

          <button
            type="button"
            onClick={() => mutate()}
            className="inline-flex h-9 items-center gap-1.5 rounded-md border border-input px-3 text-xs font-semibold hover:bg-muted"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Actualizar
          </button>
        </div>
      </div>

      {selectedSalidaId ? (
        <SalidaCorreoDetailPanel
          salidaId={selectedSalidaId}
          onBack={() => setSelectedSalidaId(null)}
        />
      ) : (
      <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-border/60 bg-card/30">
        {isLoading && registros.length === 0 ? (
          <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
            <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
            Cargando salidas...
          </div>
        ) : error ? (
          <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-sm">
            <p className="font-semibold text-amber-400">
              No se pudo cargar el flujo de correos.
            </p>
            <p className="text-muted-foreground">
              {error.response?.status === 404
                ? "El servidor aún no expone este endpoint. Recargue Gunicorn (HUP) tras desplegar cambios Django."
                : "Revise la sesión de superusuario o intente actualizar de nuevo."}
            </p>
            <button
              type="button"
              onClick={() => mutate()}
              className="mt-1 inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-xs font-semibold hover:bg-muted"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              Reintentar
            </button>
          </div>
        ) : registros.length === 0 ? (
          <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
            No hay salidas de correo en el periodo seleccionado.
          </div>
        ) : (
          <div className="h-full overflow-auto">
            <table className="w-full border-collapse text-xs">
              <thead className="sticky top-0 z-10 border-b border-border/60 bg-muted/95 text-left text-[10px] uppercase tracking-wide text-muted-foreground backdrop-blur">
                <tr>
                  <th className="w-[13%] px-3 py-2 font-semibold">Radicado</th>
                  <th className="w-[16%] px-3 py-2 font-semibold">Oficina</th>
                  <th className="w-[14%] px-3 py-2 font-semibold">Usuario</th>
                  <th className="w-[11%] px-3 py-2 font-semibold">Hora</th>
                  <th className="w-[18%] px-3 py-2 font-semibold">Destinatario</th>
                  <th className="w-[17%] px-3 py-2 font-semibold">MessageID</th>
                  <th className="px-3 py-2 font-semibold">Entrega</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((item) => (
                  <tr
                    key={item.id}
                    className="border-b border-border/40 transition-colors hover:bg-muted/30"
                  >
                    <td className="px-3 py-3 align-top">
                      <RadicadoLink item={item} onSelect={setSelectedSalidaId} />
                      <div className="mt-1">
                        <Badge
                          variant={estadoVariant(item.estado)}
                          className="px-2 py-0 text-[10px]"
                        >
                          {item.estado_label || estadoLabel(item.estado)}
                        </Badge>
                      </div>
                    </td>
                    <td className="px-3 py-3 align-top text-foreground/85">
                      <span className="line-clamp-2">
                        {item.oficina_nombre || "Sin oficina"}
                      </span>
                    </td>
                    <td className="px-3 py-3 align-top text-foreground/85">
                      <span className="line-clamp-2">
                        {item.usuario_nombre || "Sistema"}
                      </span>
                    </td>
                    <td className="whitespace-nowrap px-3 py-3 align-top tabular-nums text-muted-foreground">
                      {formatFecha(item.hora)}
                    </td>
                    <td className="px-3 py-3 align-top">
                      <p className="max-w-[190px] truncate font-semibold">
                        {item.destinatario_nombre || item.destinatario_email || "-"}
                      </p>
                      {item.destinatario_nombre && (
                        <p className="mt-0.5 max-w-[190px] truncate text-muted-foreground">
                          {item.destinatario_email}
                        </p>
                      )}
                    </td>
                        <td className="px-3 py-3 align-top">
                          <MessageIdsBlock item={item} />
                        </td>
                    <td className="px-3 py-3 align-top">
                      <p className="font-medium text-foreground/90">
                        {item.postmark_estado}
                      </p>
                      {item.postmark_recibido_at && (
                        <p className="mt-1 text-[11px] text-muted-foreground">
                          Evento {item.postmark_record_type}: {formatFecha(item.postmark_recibido_at)}
                        </p>
                      )}
                      {item.postmark_detalle && (
                        <p className="mt-1 line-clamp-2 text-[11px] text-muted-foreground">
                          {item.postmark_detalle}
                        </p>
                      )}
                      {(item.smtp_code || item.dsn_status) && (
                        <p className="mt-1 font-mono text-[10px] text-amber-400">
                          SMTP {item.smtp_code || "-"} · DSN {item.dsn_status || "-"}
                        </p>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
      )}

      {!selectedSalidaId && (
      <div className="shrink-0 border-t pt-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs text-muted-foreground tabular-nums">
            Mostrando <span className="font-semibold text-foreground">{from}-{to}</span> de{" "}
            <span className="font-semibold text-foreground">{total}</span> · max. {PAGE_SIZE} por pagina
          </p>
          <div className="flex items-center gap-2">
            <button
              type="button"
              disabled={page <= 1}
              onClick={() => setPage((value) => Math.max(1, value - 1))}
              className="inline-flex h-8 items-center gap-1 rounded-md border border-input px-3 text-xs font-semibold hover:bg-muted disabled:pointer-events-none disabled:opacity-40"
            >
              <ArrowLeft className="h-3.5 w-3.5" />
              Anterior
            </button>
            <span className="text-xs text-muted-foreground">
              Pagina {page} de {pages || 1}
            </span>
            <button
              type="button"
              disabled={pages === 0 || page >= pages}
              onClick={() => setPage((value) => value + 1)}
              className="inline-flex h-8 items-center gap-1 rounded-md border border-input px-3 text-xs font-semibold hover:bg-muted disabled:pointer-events-none disabled:opacity-40"
            >
              Siguiente
              <ArrowRight className="h-3.5 w-3.5" />
            </button>
          </div>
        </div>
      </div>
      )}
    </div>
  );
}

export { SalidasCorreoContent };
