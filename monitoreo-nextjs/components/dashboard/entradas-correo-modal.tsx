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
  Inbox,
  Loader2,
  Mail,
  RefreshCw,
  Search,
} from "lucide-react";
import api from "@/lib/axios";
import { cn } from "@/lib/utils";
import { useRangoParams } from "@/hooks/use-rango";
import { Badge } from "@/components/ui/badge";

const PAGE_SIZE = 50;

const fetcher = (url: string) => api.get(url).then((r) => r.data);

type EntradaCorreo = {
  id: number;
  message_id: string;
  remitente: string;
  asunto: string;
  hora: string;
  fecha_ingesta_bd: string;
  estado: string;
  estado_label: string;
  motivo_papelera: string;
  motivo_papelera_label: string;
  oficina_destino: string;
  radicado_asociado: string;
  radicado_asociado_id: number | null;
  ingestion_provider: string;
  en_papelera?: boolean;
};

type ResumenEstado = { estado: string; total: number; label?: string };
type ResumenMotivo = { motivo: string; total: number; label?: string };

type EntradaCorreoDetalle = {
  id: number;
  message_id: string;
  remitente: string;
  asunto: string;
  estado: string;
  estado_label: string;
  cuerpo_texto: string;
  cuerpo_html: string;
  fecha_recepcion_original: string;
  fecha_recibida_gmail: string;
  fecha_lectura_imap: string;
  procesado: boolean;
  en_papelera: boolean;
  motivo_papelera_label: string;
  requiere_revision_manual: boolean;
  ingestion_provider: string;
  sync_pipeline: { estado: string; ultimo_fin: string; ultimo_error: string };
  clasificacion: {
    oficina: string;
    serie: string;
    subserie: string;
    fecha_clasificacion: string;
  } | null;
  radicado_asociado: {
    id: number;
    radicado: string;
    asunto: string;
    oficina_destino: string;
    url: string;
  } | null;
  urgencia_asociada: { id: number; radicado: string; estado: string } | null;
  problematico: {
    id: number;
    resuelto: boolean;
    motivo_problema: string;
    detalle_problema: string;
    django_detail_url: string;
  } | null;
  adjuntos: { id: number; nombre: string; tipo_mime: string; fecha_carga: string; url: string }[];
  historial: {
    id: number;
    tipo: string;
    tipo_label: string;
    descripcion: string;
    fecha_hora: string;
    usuario: string;
  }[];
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
  if (estado === "RADICADO" || estado === "RECIBIDO") return "success";
  if (estado === "PAPELERA" || estado === "PROBLEMATICO") return "danger";
  if (estado === "REVISION" || estado === "EN_COLA") return "warning";
  if (estado === "CLASIFICADO" || estado === "URGENCIA") return "info";
  return "secondary";
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

function DetailField({ label, value }: { label: string; value?: string | number | null }) {
  return (
    <div className="rounded-lg border border-border/60 bg-background/60 p-3">
      <p className="text-[10px] font-semibold uppercase tracking-wide text-muted-foreground">{label}</p>
      <p className="mt-1 text-sm font-medium text-foreground/90">{value ?? "-"}</p>
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

function EntradaCorreoDetailPanel({
  correoId,
  onBack,
}: {
  correoId: number;
  onBack: () => void;
}) {
  const { data, error, isLoading, mutate } = useSWR<EntradaCorreoDetalle>(
    `/api/monitoreo/entradas-correo/${correoId}/detalle`,
    fetcher
  );

  if (isLoading) {
    return (
      <div className="flex min-h-0 flex-1 items-center justify-center rounded-lg border border-border/60 bg-card/30 text-sm text-muted-foreground">
        <Loader2 className="mr-2 h-5 w-5 animate-spin" />
        Cargando detalle del correo entrante...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="flex min-h-0 flex-1 flex-col items-center justify-center gap-3 rounded-lg border border-border/60 bg-card/30 px-6 text-center text-sm">
        <p className="font-semibold text-amber-400">No se pudo cargar el detalle del correo.</p>
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
              <h2 className="text-xl font-semibold">{data.asunto || "(Sin asunto)"}</h2>
              <Badge variant={estadoVariant(data.estado)}>{data.estado_label}</Badge>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">{data.remitente}</p>
          </div>
          <a
            href={data.django_detail_url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 px-3 py-1.5 text-xs font-semibold text-emerald-400 hover:bg-emerald-500/10"
          >
            Ventanilla Django
            <ExternalLink className="h-3.5 w-3.5" />
          </a>
        </div>
      </div>

      <div className="grid gap-4 p-4 xl:grid-cols-[minmax(0,1.25fr)_minmax(360px,0.75fr)]">
        <div className="space-y-4">
          <DetailSection title="Resumen de ingesta" icon={<Inbox className="h-4 w-4 text-emerald-400" />}>
            <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
              <DetailField label="Recibido en Gmail" value={formatFecha(data.fecha_recibida_gmail)} />
              <DetailField label="Ingesta en BD" value={formatFecha(data.fecha_lectura_imap)} />
              <DetailField label="Provider" value={data.ingestion_provider} />
              <DetailField label="Procesado" value={data.procesado ? "Sí" : "No"} />
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-2">
              <code className="max-w-full truncate rounded-md bg-muted/70 px-2 py-1 text-[11px]">
                {data.message_id || "Sin Message-ID"}
              </code>
              <CopyButton value={data.message_id} label="Message-ID" />
            </div>
          </DetailSection>

          {data.clasificacion && (
            <DetailSection title="Clasificación IA" icon={<FileText className="h-4 w-4 text-emerald-400" />}>
              <div className="grid gap-3 md:grid-cols-3">
                <DetailField label="Oficina" value={data.clasificacion.oficina} />
                <DetailField label="Serie" value={data.clasificacion.serie} />
                <DetailField label="Subserie" value={data.clasificacion.subserie} />
              </div>
            </DetailSection>
          )}

          <DetailSection title="Cuerpo del correo" icon={<Mail className="h-4 w-4 text-emerald-400" />}>
            <pre className="max-h-[360px] overflow-auto whitespace-pre-wrap rounded-lg bg-muted/40 p-3 text-sm leading-relaxed text-foreground/85">
              {data.cuerpo_texto || "Sin cuerpo en texto plano."}
            </pre>
          </DetailSection>
        </div>

        <div className="space-y-4">
          {data.radicado_asociado && (
            <DetailSection title="Radicado derivado" icon={<ExternalLink className="h-4 w-4 text-emerald-400" />}>
              <DetailField label="Radicado" value={data.radicado_asociado.radicado} />
              <p className="mt-2 text-sm text-muted-foreground">{data.radicado_asociado.asunto}</p>
              <a
                href={data.radicado_asociado.url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:underline"
              >
                Ver correspondencia
                <ExternalLink className="h-3 w-3" />
              </a>
            </DetailSection>
          )}

          {data.problematico && !data.problematico.resuelto && (
            <DetailSection title="Correo problemático" icon={<FileText className="h-4 w-4 text-amber-400" />}>
              <p className="text-sm text-amber-200">{data.problematico.detalle_problema || data.problematico.motivo_problema}</p>
              <a
                href={data.problematico.django_detail_url}
                target="_blank"
                rel="noopener noreferrer"
                className="mt-2 inline-flex items-center gap-1 text-xs font-semibold text-amber-400 hover:underline"
              >
                Revisar en ventanilla
                <ExternalLink className="h-3 w-3" />
              </a>
            </DetailSection>
          )}

          {data.en_papelera && (
            <DetailSection title="Papelera" icon={<FileText className="h-4 w-4 text-red-400" />}>
              <DetailField label="Motivo" value={data.motivo_papelera_label} />
            </DetailSection>
          )}

          <DetailSection title="Pipeline de sync" icon={<RefreshCw className="h-4 w-4 text-emerald-400" />}>
            <DetailField label="Estado pipeline" value={data.sync_pipeline.estado || "Sin registro"} />
            <DetailField label="Último fin" value={formatFecha(data.sync_pipeline.ultimo_fin)} />
            {data.sync_pipeline.ultimo_error && (
              <p className="mt-2 text-xs text-destructive">{data.sync_pipeline.ultimo_error}</p>
            )}
            <p className="mt-2 text-[11px] text-muted-foreground">
              Acciones operativas (verificar, recuperar) están en la pestaña Sistema del monitoreo.
            </p>
          </DetailSection>

          <DetailSection title="Adjuntos" icon={<FileText className="h-4 w-4 text-emerald-400" />}>
            {data.adjuntos.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin adjuntos.</p>
            ) : (
              <div className="space-y-2">
                {data.adjuntos.map((archivo) => (
                  <div key={archivo.id} className="rounded-lg border border-border/60 bg-background/60 p-3 text-sm">
                    <p className="font-medium">{archivo.nombre}</p>
                    {archivo.url && (
                      <a
                        href={archivo.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-1 inline-flex items-center gap-1 text-xs font-semibold text-emerald-400 hover:underline"
                      >
                        Abrir
                        <ExternalLink className="h-3 w-3" />
                      </a>
                    )}
                  </div>
                ))}
              </div>
            )}
          </DetailSection>

          <DetailSection title="Historial operativo" icon={<History className="h-4 w-4 text-emerald-400" />}>
            {data.historial.length === 0 ? (
              <p className="text-sm text-muted-foreground">Sin eventos.</p>
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

function EntradasCorreoContent() {
  const rangoParams = useRangoParams();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [estado, setEstado] = useState("");
  const [motivo, setMotivo] = useState("");
  const [selectedCorreoId, setSelectedCorreoId] = useState<number | null>(null);

  const params = useMemo(() => {
    const search = new URLSearchParams();
    search.set("page", String(page));
    search.set("page_size", String(PAGE_SIZE));
    if (query) search.set("q", query);
    if (estado) search.set("estado", estado);
    if (motivo) search.set("motivo", motivo);
    if (rangoParams) {
      const extra = new URLSearchParams(rangoParams);
      extra.forEach((v, k) => search.set(k, v));
    }
    return search.toString();
  }, [estado, motivo, page, query, rangoParams]);

  const { data, error, isLoading, mutate } = useSWR(
    `/api/monitoreo/entradas-correo?${params}`,
    fetcher,
    { keepPreviousData: true }
  );

  const registros: EntradaCorreo[] = data?.registros ?? [];
  const resumenEstados: ResumenEstado[] = data?.resumen_estados ?? [];
  const resumenMotivos: ResumenMotivo[] = data?.resumen_motivos ?? [];
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
              !estado ? "bg-primary text-primary-foreground" : "bg-muted/60 text-muted-foreground hover:bg-muted"
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
              {item.label || item.estado} ({item.total})
            </button>
          ))}
        </div>

        {resumenMotivos.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            {resumenMotivos.map((item) => (
              <button
                key={item.motivo}
                type="button"
                onClick={() => {
                  setMotivo(item.motivo === motivo ? "" : item.motivo);
                  resetPaging();
                }}
                className={cn(
                  "rounded-full px-2.5 py-1 text-[10px] font-medium transition-colors",
                  motivo === item.motivo
                    ? "bg-amber-600 text-white"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted"
                )}
              >
                {item.label || item.motivo} ({item.total})
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <div className="relative min-w-[220px] flex-1">
            <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-muted-foreground" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleSearch()}
              placeholder="Buscar remitente, asunto, Message-ID o radicado..."
              className="h-9 w-full rounded-md border border-input bg-background pl-8 pr-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
            />
          </div>
          <button
            type="button"
            onClick={handleSearch}
            className="h-9 rounded-md bg-primary px-4 text-xs font-semibold text-primary-foreground hover:bg-primary/90"
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

      {selectedCorreoId ? (
        <EntradaCorreoDetailPanel correoId={selectedCorreoId} onBack={() => setSelectedCorreoId(null)} />
      ) : (
        <div className="min-h-0 flex-1 overflow-hidden rounded-lg border border-border/60 bg-card/30">
          {isLoading && registros.length === 0 ? (
            <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
              <RefreshCw className="mr-2 h-5 w-5 animate-spin" />
              Cargando entradas...
            </div>
          ) : error ? (
            <div className="flex h-full flex-col items-center justify-center gap-2 px-6 text-center text-sm">
              <p className="font-semibold text-amber-400">No se pudo cargar el flujo de entrada.</p>
              <button type="button" onClick={() => mutate()} className="mt-1 inline-flex items-center gap-1.5 rounded-md border border-input px-3 py-1.5 text-xs font-semibold hover:bg-muted">
                <RefreshCw className="h-3.5 w-3.5" />
                Reintentar
              </button>
            </div>
          ) : registros.length === 0 ? (
            <div className="flex h-full items-center justify-center px-6 text-center text-sm text-muted-foreground">
              No hay correos entrantes en el periodo seleccionado.
            </div>
          ) : (
            <div className="h-full overflow-auto">
              <table className="w-full border-collapse text-xs">
                <thead className="sticky top-0 z-10 border-b border-border/60 bg-muted/95 text-left text-[10px] uppercase tracking-wide text-muted-foreground backdrop-blur">
                  <tr>
                    <th className="w-[14%] px-3 py-2 font-semibold">Remitente</th>
                    <th className="w-[18%] px-3 py-2 font-semibold">Asunto</th>
                    <th className="w-[11%] px-3 py-2 font-semibold">Recibido</th>
                    <th className="w-[11%] px-3 py-2 font-semibold">Ingesta BD</th>
                    <th className="w-[14%] px-3 py-2 font-semibold">Estado</th>
                    <th className="w-[14%] px-3 py-2 font-semibold">Destino operativo</th>
                    <th className="px-3 py-2 font-semibold">Message-ID</th>
                  </tr>
                </thead>
                <tbody>
                  {registros.map((item) => (
                    <tr key={item.id} className="border-b border-border/40 transition-colors hover:bg-muted/30">
                      <td className="px-3 py-3 align-top">
                        <p className="max-w-[160px] truncate font-semibold">{item.remitente || "-"}</p>
                      </td>
                      <td className="px-3 py-3 align-top">
                        <button
                          type="button"
                          className="line-clamp-2 text-left font-medium text-emerald-400 underline underline-offset-2 hover:text-emerald-300"
                          onClick={() => setSelectedCorreoId(item.id)}
                        >
                          {item.asunto || "(Sin asunto)"}
                        </button>
                        {item.radicado_asociado && (
                          <p className="mt-1 text-[10px] text-muted-foreground">→ {item.radicado_asociado}</p>
                        )}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 align-top tabular-nums text-muted-foreground">
                        {formatFecha(item.hora)}
                      </td>
                      <td className="whitespace-nowrap px-3 py-3 align-top tabular-nums text-muted-foreground">
                        {formatFecha(item.fecha_ingesta_bd)}
                      </td>
                      <td className="px-3 py-3 align-top">
                        <Badge variant={estadoVariant(item.estado)} className="px-2 py-0 text-[10px]">
                          {item.estado_label}
                        </Badge>
                        {item.en_papelera && item.motivo_papelera_label && (
                          <p className="mt-1 text-[10px] text-muted-foreground">{item.motivo_papelera_label}</p>
                        )}
                      </td>
                      <td className="px-3 py-3 align-top text-foreground/85">
                        {item.oficina_destino || "Sin asignar"}
                      </td>
                      <td className="px-3 py-3 align-top">
                        <code className="block max-w-[200px] truncate rounded bg-muted/70 px-1.5 py-1 text-[10px]">
                          {item.message_id || "-"}
                        </code>
                        {item.message_id && (
                          <CopyButton value={item.message_id} label="Message-ID" />
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

      {!selectedCorreoId && (
        <div className="shrink-0 border-t pt-3">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground tabular-nums">
              Mostrando {from}-{to} de {total} · max. {PAGE_SIZE} por pagina
            </p>
            <div className="flex items-center gap-2">
              <button
                type="button"
                disabled={page <= 1}
                onClick={() => setPage((v) => Math.max(1, v - 1))}
                className="inline-flex h-8 items-center gap-1 rounded-md border border-input px-3 text-xs font-semibold hover:bg-muted disabled:opacity-40"
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
                onClick={() => setPage((v) => v + 1)}
                className="inline-flex h-8 items-center gap-1 rounded-md border border-input px-3 text-xs font-semibold hover:bg-muted disabled:opacity-40"
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

export { EntradasCorreoContent };
