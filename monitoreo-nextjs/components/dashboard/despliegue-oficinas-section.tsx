"use client";

import { useMemo, useState } from "react";
import { format, formatDistanceToNow, parseISO } from "date-fns";
import { es } from "date-fns/locale";
import { mutate } from "swr";
import {
  Building2,
  Users,
  UserX,
  AlertCircle,
  CheckCircle2,
  MapPin,
  Search,
  Save,
} from "lucide-react";
import {
  useDespliegueOficinas,
  type DespliegueFiltro,
  type DespliegueOrden,
} from "@/hooks/use-monitoreo";
import api from "@/lib/axios";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

type EstadoOperativo = "operativa" | "sin_usuarios" | "inactiva";
type EstadoVisita = "pendiente" | "visitada" | "capacitada" | "no_aplica";

interface OficinaDespliegue {
  id: number;
  nombre: string;
  codigo: string;
  unidad_id: number | null;
  unidad_nombre: string;
  proceso_nombre: string;
  usuarios_activos: number;
  usuarios_total: number;
  tiene_lider: boolean;
  tiene_trd: boolean;
  estado_operativo: EstadoOperativo;
  estado_visita: EstadoVisita;
  fecha_visita: string | null;
  notas: string;
  ultimo_login_oficina: string | null;
  ultima_correspondencia: string | null;
  ultima_actividad: string | null;
  usuarios: {
    id: number;
    username: string;
    nombre: string;
    cargo: string;
    is_active: boolean;
    es_lider: boolean;
    last_login: string | null;
  }[];
}

const FILTROS: { id: DespliegueFiltro; label: string }[] = [
  { id: "", label: "Todas" },
  { id: "prioridad", label: "Prioridad (sin usuarios)" },
  { id: "sin_usuarios", label: "Sin usuarios activos" },
  { id: "inactiva", label: "Inactivas (meses)" },
  { id: "operativa", label: "Operativas" },
  { id: "pendiente_visita", label: "Visita pendiente" },
  { id: "visitada", label: "Visitadas" },
  { id: "capacitada", label: "Capacitadas" },
  { id: "sin_lider", label: "Sin líder" },
  { id: "sin_trd", label: "Sin TRD/código" },
];

const ORDENES: { id: DespliegueOrden; label: string }[] = [
  { id: "pendiente", label: "Pendientes primero" },
  { id: "nombre", label: "Nombre A–Z" },
  { id: "usuarios_activos", label: "Más usuarios activos" },
  { id: "ultima_actividad", label: "Última actividad" },
  { id: "unidad", label: "Unidad administrativa" },
];

function cardTone(estado: EstadoOperativo): string {
  if (estado === "operativa") {
    return "border-emerald-500/40 bg-emerald-500/5 hover:bg-emerald-500/10";
  }
  if (estado === "sin_usuarios") {
    return "border-red-500/40 bg-red-500/5 hover:bg-red-500/10";
  }
  return "border-slate-500/35 bg-slate-500/5 hover:bg-slate-500/10";
}

function estadoOperativoLabel(estado: EstadoOperativo): string {
  const map: Record<EstadoOperativo, string> = {
    operativa: "Operativa",
    sin_usuarios: "Sin usuarios",
    inactiva: "Inactiva",
  };
  return map[estado];
}

function estadoVisitaLabel(estado: EstadoVisita): string {
  const map: Record<EstadoVisita, string> = {
    pendiente: "Pendiente",
    visitada: "Visitada",
    capacitada: "Capacitada",
    no_aplica: "No aplica",
  };
  return map[estado];
}

function fmtFecha(iso: string | null): string {
  if (!iso) return "—";
  try {
    return format(parseISO(iso), "d MMM yyyy HH:mm", { locale: es });
  } catch {
    return "—";
  }
}

function fmtRelativo(iso: string | null): string {
  if (!iso) return "Nunca";
  try {
    return formatDistanceToNow(parseISO(iso), { addSuffix: true, locale: es });
  } catch {
    return "—";
  }
}

function buildEndpoint(params: {
  meses: number;
  filtro: DespliegueFiltro;
  q: string;
  orden: DespliegueOrden;
  unidadId: string;
}) {
  const search = new URLSearchParams();
  if (params.meses) search.set("meses", String(params.meses));
  if (params.filtro) search.set("filtro", params.filtro);
  if (params.q) search.set("q", params.q);
  if (params.orden) search.set("orden", params.orden);
  if (params.unidadId) search.set("unidad_id", params.unidadId);
  const qs = search.toString();
  return `/api/monitoreo/despliegue-oficinas${qs ? `?${qs}` : ""}`;
}

export default function DespliegueOficinasSection() {
  const [meses, setMeses] = useState(3);
  const [filtro, setFiltro] = useState<DespliegueFiltro>("");
  const [q, setQ] = useState("");
  const [orden, setOrden] = useState<DespliegueOrden>("pendiente");
  const [unidadId, setUnidadId] = useState("");
  const [selected, setSelected] = useState<OficinaDespliegue | null>(null);
  const [editVisita, setEditVisita] = useState<EstadoVisita>("pendiente");
  const [editFecha, setEditFecha] = useState("");
  const [editNotas, setEditNotas] = useState("");
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState("");

  const { data, error, isLoading } = useDespliegueOficinas({
    meses,
    filtro,
    q,
    orden,
    unidadId,
  });

  const swrKey = useMemo(
    () => buildEndpoint({ meses, filtro, q, orden, unidadId }),
    [meses, filtro, q, orden, unidadId]
  );

  const oficinas: OficinaDespliegue[] = data?.oficinas || [];
  const resumen = data?.resumen;

  const openDetail = (ofi: OficinaDespliegue) => {
    setSelected(ofi);
    setEditVisita(ofi.estado_visita);
    setEditFecha(ofi.fecha_visita || "");
    setEditNotas(ofi.notas || "");
    setSaveError("");
  };

  const guardarVisita = async () => {
    if (!selected) return;
    setSaving(true);
    setSaveError("");
    try {
      await api.post(`/api/monitoreo/despliegue-oficinas/${selected.id}/`, {
        estado_visita: editVisita,
        fecha_visita: editFecha || null,
        notas: editNotas,
      });
      await mutate(swrKey);
      setSelected(null);
    } catch {
      setSaveError("No se pudo guardar. Verifica sesión de superusuario.");
    } finally {
      setSaving(false);
    }
  };

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-48 bg-muted rounded" />
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-2">
            {Array.from({ length: 12 }).map((_, i) => (
              <div key={i} className="h-20 bg-muted rounded-lg" />
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">
            Error al cargar despliegue de oficinas
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <Card>
        <CardHeader className="pb-3">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 className="h-4 w-4 text-indigo-500" />
              Despliegue por oficinas
            </CardTitle>
            <p className="text-[11px] text-muted-foreground">
              Inactividad = sin login ni correspondencia en {data?.meses_inactividad ?? meses} meses
            </p>
          </div>
          {resumen && (
            <div className="flex flex-wrap gap-2 pt-2">
              <Badge variant="success">{resumen.operativa} operativas</Badge>
              <Badge variant="danger">{resumen.sin_usuarios} sin usuarios</Badge>
              <Badge variant="secondary">{resumen.inactiva} inactivas</Badge>
              <Badge variant="warning">{resumen.pendiente_visita} visita pend.</Badge>
              <Badge variant="info">{resumen.capacitada} capacitadas</Badge>
              {resumen.sin_lider > 0 && (
                <Badge variant="outline">{resumen.sin_lider} sin líder</Badge>
              )}
              {data?.usuarios_sin_oficina_total > 0 && (
                <Badge variant="danger" className="gap-1">
                  <UserX className="h-3 w-3" />
                  {data.usuarios_sin_oficina_total} usuarios sin oficina
                </Badge>
              )}
            </div>
          )}
        </CardHeader>

        <CardContent className="space-y-4">
          <div className="flex flex-col md:flex-row gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <input
                type="search"
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Buscar oficina, unidad o proceso…"
                className="w-full rounded-md border bg-background pl-9 pr-3 py-2 text-sm"
              />
            </div>
            <select
              value={unidadId}
              onChange={(e) => setUnidadId(e.target.value)}
              className="rounded-md border bg-background px-3 py-2 text-sm min-w-[180px]"
            >
              <option value="">Todas las unidades</option>
              {(data?.unidades || []).map((u: { id: number; nombre: string }) => (
                <option key={u.id} value={String(u.id)}>
                  {u.nombre}
                </option>
              ))}
            </select>
            <select
              value={String(meses)}
              onChange={(e) => setMeses(Number(e.target.value))}
              className="rounded-md border bg-background px-3 py-2 text-sm"
              title="Meses sin actividad para estado inactiva"
            >
              {[2, 3, 4, 6, 12].map((m) => (
                <option key={m} value={m}>
                  {m} meses inactividad
                </option>
              ))}
            </select>
            <select
              value={orden}
              onChange={(e) => setOrden(e.target.value as DespliegueOrden)}
              className="rounded-md border bg-background px-3 py-2 text-sm min-w-[200px]"
            >
              {ORDENES.map((o) => (
                <option key={o.id} value={o.id}>
                  {o.label}
                </option>
              ))}
            </select>
          </div>

          <div className="flex flex-wrap gap-1.5">
            {FILTROS.map((f) => (
              <button
                key={f.id || "all"}
                type="button"
                onClick={() => setFiltro(f.id)}
                className={`rounded-full px-3 py-1 text-[11px] font-medium border transition-colors ${
                  filtro === f.id
                    ? "bg-primary text-primary-foreground border-primary"
                    : "bg-muted/50 text-muted-foreground border-border hover:bg-muted"
                }`}
              >
                {f.label}
              </button>
            ))}
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-2 max-h-[520px] overflow-y-auto pr-1">
            {oficinas.map((ofi) => (
              <button
                key={ofi.id}
                type="button"
                onClick={() => openDetail(ofi)}
                className={`text-left rounded-lg border p-3 transition-colors ${cardTone(
                  ofi.estado_operativo
                )}`}
              >
                <div className="flex items-start justify-between gap-2 mb-1">
                  <span className="text-xs font-semibold leading-tight line-clamp-2">
                    {ofi.nombre}
                  </span>
                  <Badge
                    variant={
                      ofi.estado_operativo === "operativa"
                        ? "success"
                        : ofi.estado_operativo === "sin_usuarios"
                          ? "danger"
                          : "secondary"
                    }
                    className="shrink-0 text-[9px] px-1.5"
                  >
                    {estadoOperativoLabel(ofi.estado_operativo)}
                  </Badge>
                </div>
                <p className="text-[10px] text-muted-foreground line-clamp-1 mb-2">
                  {ofi.unidad_nombre}
                </p>
                <div className="flex flex-wrap gap-1">
                  <span className="inline-flex items-center gap-0.5 text-[10px] text-muted-foreground">
                    <Users className="h-3 w-3" />
                    {ofi.usuarios_activos} activos
                  </span>
                  <Badge variant="outline" className="text-[9px] py-0">
                    {estadoVisitaLabel(ofi.estado_visita)}
                  </Badge>
                  {!ofi.tiene_lider && ofi.usuarios_activos > 0 && (
                    <AlertCircle className="h-3 w-3 text-amber-500" aria-label="Sin líder" />
                  )}
                </div>
              </button>
            ))}
          </div>

          {oficinas.length === 0 && (
            <p className="text-sm text-muted-foreground text-center py-6">
              No hay oficinas con los filtros actuales.
            </p>
          )}

          {data?.usuarios_sin_oficina?.length > 0 && (
            <div className="rounded-lg border border-dashed border-amber-500/40 bg-amber-500/5 p-3">
              <p className="text-xs font-semibold text-amber-600 dark:text-amber-400 mb-2 flex items-center gap-1">
                <UserX className="h-3.5 w-3.5" />
                Usuarios activos sin oficina asignada (muestra hasta 50)
              </p>
              <ul className="text-[11px] text-muted-foreground space-y-1 max-h-24 overflow-y-auto">
                {data.usuarios_sin_oficina.map(
                  (u: { nombre: string; username: string }) => (
                    <li key={u.username}>
                      {u.nombre} ({u.username})
                    </li>
                  )
                )}
              </ul>
            </div>
          )}
        </CardContent>
      </Card>

      <Dialog open={!!selected} onOpenChange={(open) => !open && setSelected(null)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          {selected && (
            <>
              <DialogHeader>
                <DialogTitle className="text-base pr-6">{selected.nombre}</DialogTitle>
                <p className="text-xs text-muted-foreground flex items-center gap-1">
                  <MapPin className="h-3 w-3" />
                  {selected.unidad_nombre}
                  {selected.proceso_nombre ? ` · ${selected.proceso_nombre}` : ""}
                </p>
              </DialogHeader>

              <div className="flex flex-wrap gap-2">
                <Badge
                  variant={
                    selected.estado_operativo === "operativa"
                      ? "success"
                      : selected.estado_operativo === "sin_usuarios"
                        ? "danger"
                        : "secondary"
                  }
                >
                  {estadoOperativoLabel(selected.estado_operativo)}
                </Badge>
                {selected.tiene_lider ? (
                  <Badge variant="success" className="gap-1">
                    <CheckCircle2 className="h-3 w-3" /> Con líder
                  </Badge>
                ) : (
                  <Badge variant="warning">Sin líder</Badge>
                )}
                {!selected.tiene_trd && (
                  <Badge variant="warning">TRD/código incompleto</Badge>
                )}
              </div>

              <dl className="grid grid-cols-2 gap-2 text-[11px]">
                <div>
                  <dt className="text-muted-foreground">Último login (activos)</dt>
                  <dd>{fmtRelativo(selected.ultimo_login_oficina)}</dd>
                </div>
                <div>
                  <dt className="text-muted-foreground">Última correspondencia</dt>
                  <dd>{fmtRelativo(selected.ultima_correspondencia)}</dd>
                </div>
                <div className="col-span-2">
                  <dt className="text-muted-foreground">Última actividad registrada</dt>
                  <dd>{fmtFecha(selected.ultima_actividad)}</dd>
                </div>
              </dl>

              <div>
                <h4 className="text-xs font-semibold mb-2">Usuarios</h4>
                <ul className="space-y-2 max-h-40 overflow-y-auto border rounded-md p-2">
                  {selected.usuarios.length === 0 ? (
                    <li className="text-xs text-muted-foreground">Sin perfiles asignados</li>
                  ) : (
                    selected.usuarios.map((u) => (
                      <li
                        key={u.id}
                        className={`text-[11px] flex justify-between gap-2 ${
                          !u.is_active ? "opacity-50" : ""
                        }`}
                      >
                        <span>
                          {u.nombre}
                          {u.es_lider && (
                            <span className="text-emerald-600 ml-1">(líder)</span>
                          )}
                          {!u.is_active && (
                            <span className="text-red-500 ml-1">(inactivo)</span>
                          )}
                        </span>
                        <span className="text-muted-foreground shrink-0">
                          {fmtRelativo(u.last_login)}
                        </span>
                      </li>
                    ))
                  )}
                </ul>
              </div>

              <div className="border-t pt-3 space-y-2">
                <h4 className="text-xs font-semibold">Seguimiento de visita (superusuario)</h4>
                <select
                  value={editVisita}
                  onChange={(e) => setEditVisita(e.target.value as EstadoVisita)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <option value="pendiente">Pendiente de visita</option>
                  <option value="visitada">Visitada</option>
                  <option value="capacitada">Capacitada</option>
                  <option value="no_aplica">No aplica</option>
                </select>
                <input
                  type="date"
                  value={editFecha}
                  onChange={(e) => setEditFecha(e.target.value)}
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                />
                <textarea
                  value={editNotas}
                  onChange={(e) => setEditNotas(e.target.value)}
                  rows={3}
                  placeholder="Notas de capacitación o visita…"
                  className="w-full rounded-md border bg-background px-3 py-2 text-sm"
                />
                {saveError && (
                  <p className="text-xs text-destructive">{saveError}</p>
                )}
                <button
                  type="button"
                  disabled={saving}
                  onClick={guardarVisita}
                  className="inline-flex items-center gap-2 rounded-md bg-primary text-primary-foreground px-4 py-2 text-sm font-medium disabled:opacity-50"
                >
                  <Save className="h-4 w-4" />
                  {saving ? "Guardando…" : "Guardar seguimiento"}
                </button>
              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
