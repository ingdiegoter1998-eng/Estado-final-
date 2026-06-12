"use client";

import { useActividad } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Activity, User, Clock } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { es } from "date-fns/locale";

interface ActividadItem {
  tipo: string;
  descripcion: string;
  usuario: string;
  fecha: string;
  radicado?: string;
}

const tipoColor: Record<string, string> = {
  creacion: "success",
  respuesta: "info",
  distribucion: "warning",
  envio: "default",
  lectura: "secondary",
  reasignacion: "outline",
};

export default function ActividadSection() {
  const { data, error, isLoading } = useActividad();

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-10 bg-muted rounded" />
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
            Error al cargar actividad reciente
          </p>
        </CardContent>
      </Card>
    );
  }

  const actividades: ActividadItem[] = data?.actividades || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Activity className="h-4 w-4 text-orange-500" />
          Actividad Reciente
        </CardTitle>
      </CardHeader>
      <CardContent>
        {actividades.length === 0 ? (
          <div className="text-center py-6">
            <Activity className="h-8 w-8 mx-auto mb-2 text-muted-foreground/30" />
            <p className="text-sm text-muted-foreground">
              Sin actividad reciente
            </p>
          </div>
        ) : (
          <div className="space-y-1 max-h-[350px] overflow-y-auto">
            {actividades.map((a, i) => (
              <div
                key={i}
                className="flex items-start gap-3 py-2 px-2 rounded hover:bg-muted/30 transition-colors"
              >
                <div className="mt-1">
                  <div className="h-2 w-2 rounded-full bg-blue-500" />
                </div>
                <div className="flex-1 min-w-0 space-y-0.5">
                  <p className="text-sm leading-tight">{a.descripcion}</p>
                  <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
                    <span className="flex items-center gap-1">
                      <User className="h-3 w-3" />
                      {a.usuario}
                    </span>
                    {a.radicado && (
                      <>
                        <span>•</span>
                        <span>{a.radicado}</span>
                      </>
                    )}
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="h-3 w-3" />
                      {formatDistanceToNow(new Date(a.fecha), {
                        addSuffix: true,
                        locale: es,
                      })}
                    </span>
                  </div>
                </div>
                <Badge
                  variant={(tipoColor[a.tipo] as any) || "secondary"}
                  className="text-[10px] shrink-0"
                >
                  {a.tipo}
                </Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
