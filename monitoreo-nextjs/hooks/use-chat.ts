import useSWR from "swr";
import api from "@/lib/axios";

const BASE = "/api/chat";

const fetcher = (url: string) => api.get(url).then((r) => r.data);

export type Conversacion = {
  id: number;
  asunto: string;
  estado: "abierta" | "cerrada";
  prioridad: "normal" | "urgente";
  usuario: { id: number; nombre: string };
  total_mensajes: number;
  no_leidos: number;
  ultimo_texto: string;
  ultimo_autor_es_admin: boolean;
  creado: string;
  actualizado: string;
};

export type Adjunto = {
  id: number;
  url: string;
  nombre: string;
};

export type Mensaje = {
  id: number;
  texto: string;
  es_admin: boolean;
  autor: string;
  leido: boolean;
  creado: string;
  adjuntos: Adjunto[];
};

export type MensajesResponse = {
  conversacion: {
    id: number;
    asunto: string;
    estado: string;
    prioridad: string;
    usuario: { id: number; nombre: string };
  };
  mensajes: Mensaje[];
};

export type Resumen = {
  abiertas: number;
  no_leidos: number;
};

export function useConversaciones(estado?: string) {
  const params = estado ? `?estado=${estado}` : "";
  return useSWR<Conversacion[]>(
    `${BASE}/conversaciones${params}`,
    fetcher,
    { refreshInterval: 5000 }
  );
}

export function useMensajes(conversacionId: number | null) {
  return useSWR<MensajesResponse>(
    conversacionId ? `${BASE}/conversaciones/${conversacionId}/mensajes` : null,
    fetcher,
    { refreshInterval: 3000 }
  );
}

export function useResumenChat() {
  return useSWR<Resumen>(`${BASE}/resumen`, fetcher, {
    refreshInterval: 10000,
  });
}

export async function crearConversacion(data: {
  asunto: string;
  mensaje: string;
  prioridad?: string;
}) {
  const res = await api.post(`${BASE}/conversaciones/crear`, data);
  return res.data;
}

export async function enviarMensaje(
  conversacionId: number,
  texto: string,
  imagenes?: File[]
) {
  if (imagenes && imagenes.length > 0) {
    const fd = new FormData();
    fd.append("texto", texto);
    imagenes.forEach((f) => fd.append("imagenes", f));
    const res = await api.post(
      `${BASE}/conversaciones/${conversacionId}/mensajes/enviar`,
      fd,
      { headers: { "Content-Type": "multipart/form-data" } }
    );
    return res.data;
  }
  const res = await api.post(
    `${BASE}/conversaciones/${conversacionId}/mensajes/enviar`,
    { texto }
  );
  return res.data;
}

export async function cambiarEstado(
  conversacionId: number,
  estado: "abierta" | "cerrada"
) {
  const res = await api.post(
    `${BASE}/conversaciones/${conversacionId}/estado`,
    { estado }
  );
  return res.data;
}
