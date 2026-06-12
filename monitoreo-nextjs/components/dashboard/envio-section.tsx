"use client";

import { useState } from "react";
import { useEnvio } from "@/hooks/use-monitoreo";
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
  Mail,
  Send,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Clock,
  Maximize2,
  ShieldAlert,
  CircleCheck,
  Ban,
  ExternalLink,
  Fingerprint,
} from "lucide-react";

function VerificationBadge({ item }: { item: any }) {
  const verification = item?.verificacion_envio;

  if (!verification) {
    return null;
  }

  if (verification.estado_final === "no_entregado") {
    return (
      <div className="rounded-md bg-red-500/10 border border-red-500/20 px-2.5 py-2 text-[11px] text-red-300 flex items-start gap-2">
        <Ban className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        <div>
          <p className="font-medium text-red-200">No entregado</p>
          <p>{verification.resumen}</p>
        </div>
      </div>
    );
  }

  if (verification.estado_final === "error_envio") {
    return (
      <div className="rounded-md bg-amber-500/10 border border-amber-500/20 px-2.5 py-2 text-[11px] text-amber-200 flex items-start gap-2">
        <ShieldAlert className="h-3.5 w-3.5 mt-0.5 shrink-0" />
        <div>
          <p className="font-medium text-amber-100">Envío no confirmado</p>
          <p>{verification.resumen}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-2 text-[11px] text-emerald-200 flex items-start gap-2">
      <CircleCheck className="h-3.5 w-3.5 mt-0.5 shrink-0" />
      <div>
        <p className="font-medium text-emerald-100">Verificación disponible</p>
        <p>{verification.resumen}</p>
      </div>
    </div>
  );
}

export default function EnvioSection() {
  const { data, error, isLoading } = useEnvio();
  const [modalOpen, setModalOpen] = useState(false);

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
          <p className="text-destructive text-sm">Error al cargar pipeline de envío</p>
        </CardContent>
      </Card>
    );
  }

  const d = data;
  const rebotes = d?.rebotes_recientes ?? [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Send className="h-4 w-4 text-blue-500" />
          Pipeline de Envío
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Pipeline stages */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Clock className="h-4 w-4 mx-auto mb-1 text-amber-500" />
            <p className="text-lg font-bold">{d?.pendientes_envio ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Pendientes
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Mail className="h-4 w-4 mx-auto mb-1 text-blue-500" />
            <p className="text-lg font-bold">{d?.en_cola ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              En cola
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <CheckCircle2 className="h-4 w-4 mx-auto mb-1 text-emerald-500" />
            <p className="text-lg font-bold">{d?.enviados_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Enviados hoy
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <XCircle className="h-4 w-4 mx-auto mb-1 text-red-500" />
            <p className="text-lg font-bold">{d?.errores_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Errores
            </p>
          </div>
        </div>

        {/* Bounces preview + modal */}
        {rebotes.length > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <h4 className="text-xs font-medium text-muted-foreground uppercase flex items-center gap-1">
                <AlertTriangle className="h-3 w-3 text-amber-500" />
                Rebotes recientes
              </h4>
              <Dialog open={modalOpen} onOpenChange={setModalOpen}>
                <DialogTrigger asChild>
                  <button className="flex items-center gap-1 text-[10px] text-muted-foreground hover:text-foreground transition-colors">
                    <Maximize2 className="h-3 w-3" />
                    Ver detalle
                  </button>
                </DialogTrigger>
                <DialogContent className="max-w-2xl max-h-[80vh] overflow-hidden flex flex-col">
                  <DialogHeader>
                    <DialogTitle className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-amber-500" />
                      Rebotes y fallos de envío ({rebotes.length})
                    </DialogTitle>
                    <DialogDescription>
                      Detalle de los últimos errores de entrega de correspondencia.
                    </DialogDescription>
                  </DialogHeader>
                  <div className="overflow-y-auto flex-1 -mx-6 px-6">
                    <div className="space-y-3">
                      {rebotes.map((r: any, i: number) => (
                        <div
                          key={i}
                          className="rounded-lg border p-3 space-y-2"
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="min-w-0 flex-1">
                              <p className="text-sm font-medium truncate">
                                {r.nombre || r.email}
                              </p>
                              {r.nombre && (
                                <p className="text-xs text-muted-foreground truncate">
                                  {r.email}
                                </p>
                              )}
                            </div>
                            <Badge variant="danger" className="text-[10px] shrink-0">
                              {r.tipo}
                            </Badge>
                          </div>
                          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground">
                            {r.radicado && (
                              <div>
                                <span className="font-medium text-foreground">Radicado:</span>{" "}
                                {r.salida_id ? (
                                  <a
                                    href={`/registros/correspondencia/respuesta/${r.salida_id}/detalle/`}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-blue-400 hover:text-blue-300 underline underline-offset-2 inline-flex items-center gap-1"
                                  >
                                    {r.radicado}
                                    <ExternalLink className="h-3 w-3" />
                                  </a>
                                ) : (
                                  r.radicado
                                )}
                              </div>
                            )}
                            {r.fecha && (
                              <div>
                                <span className="font-medium text-foreground">Fecha:</span>{" "}
                                {new Date(r.fecha).toLocaleString("es-CO", {
                                  day: "2-digit",
                                  month: "short",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </div>
                            )}
                            {r.fecha_envio && (
                              <div>
                                <span className="font-medium text-foreground">Intento de envío:</span>{" "}
                                {new Date(r.fecha_envio).toLocaleString("es-CO", {
                                  day: "2-digit",
                                  month: "short",
                                  hour: "2-digit",
                                  minute: "2-digit",
                                })}
                              </div>
                            )}
                            <div>
                              <span className="font-medium text-foreground">Verificación SMTP:</span>{" "}
                              {r.tiene_message_id ? "Sí quedó registro de envío" : "No quedó registro de envío"}
                            </div>
                            {r.smtp_code && (
                              <div>
                                <span className="font-medium text-foreground">SMTP:</span>{" "}
                                {r.smtp_code}
                              </div>
                            )}
                            {r.dsn_status && (
                              <div>
                                <span className="font-medium text-foreground">DSN:</span>{" "}
                                {r.dsn_status}
                              </div>
                            )}
                          </div>
                          {r.message_id && (
                            <div className="flex items-start gap-1.5 text-[10px] text-muted-foreground bg-muted/30 rounded px-2 py-1.5 font-mono break-all">
                              <Fingerprint className="h-3 w-3 mt-0.5 shrink-0 text-muted-foreground/60" />
                              <span>
                                <span className="font-sans font-medium text-foreground/70">Message-ID:</span>{" "}
                                {r.message_id}
                              </span>
                            </div>
                          )}
                          <div className="rounded-md bg-muted/50 px-2.5 py-2 text-[11px] text-foreground/90">
                            <span className="font-medium">Motivo resumido:</span>{" "}
                            {r.motivo_resumen}
                          </div>
                          <VerificationBadge item={r} />
                          {r.error && (
                            <p className="text-[11px] bg-red-500/10 text-red-400 rounded px-2 py-1 font-mono break-all">
                              {r.error}
                            </p>
                          )}
                          {!r.error && !r.smtp_code && !r.dsn_status && (
                            <p className="text-[11px] text-muted-foreground">
                              No hay diagnóstico DSN técnico persistido para este rebote.
                            </p>
                          )}
                        </div>
                      ))}
                    </div>
                  </div>
                </DialogContent>
              </Dialog>
            </div>
            <div className="space-y-1 max-h-[120px] overflow-y-auto">
              {rebotes.map((r: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs py-1 px-2 rounded bg-muted/30"
                >
                  <span className="truncate max-w-[200px]">{r.email}</span>
                  <Badge variant="danger" className="text-[10px]">
                    {r.tipo}
                  </Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
