"use client";

import { appPath } from "@/lib/app-path";
import { useState, useRef, useEffect, useMemo } from "react";
import {
  useConversaciones,
  useMensajes,
  useResumenChat,
  enviarMensaje,
  cambiarEstado,
  crearConversacion,
  type Conversacion,
} from "@/hooks/use-chat";
import {
  useResumenTickets,
  useNotificacionesChat,
  useDirectorio,
  useUsuarioDetalle,
  type OficinaDir,
  type UsuarioDir,
  type Notificacion,
} from "@/hooks/use-directorio";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

/* ═══════════════════════════════════════════════════════════════
   HELPERS & SHARED COMPONENTS
   ═══════════════════════════════════════════════════════════════ */

function timeAgo(iso: string) {
  return formatDistanceToNow(new Date(iso), { addSuffix: true, locale: es });
}

function Badge({
  children,
  variant = "default",
}: {
  children: React.ReactNode;
  variant?: "default" | "urgente" | "cerrada" | "count" | "info" | "success";
}) {
  const base =
    "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-semibold tracking-wide";
  const variants: Record<string, string> = {
    default: "bg-emerald-500/15 text-emerald-400 ring-1 ring-emerald-500/20",
    urgente: "bg-red-500/15 text-red-400 ring-1 ring-red-500/20",
    cerrada: "bg-zinc-600/20 text-zinc-500 ring-1 ring-zinc-600/20",
    count: "bg-amber-500/15 text-amber-400 ring-1 ring-amber-500/20",
    info: "bg-blue-500/15 text-blue-400 ring-1 ring-blue-500/20",
    success: "bg-teal-500/15 text-teal-400 ring-1 ring-teal-500/20",
  };
  return <span className={`${base} ${variants[variant]}`}>{children}</span>;
}

/* stat card */

function StatCard({
  label,
  value,
  icon,
  accent = "emerald",
}: {
  label: string;
  value: number | string;
  icon: React.ReactNode;
  accent?: "emerald" | "amber" | "red" | "blue" | "teal" | "zinc";
}) {
  const colors: Record<string, string> = {
    emerald: "from-emerald-500/10 to-emerald-500/5 text-emerald-400 ring-emerald-500/10",
    amber: "from-amber-500/10 to-amber-500/5 text-amber-400 ring-amber-500/10",
    red: "from-red-500/10 to-red-500/5 text-red-400 ring-red-500/10",
    blue: "from-blue-500/10 to-blue-500/5 text-blue-400 ring-blue-500/10",
    teal: "from-teal-500/10 to-teal-500/5 text-teal-400 ring-teal-500/10",
    zinc: "from-zinc-500/10 to-zinc-500/5 text-zinc-400 ring-zinc-500/10",
  };
  return (
    <div
      className={`relative overflow-hidden rounded-2xl bg-gradient-to-br ${colors[accent]} ring-1 p-4 flex items-center gap-3`}
    >
      <div className="flex-shrink-0 opacity-70">{icon}</div>
      <div className="min-w-0">
        <p className="text-2xl font-bold tracking-tight">{value}</p>
        <p className="text-[11px] text-zinc-400 font-medium truncate">{label}</p>
      </div>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   KPI BAR
   ═══════════════════════════════════════════════════════════════ */

function KPIBar() {
  const { data } = useResumenTickets();

  if (!data) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3 animate-pulse">
        {Array.from({ length: 7 }).map((_, i) => (
          <div key={i} className="h-[76px] rounded-2xl bg-zinc-800/40" />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
      <StatCard
        label="Total tickets"
        value={data.total}
        accent="zinc"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12h3.75M9 15h3.75M9 18h3.75m3 .75H18a2.25 2.25 0 002.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192a48.424 48.424 0 00-1.123-.08m-5.801 0c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m0 0H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V9.375c0-.621-.504-1.125-1.125-1.125H8.25zM6.75 12h.008v.008H6.75V12zm0 3h.008v.008H6.75V15zm0 3h.008v.008H6.75V18z" /></svg>}
      />
      <StatCard
        label="Abiertas"
        value={data.abiertas}
        accent="emerald"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M2.25 13.5h3.86a2.25 2.25 0 012.012 1.244l.256.512a2.25 2.25 0 002.013 1.244h3.218a2.25 2.25 0 002.013-1.244l.256-.512a2.25 2.25 0 012.013-1.244h3.859m-19.5.338V18a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18v-4.162c0-.224-.034-.447-.1-.661L19.24 5.338a2.25 2.25 0 00-2.15-1.588H6.911a2.25 2.25 0 00-2.15 1.588L2.35 13.177a2.25 2.25 0 00-.1.661z" /></svg>}
      />
      <StatCard
        label="Resueltas"
        value={data.cerradas}
        accent="teal"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
      />
      <StatCard
        label="Urgentes"
        value={data.urgentes}
        accent="red"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" /></svg>}
      />
      <StatCard
        label="No leídos"
        value={data.no_leidos}
        accent="amber"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M21.75 6.75v10.5a2.25 2.25 0 01-2.25 2.25h-15a2.25 2.25 0 01-2.25-2.25V6.75m19.5 0A2.25 2.25 0 0019.5 4.5h-15a2.25 2.25 0 00-2.25 2.25m19.5 0v.243a2.25 2.25 0 01-1.07 1.916l-7.5 4.615a2.25 2.25 0 01-2.36 0L3.32 8.91a2.25 2.25 0 01-1.07-1.916V6.75" /></svg>}
      />
      <StatCard
        label="Nuevos hoy"
        value={data.nuevos_hoy}
        accent="blue"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M12 6v6h4.5m4.5 0a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>}
      />
      <StatCard
        label="Resueltos hoy"
        value={data.resueltos_hoy}
        accent="teal"
        icon={<svg width="22" height="22" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}><path strokeLinecap="round" strokeLinejoin="round" d="M11.35 3.836c-.065.21-.1.433-.1.664 0 .414.336.75.75.75h4.5a.75.75 0 00.75-.75 2.25 2.25 0 00-.1-.664m-5.8 0A2.251 2.251 0 0113.5 2.25H15a2.25 2.25 0 012.15 1.586m-5.8 0c-.376.023-.75.05-1.124.08C9.095 4.01 8.25 4.973 8.25 6.108V8.25m8.9-4.414c.376.023.75.05 1.124.08 1.131.094 1.976 1.057 1.976 2.192V16.5A2.25 2.25 0 0118 18.75h-2.25m-7.5-10.5H4.875c-.621 0-1.125.504-1.125 1.125v11.25c0 .621.504 1.125 1.125 1.125h9.75c.621 0 1.125-.504 1.125-1.125V18.75m-7.5-10.5h6.375c.621 0 1.125.504 1.125 1.125v9.375m-8.25-3l1.5 1.5 3-3.75" /></svg>}
      />
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   NOTIFICATION PANEL (slide-over)
   ═══════════════════════════════════════════════════════════════ */

function NotificationPanel({
  open,
  onClose,
  onGoToConversation,
}: {
  open: boolean;
  onClose: () => void;
  onGoToConversation: (id: number) => void;
}) {
  const { data } = useNotificacionesChat();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-40 transition-opacity"
          onClick={onClose}
        />
      )}
      <div
        className={`fixed top-0 right-0 h-full w-[380px] max-w-[90vw] bg-zinc-900 border-l border-zinc-800/60 z-50 transform transition-transform duration-300 ${
          open ? "translate-x-0" : "translate-x-full"
        } flex flex-col`}
      >
        <div className="flex items-center justify-between px-5 py-4 border-b border-zinc-800/60">
          <div className="flex items-center gap-2">
            <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-amber-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
            </svg>
            <h2 className="text-sm font-semibold text-zinc-100">Notificaciones</h2>
            {data && data.total > 0 && (
              <span className="bg-amber-500 text-zinc-950 text-[10px] font-bold rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
                {data.total}
              </span>
            )}
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg hover:bg-zinc-800 transition-colors text-zinc-500 hover:text-zinc-300"
          >
            <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
        <div className="flex-1 overflow-y-auto">
          {!data || data.items.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-64 text-zinc-600">
              <svg width="40" height="40" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1} className="mb-3 opacity-40">
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
              <p className="text-sm">Sin notificaciones recientes</p>
            </div>
          ) : (
            data.items.map((n, idx) => (
              <button
                key={idx}
                onClick={() => {
                  onGoToConversation(n.conversacion_id);
                  onClose();
                }}
                className="w-full text-left px-5 py-3.5 border-b border-zinc-800/40 hover:bg-zinc-800/40 transition-colors group"
              >
                <div className="flex items-start gap-3">
                  <div className={`mt-0.5 flex-shrink-0 w-2 h-2 rounded-full ${
                    n.tipo === "nueva_conversacion" ? "bg-blue-400" : "bg-amber-400"
                  }`} />
                  <div className="min-w-0 flex-1">
                    <p className="text-[13px] text-zinc-200 leading-snug group-hover:text-zinc-100">
                      {n.texto}
                    </p>
                    {n.asunto && (
                      <p className="text-[11px] text-zinc-500 mt-0.5 truncate">{n.asunto}</p>
                    )}
                    <p className="text-[10px] text-zinc-600 mt-1">{timeAgo(n.fecha)}</p>
                  </div>
                  {n.prioridad === "urgente" && (
                    <span className="flex-shrink-0 mt-0.5 w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                  )}
                </div>
              </button>
            ))
          )}
        </div>
      </div>
    </>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CONVERSACION ITEM
   ═══════════════════════════════════════════════════════════════ */

function ConversacionItem({
  conv,
  activa,
  onClick,
}: {
  conv: Conversacion;
  activa: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={`w-full text-left p-3.5 border-b border-zinc-800/40 transition-all hover:bg-zinc-800/40 ${
        activa
          ? "bg-zinc-800/60 border-l-2 border-l-emerald-500"
          : "border-l-2 border-l-transparent"
      }`}
    >
      <div className="flex items-start justify-between gap-2 mb-1">
        <span className="text-[13px] font-medium text-zinc-100 truncate flex-1">
          {conv.asunto}
        </span>
        {conv.no_leidos > 0 && (
          <span className="flex-shrink-0 bg-emerald-500 text-zinc-950 text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center">
            {conv.no_leidos}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="text-xs text-zinc-400 truncate">{conv.usuario.nombre}</span>
        {conv.prioridad === "urgente" && <Badge variant="urgente">Urgente</Badge>}
        {conv.estado === "cerrada" && <Badge variant="cerrada">Cerrada</Badge>}
      </div>
      <p className="text-xs text-zinc-500 truncate">{conv.ultimo_texto}</p>
      <p className="text-[10px] text-zinc-600 mt-1">{timeAgo(conv.actualizado)}</p>
    </button>
  );
}

/* ═══════════════════════════════════════════════════════════════
   PANEL DE MENSAJES
   ═══════════════════════════════════════════════════════════════ */

function PanelMensajes({
  conversacionId,
  onEstadoCambiado,
}: {
  conversacionId: number;
  onEstadoCambiado: () => void;
}) {
  const { data, mutate } = useMensajes(conversacionId);
  const [texto, setTexto] = useState("");
  const [imagenes, setImagenes] = useState<File[]>([]);
  const [previews, setPreviews] = useState<string[]>([]);
  const [enviando, setEnviando] = useState(false);
  const [lightbox, setLightbox] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [data?.mensajes]);

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    const nuevas = Array.from(files)
      .filter((f) => f.type.startsWith("image/") && f.size <= 5 * 1024 * 1024)
      .slice(0, 5 - imagenes.length);
    const all = [...imagenes, ...nuevas];
    setImagenes(all);
    setPreviews(all.map((f) => URL.createObjectURL(f)));
  };

  const removeImage = (idx: number) => {
    const next = imagenes.filter((_, i) => i !== idx);
    setImagenes(next);
    setPreviews(next.map((f) => URL.createObjectURL(f)));
  };

  const handleSend = async () => {
    if ((!texto.trim() && imagenes.length === 0) || enviando) return;
    setEnviando(true);
    try {
      await enviarMensaje(conversacionId, texto.trim(), imagenes.length > 0 ? imagenes : undefined);
      setTexto("");
      setImagenes([]);
      setPreviews([]);
      mutate();
    } finally {
      setEnviando(false);
    }
  };

  const handleToggleEstado = async () => {
    if (!data) return;
    const nuevo = data.conversacion.estado === "abierta" ? "cerrada" : "abierta";
    await cambiarEstado(conversacionId, nuevo);
    mutate();
    onEstadoCambiado();
  };

  if (!data) {
    return (
      <div className="flex-1 flex items-center justify-center text-zinc-600">
        <div className="flex items-center gap-2">
          <div className="w-4 h-4 border-2 border-zinc-600 border-t-transparent rounded-full animate-spin" />
          Cargando…
        </div>
      </div>
    );
  }

  const { conversacion: conv, mensajes } = data;

  return (
    <div className="flex-1 flex flex-col min-h-0">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-zinc-800/60 bg-zinc-900/40">
        <div className="min-w-0 flex-1">
          <h2 className="text-sm font-semibold text-zinc-100 truncate">{conv.asunto}</h2>
          <p className="text-xs text-zinc-500">
            {conv.usuario.nombre}
            {conv.prioridad === "urgente" && (
              <span className="ml-2 text-red-400">● Urgente</span>
            )}
          </p>
        </div>
        <button
          onClick={handleToggleEstado}
          className={`text-xs px-3 py-1.5 rounded-lg font-medium transition-colors ${
            conv.estado === "abierta"
              ? "bg-zinc-700/60 text-zinc-300 hover:bg-zinc-700"
              : "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30"
          }`}
        >
          {conv.estado === "abierta" ? "Cerrar ticket" : "Reabrir"}
        </button>
      </div>

      {/* Mensajes */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-4 space-y-3">
        {mensajes.map((m) => (
          <div key={m.id} className={`flex ${m.es_admin ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[75%] rounded-2xl px-4 py-2.5 ${
                m.es_admin
                  ? "bg-emerald-600/20 text-emerald-100 rounded-br-md"
                  : "bg-zinc-800 text-zinc-200 rounded-bl-md"
              }`}
            >
              <p className="text-[11px] font-medium mb-0.5 opacity-60">{m.autor}</p>
              <p className="text-sm whitespace-pre-wrap break-words">{m.texto}</p>
              {m.adjuntos && m.adjuntos.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {m.adjuntos.map((a) => (
                    <img
                      key={a.id}
                      src={a.url}
                      alt={a.nombre}
                      onClick={() => setLightbox(a.url)}
                      className="rounded-lg max-h-40 max-w-[200px] object-cover cursor-pointer hover:opacity-80 transition-opacity border border-white/10"
                    />
                  ))}
                </div>
              )}
              <p className="text-[10px] opacity-40 mt-1 text-right">
                {new Date(m.creado).toLocaleTimeString("es-CO", { hour: "2-digit", minute: "2-digit" })}
              </p>
            </div>
          </div>
        ))}
        {mensajes.length === 0 && (
          <p className="text-center text-zinc-600 text-sm py-8">Sin mensajes aún.</p>
        )}
      </div>

      {/* Input */}
      {conv.estado === "abierta" ? (
        <div className="border-t border-zinc-800/60 p-3.5">
          {previews.length > 0 && (
            <div className="flex gap-2 mb-2 flex-wrap">
              {previews.map((src, i) => (
                <div key={i} className="relative group">
                  <img src={src} alt="" className="h-16 w-16 object-cover rounded-lg border border-zinc-700" />
                  <button
                    onClick={() => removeImage(i)}
                    className="absolute -top-1.5 -right-1.5 bg-red-500 text-white rounded-full w-4 h-4 text-[10px] flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity"
                  >×</button>
                </div>
              ))}
            </div>
          )}
          <div className="flex gap-2">
            <input type="file" ref={fileRef} accept="image/*" multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
            <button
              onClick={() => fileRef.current?.click()}
              className="bg-zinc-800/60 hover:bg-zinc-700 text-zinc-400 hover:text-zinc-200 px-3 py-2.5 rounded-xl transition-colors flex-shrink-0"
              title="Adjuntar imagen"
            >
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
              </svg>
            </button>
            <input
              value={texto}
              onChange={(e) => setTexto(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              onPaste={(e) => {
                const items = e.clipboardData?.items;
                if (!items) return;
                const imgs: File[] = [];
                for (let i = 0; i < items.length; i++) {
                  if (items[i].type.startsWith("image/")) {
                    const f = items[i].getAsFile();
                    if (f) imgs.push(f);
                  }
                }
                if (imgs.length > 0) {
                  e.preventDefault();
                  const all = [...imagenes, ...imgs].slice(0, 5);
                  setImagenes(all);
                  setPreviews(all.map((f) => URL.createObjectURL(f)));
                }
              }}
              placeholder="Escribe tu respuesta… (Ctrl+V para capturas)"
              className="flex-1 bg-zinc-800/60 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-emerald-500/40"
            />
            <button
              onClick={handleSend}
              disabled={(!texto.trim() && imagenes.length === 0) || enviando}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 disabled:hover:bg-emerald-600 text-white text-sm font-medium px-5 py-2.5 rounded-xl transition-colors"
            >
              {enviando ? (
                <div className="w-4 h-4 border-2 border-white/50 border-t-white rounded-full animate-spin" />
              ) : "Enviar"}
            </button>
          </div>
        </div>
      ) : (
        <div className="border-t border-zinc-800/60 p-3.5 text-center text-xs text-zinc-600">
          Conversación cerrada — puedes reabrir arriba.
        </div>
      )}

      {lightbox && (
        <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center cursor-pointer" onClick={() => setLightbox(null)}>
          <img src={lightbox} alt="Vista ampliada" className="max-h-[90vh] max-w-[90vw] object-contain rounded-lg shadow-2xl" onClick={(e) => e.stopPropagation()} />
          <button onClick={() => setLightbox(null)} className="absolute top-4 right-4 text-white/70 hover:text-white text-2xl font-bold">×</button>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   CONVERSACIONES TAB
   ═══════════════════════════════════════════════════════════════ */

function ConversacionesTab({ activa, setActiva }: { activa: number | null; setActiva: (id: number | null) => void }) {
  const [filtroEstado, setFiltroEstado] = useState<string>("abierta");
  const { data: conversaciones, mutate: mutateConvs } = useConversaciones(filtroEstado);

  return (
    <div className="flex flex-1 min-h-0">
      <aside className="w-80 border-r border-zinc-800/60 flex flex-col min-h-0 bg-zinc-900/20">
        <div className="flex border-b border-zinc-800/60">
          {(["abierta", "cerrada"] as const).map((est) => (
            <button
              key={est}
              onClick={() => { setFiltroEstado(est); setActiva(null); }}
              className={`flex-1 py-2.5 text-xs font-medium transition-colors ${
                filtroEstado === est
                  ? "text-emerald-400 border-b-2 border-emerald-500"
                  : "text-zinc-500 hover:text-zinc-300"
              }`}
            >
              {est === "abierta" ? "Abiertas" : "Cerradas"}
            </button>
          ))}
        </div>
        <div className="flex-1 overflow-y-auto">
          {conversaciones?.map((c) => (
            <ConversacionItem key={c.id} conv={c} activa={activa === c.id} onClick={() => setActiva(c.id)} />
          ))}
          {conversaciones?.length === 0 && (
            <p className="text-center text-zinc-600 text-sm py-12">Sin conversaciones {filtroEstado}s.</p>
          )}
        </div>
      </aside>

      {activa ? (
        <PanelMensajes key={activa} conversacionId={activa} onEstadoCambiado={() => mutateConvs()} />
      ) : (
        <div className="flex-1 flex items-center justify-center text-zinc-700">
          <div className="text-center">
            <svg className="mx-auto mb-3 opacity-30" width="48" height="48" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <p className="text-sm">Selecciona una conversación</p>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   USER DETAIL MODAL
   ═══════════════════════════════════════════════════════════════ */

function UserDetailModal({ userId, onClose, onOpenChat }: { userId: number; onClose: () => void; onOpenChat: (convId: number) => void }) {
  const { data } = useUsuarioDetalle(userId);

  if (!data) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={onClose}>
        <div className="bg-zinc-900 rounded-2xl p-8 w-[480px] max-w-[90vw]" onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-center h-40">
            <div className="w-6 h-6 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={onClose}>
      <div className="bg-zinc-900 rounded-2xl w-[520px] max-w-[90vw] max-h-[85vh] overflow-hidden ring-1 ring-zinc-800" onClick={(e) => e.stopPropagation()}>
        <div className="px-6 py-5 border-b border-zinc-800/60 bg-gradient-to-r from-zinc-900 to-zinc-800/50">
          <div className="flex items-start justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full bg-gradient-to-br from-emerald-500/30 to-blue-500/30 flex items-center justify-center text-lg font-bold text-zinc-100 ring-2 ring-zinc-700/50">
                {data.nombre.charAt(0).toUpperCase()}
              </div>
              <div>
                <h3 className="text-base font-semibold text-zinc-100">{data.nombre}</h3>
                <p className="text-xs text-zinc-500">@{data.username}</p>
              </div>
            </div>
            <button onClick={onClose} className="p-1 rounded-lg hover:bg-zinc-800 transition-colors text-zinc-500 hover:text-zinc-300">
              <svg width="18" height="18" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
        <div className="px-6 py-5 space-y-5 overflow-y-auto max-h-[calc(85vh-160px)]">
          <div className="grid grid-cols-2 gap-4">
            <InfoField label="Oficina" value={data.perfil?.oficina || "Sin asignar"} />
            <InfoField label="Cargo" value={data.perfil?.cargo || "—"} />
            <InfoField label="Email" value={data.email || "—"} />
            <InfoField label="Teléfono" value={data.perfil?.telefono || "—"} />
            <InfoField label="Último acceso" value={data.last_login ? timeAgo(data.last_login) : "Nunca"} />
            <InfoField label="Registro" value={new Date(data.date_joined).toLocaleDateString("es-CO")} />
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${data.is_active ? "bg-emerald-400" : "bg-red-400"}`} />
            <span className="text-xs text-zinc-400">{data.is_active ? "Activo" : "Inactivo"}</span>
            {data.is_superuser && <Badge variant="info">Superusuario</Badge>}
          </div>
          {data.conversaciones.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-3">
                Historial de tickets ({data.conversaciones.length})
              </h4>
              <div className="space-y-2">
                {data.conversaciones.map((c) => (
                  <button
                    key={c.id}
                    onClick={() => { onOpenChat(c.id); onClose(); }}
                    className="w-full text-left p-3 rounded-xl bg-zinc-800/40 hover:bg-zinc-800/70 transition-colors ring-1 ring-zinc-800/60"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-[13px] text-zinc-200 truncate flex-1">{c.asunto}</span>
                      <Badge variant={c.estado === "abierta" ? "default" : "cerrada"}>{c.estado}</Badge>
                    </div>
                    <p className="text-[10px] text-zinc-600 mt-1">{timeAgo(c.actualizado)}</p>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <div className="px-6 py-4 border-t border-zinc-800/60 bg-zinc-900/50">
          <button onClick={onClose} className="w-full py-2.5 rounded-xl bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors text-sm font-medium">
            Cerrar
          </button>
        </div>
      </div>
    </div>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <span className="text-[10px] uppercase tracking-wider text-zinc-600 font-medium">{label}</span>
      <p className="text-[13px] text-zinc-300 mt-0.5 truncate">{value}</p>
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   DIRECTORIO TAB (Users by Office)
   ═══════════════════════════════════════════════════════════════ */

function DirectorioTab({ onStartChat }: { onStartChat: (userId: number, nombre: string) => void }) {
  const [busqueda, setBusqueda] = useState("");
  const [debouncedQ, setDebouncedQ] = useState("");
  const { data } = useDirectorio(debouncedQ || undefined);
  const [expandidas, setExpandidas] = useState<Set<number>>(new Set());
  const [detailUser, setDetailUser] = useState<number | null>(null);
  const [creatingFor, setCreatingFor] = useState<{ id: number; nombre: string } | null>(null);
  const [nuevoAsunto, setNuevoAsunto] = useState("");
  const [nuevoMensaje, setNuevoMensaje] = useState("");
  const [creando, setCreando] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQ(busqueda), 400);
    return () => clearTimeout(t);
  }, [busqueda]);

  const toggleOficina = (id: number) => {
    setExpandidas((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleCrearConversacion = async () => {
    if (!nuevoAsunto.trim() || !nuevoMensaje.trim() || creando) return;
    setCreando(true);
    try {
      await crearConversacion({ asunto: nuevoAsunto.trim(), mensaje: nuevoMensaje.trim() });
      setCreatingFor(null);
      setNuevoAsunto("");
      setNuevoMensaje("");
      onStartChat(0, "");
    } finally {
      setCreando(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col min-h-0">
      <div className="px-5 py-4 border-b border-zinc-800/60">
        <div className="relative">
          <svg className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500" width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
          </svg>
          <input
            value={busqueda}
            onChange={(e) => setBusqueda(e.target.value)}
            placeholder="Buscar usuario, oficina o cargo…"
            className="w-full bg-zinc-800/60 rounded-xl pl-10 pr-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-blue-500/40"
          />
        </div>
        {data && (
          <p className="text-[11px] text-zinc-600 mt-2">{data.total_usuarios} usuarios en {data.total_oficinas} oficinas</p>
        )}
      </div>

      <div className="flex-1 overflow-y-auto">
        {!data ? (
          <div className="flex items-center justify-center h-40">
            <div className="w-5 h-5 border-2 border-zinc-600 border-t-zinc-300 rounded-full animate-spin" />
          </div>
        ) : data.oficinas.length === 0 ? (
          <p className="text-center text-zinc-600 text-sm py-12">No se encontraron resultados.</p>
        ) : (
          data.oficinas.map((ofi) => (
            <div key={ofi.id} className="border-b border-zinc-800/40">
              <button
                onClick={() => toggleOficina(ofi.id)}
                className="w-full flex items-center justify-between px-5 py-3 hover:bg-zinc-800/30 transition-colors"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500/20 to-emerald-500/10 flex items-center justify-center ring-1 ring-zinc-700/50">
                    <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5} className="text-blue-400">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M3.75 21h16.5M4.5 3h15M5.25 3v18m13.5-18v18M9 6.75h1.5m-1.5 3h1.5m-1.5 3h1.5m3-6H15m-1.5 3H15m-1.5 3H15M9 21v-3.375c0-.621.504-1.125 1.125-1.125h3.75c.621 0 1.125.504 1.125 1.125V21" />
                    </svg>
                  </div>
                  <div className="text-left">
                    <p className="text-[13px] font-medium text-zinc-200">{ofi.nombre}</p>
                    {ofi.unidad && <p className="text-[10px] text-zinc-500">{ofi.unidad}</p>}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[11px] text-zinc-500 bg-zinc-800/60 px-2 py-0.5 rounded-full">{ofi.usuarios.length}</span>
                  <svg width="14" height="14" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
                    className={`text-zinc-500 transition-transform ${expandidas.has(ofi.id) ? "rotate-180" : ""}`}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </button>

              {expandidas.has(ofi.id) && (
                <div className="pb-2">
                  {ofi.usuarios.map((u) => (
                    <div key={u.id} className="flex items-center justify-between px-5 pl-14 py-2.5 hover:bg-zinc-800/20 transition-colors group">
                      <div className="flex items-center gap-3 min-w-0 flex-1">
                        <div className="w-8 h-8 rounded-full bg-zinc-800 flex items-center justify-center text-xs font-semibold text-zinc-400 flex-shrink-0 ring-1 ring-zinc-700/50">
                          {u.nombre.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <p className="text-[13px] text-zinc-200 truncate">{u.nombre}</p>
                          <p className="text-[10px] text-zinc-500 truncate">{u.cargo || u.email || u.username}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                        <button
                          onClick={() => setCreatingFor({ id: u.id, nombre: u.nombre })}
                          className="p-1.5 rounded-lg hover:bg-emerald-500/20 text-zinc-500 hover:text-emerald-400 transition-colors"
                          title="Abrir chat"
                        >
                          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                          </svg>
                        </button>
                        <button
                          onClick={() => setDetailUser(u.id)}
                          className="p-1.5 rounded-lg hover:bg-blue-500/20 text-zinc-500 hover:text-blue-400 transition-colors"
                          title="Ver detalles"
                        >
                          <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z" />
                          </svg>
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      {detailUser && (
        <UserDetailModal userId={detailUser} onClose={() => setDetailUser(null)} onOpenChat={() => {}} />
      )}

      {creatingFor && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center" onClick={() => setCreatingFor(null)}>
          <div className="bg-zinc-900 rounded-2xl w-[460px] max-w-[90vw] ring-1 ring-zinc-800 overflow-hidden" onClick={(e) => e.stopPropagation()}>
            <div className="px-6 py-4 border-b border-zinc-800/60">
              <h3 className="text-sm font-semibold text-zinc-100">Nuevo ticket para {creatingFor.nombre}</h3>
              <p className="text-[11px] text-zinc-500 mt-0.5">Se abrirá una conversación de soporte</p>
            </div>
            <div className="px-6 py-5 space-y-4">
              <div>
                <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-medium">Asunto</label>
                <input
                  value={nuevoAsunto}
                  onChange={(e) => setNuevoAsunto(e.target.value)}
                  placeholder="Describe el ticket…"
                  className="mt-1 w-full bg-zinc-800/60 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-emerald-500/40"
                />
              </div>
              <div>
                <label className="text-[11px] uppercase tracking-wider text-zinc-500 font-medium">Mensaje inicial</label>
                <textarea
                  value={nuevoMensaje}
                  onChange={(e) => setNuevoMensaje(e.target.value)}
                  placeholder="Escribe el primer mensaje…"
                  rows={3}
                  className="mt-1 w-full bg-zinc-800/60 rounded-xl px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-600 outline-none focus:ring-1 focus:ring-emerald-500/40 resize-none"
                />
              </div>
            </div>
            <div className="px-6 py-4 border-t border-zinc-800/60 flex gap-3 justify-end">
              <button onClick={() => setCreatingFor(null)} className="px-4 py-2 rounded-xl bg-zinc-800/60 text-zinc-400 hover:bg-zinc-800 hover:text-zinc-200 transition-colors text-sm">
                Cancelar
              </button>
              <button
                onClick={handleCrearConversacion}
                disabled={!nuevoAsunto.trim() || !nuevoMensaje.trim() || creando}
                className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white text-sm font-medium transition-colors"
              >
                {creando ? "Creando…" : "Crear ticket"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/* ═══════════════════════════════════════════════════════════════
   MAIN PAGE
   ═══════════════════════════════════════════════════════════════ */

export default function ChatPage() {
  const [tab, setTab] = useState<"conversaciones" | "directorio">("conversaciones");
  const [activa, setActiva] = useState<number | null>(null);
  const [notifOpen, setNotifOpen] = useState(false);
  const { data: resumen } = useResumenChat();
  const { data: notifData } = useNotificacionesChat();

  const handleGoToConversation = (id: number) => {
    setTab("conversaciones");
    setActiva(id);
  };

  return (
    <div className="flex flex-col h-screen bg-zinc-950 text-zinc-100">
      {/* HEADER */}
      <header className="border-b border-zinc-800/60 bg-zinc-900/50">
        <div className="flex items-center justify-between px-5 py-3">
          <div className="flex items-center gap-3">
            <a href={appPath("/")} className="text-zinc-500 hover:text-zinc-300 transition-colors">
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
              </svg>
            </a>
            <div>
              <h1 className="text-base font-semibold tracking-tight">Centro de Soporte</h1>
              <p className="text-[10px] text-zinc-500">Tickets y directorio de usuarios</p>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {resumen && resumen.no_leidos > 0 && (
              <Badge variant="count">{resumen.no_leidos} sin leer</Badge>
            )}
            <button
              onClick={() => setNotifOpen(true)}
              className="relative p-2 rounded-xl hover:bg-zinc-800/60 transition-colors text-zinc-400 hover:text-zinc-200"
            >
              <svg width="20" height="20" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M14.857 17.082a23.848 23.848 0 005.454-1.31A8.967 8.967 0 0118 9.75v-.7V9A6 6 0 006 9v.75a8.967 8.967 0 01-2.312 6.022c1.733.64 3.56 1.085 5.455 1.31m5.714 0a24.255 24.255 0 01-5.714 0m5.714 0a3 3 0 11-5.714 0" />
              </svg>
              {notifData && notifData.total > 0 && (
                <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[9px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
                  {notifData.total > 9 ? "9+" : notifData.total}
                </span>
              )}
            </button>
          </div>
        </div>

        {/* KPIs */}
        <div className="px-5 pb-4">
          <KPIBar />
        </div>

        {/* Tabs */}
        <div className="flex px-5 gap-1">
          <button
            onClick={() => setTab("conversaciones")}
            className={`px-4 py-2 text-sm font-medium rounded-t-xl transition-colors ${
              tab === "conversaciones"
                ? "bg-zinc-900/80 text-emerald-400 border-b-2 border-emerald-500"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/30"
            }`}
          >
            <span className="flex items-center gap-2">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 8.511c.884.284 1.5 1.128 1.5 2.097v4.286c0 1.136-.847 2.1-1.98 2.193-.34.027-.68.052-1.02.072v3.091l-3-3c-1.354 0-2.694-.055-4.02-.163a2.115 2.115 0 01-.825-.242m9.345-8.334a2.126 2.126 0 00-.476-.095 48.64 48.64 0 00-8.048 0c-1.131.094-1.976 1.057-1.976 2.192v4.286c0 1.136.845 2.1 1.976 2.193 1.31.11 2.637.165 3.976.165l3 3V16.5a48.3 48.3 0 001.024-.072c1.133-.093 1.98-1.057 1.98-2.192V10.608c0-1.136-.847-2.098-1.98-2.192a48.394 48.394 0 00-1.524-.095" />
              </svg>
              Conversaciones
              {resumen && resumen.abiertas > 0 && (
                <span className="bg-zinc-800 text-zinc-400 text-[10px] font-bold rounded-full px-1.5 py-0.5 min-w-[18px] text-center">
                  {resumen.abiertas}
                </span>
              )}
            </span>
          </button>
          <button
            onClick={() => setTab("directorio")}
            className={`px-4 py-2 text-sm font-medium rounded-t-xl transition-colors ${
              tab === "directorio"
                ? "bg-zinc-900/80 text-blue-400 border-b-2 border-blue-500"
                : "text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800/30"
            }`}
          >
            <span className="flex items-center gap-2">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M18 18.72a9.094 9.094 0 003.741-.479 3 3 0 00-4.682-2.72m.94 3.198l.001.031c0 .225-.012.447-.037.666A11.944 11.944 0 0112 21c-2.17 0-4.207-.576-5.963-1.584A6.062 6.062 0 016 18.719m12 0a5.971 5.971 0 00-.941-3.197m0 0A5.995 5.995 0 0012 12.75a5.995 5.995 0 00-5.058 2.772m0 0a3 3 0 00-4.681 2.72 8.986 8.986 0 003.74.477m.94-3.197a5.971 5.971 0 00-.94 3.197M15 6.75a3 3 0 11-6 0 3 3 0 016 0zm6 3a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0zm-13.5 0a2.25 2.25 0 11-4.5 0 2.25 2.25 0 014.5 0z" />
              </svg>
              Directorio
            </span>
          </button>
        </div>
      </header>

      {/* CONTENT */}
      {tab === "conversaciones" ? (
        <ConversacionesTab activa={activa} setActiva={setActiva} />
      ) : (
        <DirectorioTab onStartChat={(userId, nombre) => {
          if (userId === 0) { setTab("conversaciones"); setActiva(null); }
        }} />
      )}

      {/* NOTIFICATION PANEL */}
      <NotificationPanel open={notifOpen} onClose={() => setNotifOpen(false)} onGoToConversation={handleGoToConversation} />
    </div>
  );
}
