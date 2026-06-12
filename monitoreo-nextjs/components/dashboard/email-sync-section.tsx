"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import api from "@/lib/axios";
import { useEmailSync } from "@/hooks/use-monitoreo";
import { useRangoParams } from "@/hooks/use-rango";
import EmailSyncControlBoard, {
  type EmailSyncBoardData,
} from "@/components/dashboard/email-sync-control-board";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogTrigger,
} from "@/components/ui/dialog";
import {
  RefreshCw,
  CheckCircle2,
  XCircle,
  Clock,
  Wifi,
  WifiOff,
  Maximize2,
  Search,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

type EmailSyncData = EmailSyncBoardData & {
  estado_conexion: string;
  ultima_sincronizacion: string | null;
  correos_procesados_hoy: number;
  errores_sync: number;
  ejecuciones_hoy: number;
  tareas_celery?: {
    activas: number;
    exitosas: number;
    advertencias: number;
    fallidas: number;
  };
};

const MOTIVO_LABELS: Record<string, string> = {
  NOTIFICACION_AUTOMATICA: "Notificación automática",
  NO_APLICABLE: "No aplicable",
  SPAM: "Spam",
  OTRO: "Otro",
  INVITACION_PROMOCIONAL: "Invitación/Promocional",
  DUPLICADO: "Duplicado",
  sin_motivo: "Sin motivo",
};

function ErroresSyncModal() {
  const rangoParams = useRangoParams();
  const [page, setPage] = useState(1);
  const [query, setQuery] = useState("");
  const [searchInput, setSearchInput] = useState("");
  const [motivo, setMotivo] = useState("");

  const params = new URLSearchParams();
  params.set("page", String(page));
  params.set("page_size", "15");
  if (query) params.set("q", query);
  if (motivo) params.set("motivo", motivo);
  if (rangoParams) {
    const extra = new URLSearchParams(rangoParams);
    extra.forEach((v, k) => params.set(k, v));
  }

  const { data, isLoading } = useSWR(
    `/api/monitoreo/errores-sync?${params.toString()}`,
    fetcher,
    { keepPreviousData: true }
  );

  const handleSearch = useCallback(() => {
    setQuery(searchInput);
    setPage(1);
  }, [searchInput]);

  const total = data?.total ?? 0;
  const pages = data?.pages ?? 0;
  const registros = data?.registros ?? [];
  const resumen = data?.resumen_motivos ?? [];

  return (
    <div className="flex flex-col gap-4 min-h-0 flex-1">
      {/* Resumen chips */}
      {resumen.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          <button
            onClick={() => { setMotivo(""); setPage(1); }}
            className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-all ${
              !motivo
                ? "bg-primary text-primary-foreground"
                : "bg-muted/60 text-muted-foreground hover:bg-muted"
            }`}
          >
            Todos ({total})
          </button>
          {resumen.map((m: any) => (
            <button
              key={m.motivo}
              onClick={() => { setMotivo(m.motivo === motivo ? "" : m.motivo); setPage(1); }}
              className={`px-2.5 py-1 rounded-full text-[10px] font-medium transition-all ${
                motivo === m.motivo
                  ? "bg-primary text-primary-foreground"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted"
              }`}
            >
              {MOTIVO_LABELS[m.motivo] || m.motivo} ({m.total})
            </button>
          ))}
        </div>
      )}

      {/* Barra de búsqueda */}
      <div className="flex gap-2">
        <div className="relative flex-1">
          <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground" />
          <input
            type="text"
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSearch()}
            placeholder="Buscar por remitente o asunto…"
            className="w-full h-8 pl-8 pr-3 rounded-md border border-input bg-background text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
        </div>
        <button
          onClick={handleSearch}
          className="h-8 px-3 rounded-md bg-primary text-primary-foreground text-xs font-medium hover:bg-primary/90 transition-colors"
        >
          Buscar
        </button>
      </div>

      {/* Tabla */}
      <div className="overflow-y-auto flex-1 -mx-6 px-6">
        {isLoading && registros.length === 0 ? (
          <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
            <RefreshCw className="h-4 w-4 animate-spin mr-2" />
            Cargando…
          </div>
        ) : registros.length === 0 ? (
          <div className="text-center py-12 text-sm text-muted-foreground">
            No se encontraron errores de sincronización.
          </div>
        ) : (
          <div className="space-y-1.5">
            {registros.map((r: any) => (
              <div
                key={r.id}
                className="flex items-start gap-3 text-xs py-2 px-3 rounded-lg border bg-card hover:bg-muted/30 transition-colors"
              >
                <div className="min-w-0 flex-1 space-y-0.5">
                  <p className="font-medium truncate">{r.asunto || "(Sin asunto)"}</p>
                  <p className="text-muted-foreground truncate">{r.remitente}</p>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  <Badge
                    variant="outline"
                    className="text-[9px]"
                  >
                    {MOTIVO_LABELS[r.motivo] || r.motivo}
                  </Badge>
                  {r.fecha_correo && (
                    <span className="text-[10px] text-muted-foreground whitespace-nowrap">
                      {new Date(r.fecha_correo).toLocaleDateString("es-CO", {
                        day: "2-digit",
                        month: "short",
                      })}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Paginación */}
      {pages > 1 && (
        <div className="flex items-center justify-between pt-2 border-t text-xs text-muted-foreground">
          <span>
            Página {page} de {pages} — {total} registros
          </span>
          <div className="flex items-center gap-1">
            <button
              disabled={page <= 1}
              onClick={() => setPage(page - 1)}
              className="p-1.5 rounded hover:bg-muted disabled:opacity-30 transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <button
              disabled={page >= pages}
              onClick={() => setPage(page + 1)}
              className="p-1.5 rounded hover:bg-muted disabled:opacity-30 transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

export default function EmailSyncSection() {
  const { data, error, isLoading, mutate } = useEmailSync() as {
    data: EmailSyncData | undefined;
    error: unknown;
    isLoading: boolean;
    mutate: () => Promise<EmailSyncData | undefined>;
  };
  const [syncModalOpen, setSyncModalOpen] = useState(false);

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="h-20 bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">
            Error al cargar estado de sincronizacion de correo
          </p>
        </CardContent>
      </Card>
    );
  }

  const d = data!;
  const provider = d.ingestion_provider ?? "imap";
  const isGmailApi = provider === "gmail_api";
  const lastSync = d.ultima_sincronizacion
    ? formatDistanceToNow(new Date(d.ultima_sincronizacion), {
        addSuffix: true,
        locale: es,
      })
    : "Nunca";

  const isHealthy = d.estado_conexion === "ok";
  const erroresCount = d.errores_sync ?? 0;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <RefreshCw className="h-4 w-4 text-primary" />
            Control de sincronizacion de correos
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="text-[10px] uppercase">
              {isGmailApi ? "Gmail API" : "IMAP"}
            </Badge>
            <Badge variant={isHealthy ? "success" : "danger"}>
            {isHealthy ? (
              <Wifi className="h-3 w-3 mr-1" />
            ) : (
              <WifiOff className="h-3 w-3 mr-1" />
            )}
            {d?.estado_conexion ?? "desconocido"}
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Clock className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <p className="text-sm font-medium">{lastSync}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Última sincronización
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <CheckCircle2 className="h-4 w-4 mx-auto mb-1 text-emerald-500" />
            <p className="text-lg font-bold">{d?.correos_procesados_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Procesados hoy
            </p>
          </div>

          {/* Errores sync – clickable to open modal */}
          <Dialog open={syncModalOpen} onOpenChange={setSyncModalOpen}>
            <DialogTrigger asChild>
              <button className="rounded-lg bg-muted/50 p-3 text-center hover:bg-muted/80 transition-colors group relative">
                <XCircle className="h-4 w-4 mx-auto mb-1 text-red-500" />
                <p className="text-lg font-bold">{erroresCount}</p>
                <p className="text-[10px] text-muted-foreground uppercase">
                  Errores sync
                </p>
                <Maximize2 className="h-3 w-3 absolute top-2 right-2 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
            </DialogTrigger>
            <DialogContent className="max-w-2xl max-h-[85vh] overflow-hidden flex flex-col">
              <DialogHeader>
                <DialogTitle className="flex items-center gap-2">
                  <XCircle className="h-4 w-4 text-red-500" />
                  Errores de sincronización
                </DialogTitle>
                <DialogDescription>
                  Correos descartados o en papelera durante la sincronizacion de entrada.
                </DialogDescription>
              </DialogHeader>
              <ErroresSyncModal />
            </DialogContent>
          </Dialog>

          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <RefreshCw className="h-4 w-4 mx-auto mb-1 text-blue-500" />
            <p className="text-lg font-bold">{d?.ejecuciones_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Ejecuciones hoy
            </p>
          </div>
        </div>

        {d?.tareas_celery && (
          <div className="space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase">
              Tareas Celery
            </h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-center text-xs">
              <div className="p-2 rounded bg-emerald-500/10">
                <p className="font-bold text-emerald-500">
                  {d.tareas_celery.activas ?? 0}
                </p>
                <p className="text-muted-foreground">Activas</p>
              </div>
              <div className="p-2 rounded bg-amber-500/10">
                <p className="font-bold text-amber-500">
                  {d.tareas_celery.exitosas ?? 0}
                </p>
                <p className="text-muted-foreground">Exitosas</p>
              </div>
              <div className="p-2 rounded bg-orange-500/10">
                <p className="font-bold text-orange-500">
                  {d.tareas_celery.advertencias ?? 0}
                </p>
                <p className="text-muted-foreground">Advertencias</p>
              </div>
              <div className="p-2 rounded bg-red-500/10">
                <p className="font-bold text-red-500">
                  {d.tareas_celery.fallidas ?? 0}
                </p>
                <p className="text-muted-foreground">Fallidas</p>
              </div>
            </div>
          </div>
        )}

        <EmailSyncControlBoard data={d} mutate={mutate} />
      </CardContent>
    </Card>
  );
}
