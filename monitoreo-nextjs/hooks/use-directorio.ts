import useSWR from "swr";
import api from "@/lib/axios";

const BASE = "/api/chat";
const fetcher = (url: string) => api.get(url).then((r) => r.data);

/* ─── tipos ─────────────────────────────────────────────────── */

export type UsuarioDir = {
  id: number;
  username: string;
  nombre: string;
  cargo: string;
  email: string;
  is_superuser: boolean;
  last_login: string | null;
};

export type OficinaDir = {
  id: number;
  nombre: string;
  codigo: string;
  unidad: string;
  usuarios: UsuarioDir[];
};

export type DirectorioResponse = {
  oficinas: OficinaDir[];
  total_usuarios: number;
  total_oficinas: number;
};

export type ResumenTickets = {
  total: number;
  abiertas: number;
  cerradas: number;
  urgentes: number;
  no_leidos: number;
  nuevos_hoy: number;
  resueltos_hoy: number;
};

export type Notificacion = {
  tipo: "nueva_conversacion" | "mensaje_no_leido";
  texto: string;
  prioridad?: string;
  conversacion_id: number;
  asunto?: string;
  fecha: string;
};

export type NotificacionesResponse = {
  items: Notificacion[];
  total: number;
};

export type UsuarioDetalle = {
  id: number;
  username: string;
  nombre: string;
  email: string;
  is_active: boolean;
  is_superuser: boolean;
  last_login: string | null;
  date_joined: string;
  perfil: {
    oficina: string | null;
    cargo: string | null;
    telefono: string | null;
  } | null;
  conversaciones: {
    id: number;
    asunto: string;
    estado: string;
    prioridad: string;
    creado: string;
    actualizado: string;
  }[];
};

/* ─── hooks ─────────────────────────────────────────────────── */

export function useDirectorio(busqueda?: string) {
  const params = busqueda ? `?q=${encodeURIComponent(busqueda)}` : "";
  return useSWR<DirectorioResponse>(
    `${BASE}/directorio${params}`,
    fetcher,
    { refreshInterval: 60000 }
  );
}

export function useResumenTickets() {
  return useSWR<ResumenTickets>(
    `${BASE}/resumen-tickets`,
    fetcher,
    { refreshInterval: 15000 }
  );
}

export function useNotificacionesChat() {
  return useSWR<NotificacionesResponse>(
    `${BASE}/notificaciones`,
    fetcher,
    { refreshInterval: 10000 }
  );
}

export function useUsuarioDetalle(userId: number | null) {
  return useSWR<UsuarioDetalle>(
    userId ? `${BASE}/usuarios/${userId}` : null,
    fetcher
  );
}
