"use client";

import { useInternas } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Building2, Send, CheckCircle2, Clock } from "lucide-react";

export default function InternasSection() {
  const { data, error, isLoading } = useInternas();

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent>
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
            Error al cargar comunicaciones internas
          </p>
        </CardContent>
      </Card>
    );
  }

  const d = data;

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <Building2 className="h-4 w-4 text-indigo-500" />
          Comunicaciones Internas
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Send className="h-4 w-4 mx-auto mb-1 text-blue-500" />
            <p className="text-lg font-bold">{d?.creadas_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Creadas hoy
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <CheckCircle2 className="h-4 w-4 mx-auto mb-1 text-emerald-500" />
            <p className="text-lg font-bold">{d?.respondidas ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Respondidas
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Clock className="h-4 w-4 mx-auto mb-1 text-amber-500" />
            <p className="text-lg font-bold">{d?.pendientes ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Pendientes
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Building2 className="h-4 w-4 mx-auto mb-1 text-purple-500" />
            <p className="text-lg font-bold">{d?.total_semana ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Esta semana
            </p>
          </div>
        </div>

        {d?.oficinas_mas_activas && d.oficinas_mas_activas.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase">
              Oficinas más activas
            </h4>
            <div className="space-y-1">
              {d.oficinas_mas_activas.map((o: any, i: number) => (
                <div
                  key={i}
                  className="flex items-center justify-between text-xs py-1 px-2 rounded bg-muted/30"
                >
                  <span className="truncate">{o.oficina}</span>
                  <Badge variant="secondary">{o.total}</Badge>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
