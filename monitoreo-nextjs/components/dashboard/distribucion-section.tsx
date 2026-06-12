"use client";

import { useDistribucion } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Users, Eye, EyeOff, Forward } from "lucide-react";

interface OficinaDistribucion {
  oficina: string;
  total: number;
  leidos: number;
  sin_leer: number;
  reasignados: number;
  pct_lectura: number;
}

export default function DistribucionSection() {
  const { data, error, isLoading } = useDistribucion();

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent className="space-y-3">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-8 bg-muted rounded" />
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
            Error al cargar distribución interna
          </p>
        </CardContent>
      </Card>
    );
  }

  const global = data?.global;
  const oficinas: OficinaDistribucion[] = data?.por_oficina || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Users className="h-4 w-4 text-violet-500" />
            Distribución Interna
          </CardTitle>
          {global && (
            <div className="flex items-center gap-2">
              <Badge variant="success" className="gap-1">
                <Eye className="h-3 w-3" />
                {global.leidos}
              </Badge>
              <Badge variant="warning" className="gap-1">
                <EyeOff className="h-3 w-3" />
                {global.sin_leer}
              </Badge>
              <Badge variant="info" className="gap-1">
                <Forward className="h-3 w-3" />
                {global.reasignados}
              </Badge>
            </div>
          )}
        </div>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border max-h-[250px] overflow-y-auto">
          {oficinas.map((item, i) => (
            <div key={i} className="flex items-center gap-4 py-2">
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium truncate">{item.oficina}</p>
                <div className="flex items-center gap-2 mt-1">
                  <Progress
                    value={item.pct_lectura}
                    className="h-1.5 flex-1"
                    indicatorClassName={
                      item.pct_lectura >= 70
                        ? "bg-emerald-500"
                        : item.pct_lectura >= 40
                        ? "bg-amber-500"
                        : "bg-red-500"
                    }
                  />
                  <span className="text-xs text-muted-foreground w-10 text-right">
                    {item.pct_lectura}%
                  </span>
                </div>
              </div>
              <div className="text-xs text-muted-foreground">
                {item.total} total
              </div>
            </div>
          ))}
          {oficinas.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Sin datos de distribución
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
