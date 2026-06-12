import useSWR from "swr";
import api from "@/lib/axios";
import { useRangoParams } from "./use-rango";

const fetcher = (url: string) => api.get(url).then((res) => res.data);

const BASE = "/api/monitoreo";

function useMonitoreoSWR(endpoint: string, realtimeMs: number) {
  const rangoParams = useRangoParams();
  const sep = rangoParams ? `?${rangoParams}` : "";
  const isRealtime = !rangoParams;
  return useSWR(`${BASE}/${endpoint}${sep}`, fetcher, {
    refreshInterval: isRealtime ? realtimeMs : 0,
  });
}

export function usePulso() { return useMonitoreoSWR("pulso", 15000); }
export function useSLA() { return useMonitoreoSWR("sla", 30000); }
export function useEnvio() { return useMonitoreoSWR("envio", 30000); }
export function useIMAP() { return useMonitoreoSWR("imap", 30000); }
export function useEmailSync() { return useMonitoreoSWR("email-sync", 30000); }
export function useDistribucion() { return useMonitoreoSWR("distribucion", 30000); }
export function useInternas() { return useMonitoreoSWR("internas", 30000); }
export function useUrgencias() { return useMonitoreoSWR("urgencias", 20000); }
export function useTendencias() { return useMonitoreoSWR("tendencias", 60000); }
export function useActividad() { return useMonitoreoSWR("actividad", 15000); }
export function useNotificaciones() { return useMonitoreoSWR("notificaciones", 30000); }

export type DespliegueFiltro =
  | ""
  | "operativa"
  | "sin_usuarios"
  | "inactiva"
  | "pendiente_visita"
  | "visitada"
  | "capacitada"
  | "sin_lider"
  | "sin_trd"
  | "prioridad";

export type DespliegueOrden =
  | "pendiente"
  | "nombre"
  | "usuarios_activos"
  | "ultima_actividad"
  | "unidad";

export function useDespliegueOficinas(params: {
  meses?: number;
  filtro?: DespliegueFiltro;
  q?: string;
  orden?: DespliegueOrden;
  unidadId?: string;
}) {
  const search = new URLSearchParams();
  if (params.meses) search.set("meses", String(params.meses));
  if (params.filtro) search.set("filtro", params.filtro);
  if (params.q) search.set("q", params.q);
  if (params.orden) search.set("orden", params.orden);
  if (params.unidadId) search.set("unidad_id", params.unidadId);
  const qs = search.toString();
  const endpoint = `despliegue-oficinas${qs ? `?${qs}` : ""}`;
  return useSWR(`${BASE}/${endpoint}`, fetcher, { refreshInterval: 60000 });
}
