"use client";

import { useNotificaciones } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Bell, BellOff, CheckCircle2, MailWarning } from "lucide-react";

export default function NotificacionesSection() {
  const { data, error, isLoading } = useNotificaciones();

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
            Error al cargar notificaciones
          </p>
        </CardContent>
      </Card>
    );
  }

  const d = data;

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Bell className="h-4 w-4 text-yellow-500" />
            Notificaciones
          </CardTitle>
          {(d?.sin_leer ?? 0) > 0 && (
            <Badge variant="warning">{d?.sin_leer} sin leer</Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <Bell className="h-4 w-4 mx-auto mb-1 text-yellow-500" />
            <p className="text-lg font-bold">{d?.total_hoy ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Hoy
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <MailWarning className="h-4 w-4 mx-auto mb-1 text-amber-500" />
            <p className="text-lg font-bold">{d?.sin_leer ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Sin leer
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <CheckCircle2 className="h-4 w-4 mx-auto mb-1 text-emerald-500" />
            <p className="text-lg font-bold">{d?.leidas ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Leídas
            </p>
          </div>
          <div className="rounded-lg bg-muted/50 p-3 text-center">
            <BellOff className="h-4 w-4 mx-auto mb-1 text-muted-foreground" />
            <p className="text-lg font-bold">{d?.total_semana ?? 0}</p>
            <p className="text-[10px] text-muted-foreground uppercase">
              Esta semana
            </p>
          </div>
        </div>

        {d?.por_tipo && d.por_tipo.length > 0 && (
          <div className="mt-4 space-y-2">
            <h4 className="text-xs font-medium text-muted-foreground uppercase">
              Por tipo
            </h4>
            <div className="flex flex-wrap gap-2">
              {d.por_tipo.map((t: any, i: number) => (
                <Badge key={i} variant="outline" className="text-[10px]">
                  {t.tipo}: {t.total}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
