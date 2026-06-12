"use client";

import { useUrgencias } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertTriangle, Clock, User } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

interface Urgencia {
  radicado: string;
  asunto: string;
  oficina: string;
  usuario: string;
  fecha: string;
  dias_sin_respuesta: number;
}

export default function UrgenciasSection() {
  const { data, error, isLoading } = useUrgencias();

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-12 bg-muted rounded" />
          ))}
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">
            Error al cargar urgencias
          </p>
        </CardContent>
      </Card>
    );
  }

  const urgencias: Urgencia[] = data?.urgencias || [];
  const total = data?.total ?? 0;

  return (
    <Card className={total > 0 ? "border-red-500/30" : ""}>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <AlertTriangle
              className={`h-4 w-4 ${
                total > 0 ? "text-red-500" : "text-muted-foreground"
              }`}
            />
            Urgencias Activas
          </CardTitle>
          <Badge variant={total > 0 ? "danger" : "success"}>
            {total} {total === 1 ? "urgencia" : "urgencias"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        {urgencias.length === 0 ? (
          <div className="text-center py-6">
            <AlertTriangle className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Sin urgencias activas
            </p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[250px] overflow-y-auto">
            {urgencias.map((u, i) => (
              <div
                key={i}
                className="rounded-lg border border-red-500/20 bg-red-500/5 p-3 space-y-1"
              >
                <div className="flex items-center justify-between">
                  <Badge variant="danger" className="text-[10px]">
                    {u.radicado}
                  </Badge>
                  <span className="text-[10px] text-muted-foreground flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {u.dias_sin_respuesta}d sin respuesta
                  </span>
                </div>
                <p className="text-sm truncate">{u.asunto}</p>
                <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                  <span className="flex items-center gap-1">
                    <User className="h-3 w-3" />
                    {u.usuario}
                  </span>
                  <span>•</span>
                  <span>{u.oficina}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
