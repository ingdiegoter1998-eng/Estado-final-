"use client";

import { useState, useCallback, useMemo, Fragment } from "react";
import useSWR from "swr";
import api from "@/lib/axios";
import { useRangoParams } from "@/hooks/use-rango";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  AlertTriangle,
  Search,
  ChevronLeft,
  ChevronRight,
  ChevronsLeft,
  ChevronsRight,
  RefreshCw,
  Ban,
  ShieldAlert,
  CircleCheck,
  Fingerprint,
  ExternalLink,
  Building2,
  ArrowDown,
  ArrowUp,
  ChevronDown,
  ChevronUp,
  LayoutList,
  Wrench,
} from "lucide-react";

const PAGE_SIZE = 30;

const fetcher = (url: string) => api.get(url).then((r) => r.data);

type VerificacionEnvio = {
  estado_final: string;
  resumen: string;
};

type ReboteRegistro = {
  email: string;
  nombre: string;
  tipo: string;
  error: string;
  motivo_resumen: string;
  smtp_code: string;
  dsn_status: string;
  fecha_envio: string;
  tiene_message_id: boolean;
  message_id: string;
  fecha: string;
  radicado: string;
  salida_id: number | null;
  redactor_nombre: string;
  oficina_nombre: string;
  verificacion_envio: VerificacionEnvio | null;
};

const TIPO_LABELS: Record<string, string> = {
  REBOTE: "Rebote",
  FALLO: "Fallo de envio",
};

const TIPO_LABELS_SIMPLE: Record<string, string> = {
  REBOTE: "Correo rechazado",
  FALLO: "No se pudo enviar",
};

function formatFecha(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function formatFechaCorta(iso: string) {
  if (!iso) return "—";
  return new Date(iso).toLocaleString("es-CO", {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function getExplicacionSimple(r: ReboteRegistro) {
  const v = r.verificacion_envio;
  if (v?.estado_final === "no_entregado") {
    return v.resumen || "El correo no llego al destinatario.";
  }
  if (v?.estado_final === "error_envio") {
    return v.resumen || "No se pudo confirmar que el correo se entrego.";
  }
  if (r.motivo_resumen) return r.motivo_resumen;
  if (r.tipo === "REBOTE") return "El servidor del destinatario rechazo el correo.";
  return "Ocurrio un problema al intentar enviar la correspondencia.";
}

function RadicadoLink({ r }: { r: ReboteRegistro }) {
  if (!r.radicado) return <span className="text-muted-foreground">—</span>;
  if (!r.salida_id) {
    return <span className="font-medium text-foreground">{r.radicado}</span>;
  }
  return (
    <a
      href={`/registros/correspondencia/respuesta/${r.salida_id}/detalle/`}
      target="_blank"
      rel="noopener noreferrer"
      className="font-medium text-blue-400 hover:text-blue-300 underline underline-offset-2 inline-flex items-center gap-1"
      onClick={(e) => e.stopPropagation()}
    >
      {r.radicado}
      <ExternalLink className="h-3 w-3 shrink-0" />
    </a>
  );
}

function VerificationBadge({ item }: { item: ReboteRegistro }) {
  const v = item.verificacion_envio;
  if (!v) return null;

  if (v.estado_final === "no_entregado") {
    return (
      <div className="rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-xs text-red-300 flex items-start gap-2">
        <Ban className="h-4 w-4 mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold text-red-200 mb-0.5">No entregado</p>
          <p className="text-red-300/80">{v.resumen}</p>
        </div>
      </div>
    );
  }

  if (v.estado_final === "error_envio") {
    return (
      <div className="rounded-md border border-amber-500/20 bg-amber-500/10 px-3 py-2 text-xs text-amber-200 flex items-start gap-2">
        <ShieldAlert className="h-4 w-4 mt-0.5 shrink-0" />
        <div>
          <p className="font-semibold text-amber-100 mb-0.5">Envio no confirmado</p>
          <p className="text-amber-200/80">{v.resumen}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md border border-emerald-500/20 bg-emerald-500/10 px-3 py-2 text-xs text-emerald-200 flex items-start gap-2">
      <CircleCheck className="h-4 w-4 mt-0.5 shrink-0" />
      <div>
        <p className="font-semibold text-emerald-100 mb-0.5">Verificacion disponible</p>
        <p className="text-emerald-200/80">{v.resumen}</p>
      </div>
    </div>
  );
}

function AdvancedDetailPanel({ r }: { r: ReboteRegistro }) {
  return (
    <div className="border-t border-border/60 bg-muted/20 px-4 py-3 space-y-3">
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
        <div>
          <span className="text-muted-foreground uppercase tracking-wide block mb-0.5">
            Redactor
          </span>
          <span className="font-medium">{r.redactor_nombre || "No disponible"}</span>
        </div>
        <div>
          <span className="text-muted-foreground uppercase tracking-wide block mb-0.5">
            Intento de envio
          </span>
          <span className="font-medium">{formatFecha(r.fecha_envio)}</span>
        </div>
        <div>
          <span className="text-muted-foreground uppercase tracking-wide block mb-0.5">
            Registro SMTP
          </span>
          <span className="font-medium">{r.tiene_message_id ? "Si" : "No"}</span>
        </div>
        <div>
          <span className="text-muted-foreground uppercase tracking-wide block mb-0.5">
            Codigo SMTP
          </span>
          <span className="font-mono font-semibold text-orange-400">
            {r.smtp_code || "—"}
          </span>
        </div>
        <div>
          <span className="text-muted-foreground uppercase tracking-wide block mb-0.5">
            DSN
          </span>
          <span className="font-mono font-semibold text-orange-400">
            {r.dsn_status || "—"}
          </span>
        </div>
      </div>

      <div className="rounded-lg bg-muted/40 px-3 py-2">
        <span className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wide block mb-1">
          Motivo tecnico
        </span>
        <p className="text-xs text-foreground/90 leading-relaxed">{r.motivo_resumen}</p>
      </div>

      <VerificationBadge item={r} />

      {r.error && (
        <p className="text-[11px] bg-red-500/10 text-red-400 rounded-md px-3 py-2 font-mono break-all leading-relaxed">
          {r.error}
        </p>
      )}

      {r.message_id && (
        <div className="flex items-start gap-1.5 text-[11px] text-muted-foreground bg-muted/30 rounded-md px-3 py-2 font-mono break-all">
          <Fingerprint className="h-3.5 w-3.5 mt-0.5 shrink-0 text-muted-foreground/60" />
          <span>
            <span className="font-sans font-semibold text-foreground/70">Message-ID: </span>
            {r.message_id}
          </span>
        </div>
      )}

      {!r.error && !r.smtp_code && !r.dsn_status && (
        <p className="text-xs text-muted-foreground italic">
          No hay diagnostico DSN tecnico persistido para este registro.
        </p>
      )}
    </div>
  );
}

function PaginationBar({
  page,
  pages,
  total,
  pageSize,
  onPageChange,
}: {
  page: number;
  pages: number;
  total: number;
  pageSize: number;
  onPageChange: (page: number) => void;
}) {
  const from = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const to = Math.min(page * pageSize, total);

  const pageNumbers = useMemo(() => {
    if (pages <= 7) return Array.from({ length: pages }, (_, i) => i + 1);
    const nums = new Set<number>([1, pages, page, page - 1, page + 1]);
    return Array.from(nums)
      .filter((n) => n >= 1 && n <= pages)
      .sort((a, b) => a - b);
  }, [page, pages]);

  if (total === 0) return null;

  return (
    <div className="shrink-0 border-t bg-background/95 backdrop-blur px-1 py-2.5 flex flex-wrap items-center justify-between gap-3">
      <p className="text-xs text-muted-foreground tabular-nums">
        Mostrando <span className="font-semibold text-foreground">{from}–{to}</span> de{" "}
        <span className="font-semibold text-foreground">{total}</span> ·{" "}
        {pageSize} por pagina
      </p>

      <div className="flex items-center gap-1">
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(1)}
          className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
          aria-label="Primera pagina"
        >
          <ChevronsLeft className="h-4 w-4" />
        </button>
        <button
          type="button"
          disabled={page <= 1}
          onClick={() => onPageChange(page - 1)}
          className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
          aria-label="Pagina anterior"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-0.5 px-1">
          {pageNumbers.map((n, idx) => {
            const prev = pageNumbers[idx - 1];
            const gap = prev !== undefined && n - prev > 1;
            return (
              <span key={n} className="flex items-center gap-0.5">
                {gap && <span className="px-1 text-muted-foreground text-xs">…</span>}
                <button
                  type="button"
                  onClick={() => onPageChange(n)}
                  className={cn(
                    "min-w-[2rem] h-8 px-2 rounded-md text-xs font-semibold transition-colors",
                    n === page
                      ? "bg-primary text-primary-foreground"
                      : "hover:bg-muted text-muted-foreground"
                  )}
                >
                  {n}
                </button>
              </span>
            );
          })}
        </div>

        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPageChange(page + 1)}
          className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
          aria-label="Pagina siguiente"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
        <button
          type="button"
          disabled={page >= pages}
          onClick={() => onPageChange(pages)}
          className="p-1.5 rounded-md hover:bg-muted disabled:opacity-30 disabled:pointer-events-none transition-colors"
          aria-label="Ultima pagina"
        >
          <ChevronsRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}

function RebotesModalContent() {
  const rangoParams = useRangoParams();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [tipo, setTipo] = useState("");
  const [oficina, setOficina] = useState("");
  const [order, setOrder] = useState<"desc" | "asc">("desc");
  const [viewMode, setViewMode] = useState<"simple" | "advanced">("simple");
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", String(PAGE_SIZE));
  params.set("order", order);
  if (query) params.set("q", query);
  if (tipo) params.set("tipo", tipo);
  if (oficina) params.set("oficina", oficina);
  if (rangoParams) {
    const extra = new URLSearchParams(rangoParams);
    extra.forEach((v, k) => params.set(k, v));
  }

  const { data, isLoading } = useSWR(
    `/api/monitoreo/rebotes?${params.toString()}`,
    fetcher,
    { keepPreviousData: true }
  );

  const handleSearch = useCallback(() => {
    setQuery(searchInput);
    setPage(1);
    setExpandedId(null);
  }, [searchInput]);

  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;
  const registros: ReboteRegistro[] = data?.registros ?? [];
  const resumenTipos = data?.resumen_tipos ?? [];
  const resumenOficinas: Array<{ oficina: string; total: number }> =
    data?.resumen_oficinas ?? [];

  const rowKey = (r: ReboteRegistro, i: number) =>
    `${r.radicado}-${r.email}-${r.fecha}-${i}`;

  return (
    <div className="flex flex-col min-h-0 flex-1 overflow-hidden gap-0">
      <div className="shrink-0 space-y-3 pb-3 border-b border-border/60">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <Tabs
            value={viewMode}
            onValueChange={(v) => {
              setViewMode(v as "simple" | "advanced");
              setExpandedId(null);
            }}
          >
            <TabsList className="h-9">
              <TabsTrigger value="simple" className="gap-1.5 text-xs px-3">
                <LayoutList className="h-3.5 w-3.5" />
                Modo simple
              </TabsTrigger>
              <TabsTrigger value="advanced" className="gap-1.5 text-xs px-3">
                <Wrench className="h-3.5 w-3.5" />
                Modo avanzado
              </TabsTrigger>
            </TabsList>
          </Tabs>

          <p className="text-xs text-muted-foreground hidden sm:block">
            {viewMode === "simple"
              ? "Lenguaje claro para seguimiento administrativo."
              : "Detalle tecnico: SMTP, DSN, Message-ID y errores crudos."}
          </p>
        </div>

        {resumenTipos.length > 0 && (
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() => {
                setTipo("");
                setPage(1);
                setExpandedId(null);
              }}
              className={cn(
                "px-3 py-1 rounded-full text-xs font-semibold transition-all",
                !tipo
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted"
              )}
            >
              Todos ({total})
            </button>
            {resumenTipos.map((t: { tipo: string; total: number }) => (
              <button
                key={t.tipo}
                type="button"
                onClick={() => {
                  setTipo(t.tipo === tipo ? "" : t.tipo);
                  setPage(1);
                  setExpandedId(null);
                }}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-semibold transition-all",
                  tipo === t.tipo
                    ? "bg-primary text-primary-foreground"
                    : "bg-muted/60 text-muted-foreground hover:bg-muted"
                )}
              >
                {(viewMode === "simple" ? TIPO_LABELS_SIMPLE : TIPO_LABELS)[t.tipo] ||
                  t.tipo}{" "}
                ({t.total})
              </button>
            ))}
          </div>
        )}

        <div className="flex flex-wrap items-center gap-2">
          {resumenOficinas.length > 0 && (
            <div className="relative">
              <Building2 className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
              <select
                value={oficina}
                onChange={(e) => {
                  setOficina(e.target.value);
                  setPage(1);
                  setExpandedId(null);
                }}
                className="h-8 w-full sm:w-auto pl-8 pr-7 rounded-md border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-ring appearance-none cursor-pointer min-w-[200px]"
              >
                <option value="">Todas las oficinas</option>
                {resumenOficinas.map((o) => (
                  <option key={o.oficina} value={o.oficina}>
                    {o.oficina} ({o.total})
                  </option>
                ))}
              </select>
              <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
            </div>
          )}

          <button
            type="button"
            onClick={() => {
              setOrder(order === "desc" ? "asc" : "desc");
              setPage(1);
              setExpandedId(null);
            }}
            className="h-8 px-3 rounded-md border border-input bg-background text-xs flex items-center justify-center gap-1.5 hover:bg-muted transition-colors whitespace-nowrap w-fit"
          >
            {order === "desc" ? (
              <ArrowDown className="h-3.5 w-3.5" />
            ) : (
              <ArrowUp className="h-3.5 w-3.5" />
            )}
            {order === "desc" ? "Mas recientes" : "Mas antiguos"}
          </button>

          <div className="flex flex-1 min-w-[220px] items-center gap-2">
            <div className="relative flex-1 min-w-0">
              <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
              <input
                type="text"
                value={searchInput}
                onChange={(e) => setSearchInput(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && handleSearch()}
                placeholder="Buscar por email, nombre, redactor o radicado..."
                className="w-full h-8 pl-8 pr-3 rounded-md border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-ring"
              />
            </div>

            <button
              type="button"
              onClick={handleSearch}
              className="h-8 px-4 rounded-md bg-primary text-primary-foreground text-xs font-semibold hover:bg-primary/90 transition-colors shrink-0 w-fit"
            >
              Buscar
            </button>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 flex flex-col border border-border/60 rounded-lg mt-3 overflow-hidden bg-card/30">
        {isLoading && registros.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground">
            <RefreshCw className="h-5 w-5 animate-spin mr-2" />
            Cargando registros...
          </div>
        ) : registros.length === 0 ? (
          <div className="flex-1 flex items-center justify-center text-sm text-muted-foreground px-6 text-center">
            No se encontraron errores de envio en el periodo seleccionado.
          </div>
        ) : viewMode === "simple" ? (
          <div className="flex-1 min-h-0 overflow-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0 z-10 bg-muted/95 backdrop-blur border-b border-border/60">
                <tr className="text-left text-muted-foreground uppercase tracking-wide text-[10px]">
                  <th className="px-3 py-2 font-semibold w-[22%]">Destinatario</th>
                  <th className="px-3 py-2 font-semibold w-[14%]">Radicado</th>
                  <th className="px-3 py-2 font-semibold w-[16%]">Oficina</th>
                  <th className="px-3 py-2 font-semibold w-[11%]">Fecha</th>
                  <th className="px-3 py-2 font-semibold">Que paso</th>
                  <th className="px-3 py-2 font-semibold w-[12%]">Estado</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((r, i) => (
                  <tr
                    key={rowKey(r, i)}
                    className="border-b border-border/40 hover:bg-muted/30 transition-colors"
                  >
                    <td className="px-3 py-2 align-top">
                      <p className="font-semibold text-foreground truncate max-w-[180px]">
                        {r.nombre || r.email}
                      </p>
                      {r.nombre && (
                        <p className="text-muted-foreground truncate max-w-[180px] mt-0.5">
                          {r.email}
                        </p>
                      )}
                    </td>
                    <td className="px-3 py-2 align-top">
                      <RadicadoLink r={r} />
                    </td>
                    <td className="px-3 py-2 align-top text-foreground/80">
                      <span className="line-clamp-2">{r.oficina_nombre || "Sin oficina"}</span>
                    </td>
                    <td className="px-3 py-2 align-top text-muted-foreground whitespace-nowrap tabular-nums">
                      {formatFechaCorta(r.fecha)}
                    </td>
                    <td className="px-3 py-2 align-top text-foreground/90 leading-snug">
                      <span className="line-clamp-2">{getExplicacionSimple(r)}</span>
                    </td>
                    <td className="px-3 py-2 align-top">
                      <Badge variant="danger" className="text-[10px] px-2 py-0 whitespace-nowrap">
                        {TIPO_LABELS_SIMPLE[r.tipo] || r.tipo}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="flex-1 min-h-0 overflow-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0 z-10 bg-muted/95 backdrop-blur border-b border-border/60">
                <tr className="text-left text-muted-foreground uppercase tracking-wide text-[10px]">
                  <th className="px-3 py-2 font-semibold w-8" />
                  <th className="px-3 py-2 font-semibold w-[20%]">Destinatario</th>
                  <th className="px-3 py-2 font-semibold w-[13%]">Radicado</th>
                  <th className="px-3 py-2 font-semibold w-[8%]">SMTP</th>
                  <th className="px-3 py-2 font-semibold w-[8%]">DSN</th>
                  <th className="px-3 py-2 font-semibold w-[11%]">Fecha</th>
                  <th className="px-3 py-2 font-semibold w-[12%]">Tipo</th>
                  <th className="px-3 py-2 font-semibold">Motivo</th>
                </tr>
              </thead>
              <tbody>
                {registros.map((r, i) => {
                  const key = rowKey(r, i);
                  const isOpen = expandedId === key;
                  return (
                    <Fragment key={key}>
                      <tr
                        className={cn(
                          "border-b border-border/40 cursor-pointer transition-colors",
                          isOpen ? "bg-muted/40" : "hover:bg-muted/30"
                        )}
                        onClick={() => setExpandedId(isOpen ? null : key)}
                      >
                        <td className="px-2 py-2 text-muted-foreground">
                          {isOpen ? (
                            <ChevronUp className="h-3.5 w-3.5" />
                          ) : (
                            <ChevronDown className="h-3.5 w-3.5" />
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <p className="font-semibold truncate max-w-[160px]">
                            {r.nombre || r.email}
                          </p>
                          {r.nombre && (
                            <p className="text-muted-foreground truncate max-w-[160px]">
                              {r.email}
                            </p>
                          )}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <RadicadoLink r={r} />
                        </td>
                        <td className="px-3 py-2 align-top font-mono text-orange-400">
                          {r.smtp_code || "—"}
                        </td>
                        <td className="px-3 py-2 align-top font-mono text-orange-400">
                          {r.dsn_status || "—"}
                        </td>
                        <td className="px-3 py-2 align-top text-muted-foreground whitespace-nowrap tabular-nums">
                          {formatFechaCorta(r.fecha)}
                        </td>
                        <td className="px-3 py-2 align-top">
                          <Badge variant="danger" className="text-[10px] px-2 py-0">
                            {TIPO_LABELS[r.tipo] || r.tipo}
                          </Badge>
                        </td>
                        <td className="px-3 py-2 align-top text-foreground/80 line-clamp-2">
                          {r.motivo_resumen}
                        </td>
                      </tr>
                      {isOpen && (
                        <tr>
                          <td colSpan={8} className="p-0">
                            <AdvancedDetailPanel r={r} />
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <PaginationBar
          page={page}
          pages={pages}
          total={total}
          pageSize={PAGE_SIZE}
          onPageChange={(p) => {
            setPage(p);
            setExpandedId(null);
          }}
        />
      </div>
    </div>
  );
}

export default function RebotesGlobalModal() {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="w-full flex items-center justify-center gap-3 px-6 py-4 rounded-xl border-2 border-dashed border-red-500/30 bg-red-500/5 hover:bg-red-500/10 hover:border-red-500/50 transition-all group"
      >
        <AlertTriangle className="h-6 w-6 text-red-500 group-hover:scale-110 transition-transform" />
        <div className="text-left">
          <p className="text-sm font-semibold text-foreground">Ver todos los errores de envio</p>
          <p className="text-xs text-muted-foreground">
            Rebotes y fallos del ultimo mes · vista simple o avanzada
          </p>
        </div>
        <AlertTriangle className="h-6 w-6 text-red-500 group-hover:scale-110 transition-transform" />
      </button>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-w-7xl h-[92vh] overflow-hidden flex flex-col p-4 sm:p-6 gap-3">
          <DialogHeader className="shrink-0 space-y-1">
            <DialogTitle className="flex items-center gap-2 text-lg">
              <AlertTriangle className="h-5 w-5 text-red-500" />
              Todos los errores de envio
            </DialogTitle>
            <DialogDescription className="text-xs sm:text-sm">
              Revise hasta {PAGE_SIZE} correspondencias por pagina. Use modo simple para seguimiento
              administrativo o modo avanzado para diagnostico tecnico.
            </DialogDescription>
          </DialogHeader>
          <RebotesModalContent />
        </DialogContent>
      </Dialog>
    </>
  );
}
