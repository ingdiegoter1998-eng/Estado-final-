"use client";

import { useSLA } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ShieldCheck, AlertTriangle, XCircle } from "lucide-react";

interface SemaphoreItem {
  oficina: string;
  total: number;
  a_tiempo: number;
  por_vencer: number;
  vencidos: number;
  pct_cumplimiento: number;
}

function SemaphoreRow({ item }: { item: SemaphoreItem }) {
  const pct = item.pct_cumplimiento;
  const color =
    pct >= 80
      ? "bg-emerald-500"
      : pct >= 50
      ? "bg-amber-500"
      : "bg-red-500";

  return (
    <div className="flex items-center gap-4 py-2">
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">{item.oficina}</p>
        <div className="flex items-center gap-2 mt-1">
          <Progress
            value={pct}
            className="h-1.5 flex-1"
            indicatorClassName={color}
          />
          <span className="text-xs text-muted-foreground w-10 text-right">
            {pct}%
          </span>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs">
        <Badge variant="success" className="gap-1">
          <ShieldCheck className="h-3 w-3" />
          {item.a_tiempo}
        </Badge>
        <Badge variant="warning" className="gap-1">
          <AlertTriangle className="h-3 w-3" />
          {item.por_vencer}
        </Badge>
        <Badge variant="danger" className="gap-1">
          <XCircle className="h-3 w-3" />
          {item.vencidos}
        </Badge>
      </div>
    </div>
  );
}

export default function SLASection() {
  const { data, error, isLoading } = useSLA();

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
          <p className="text-destructive text-sm">Error al cargar datos SLA</p>
        </CardContent>
      </Card>
    );
  }

  const global = data?.global;
  const oficinas: SemaphoreItem[] = data?.por_oficina || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-4 w-4 text-emerald-500" />
            Semáforo SLA
          </CardTitle>
          {global && (
            <Badge
              variant={
                global.pct_cumplimiento >= 80
                  ? "success"
                  : global.pct_cumplimiento >= 50
                  ? "warning"
                  : "danger"
              }
            >
              Global: {global.pct_cumplimiento}%
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {global && (
          <div className="grid grid-cols-3 gap-3 mb-4 p-3 rounded-lg bg-muted/50">
            <div className="text-center">
              <p className="text-xl font-bold text-emerald-500">
                {global.a_tiempo}
              </p>
              <p className="text-[10px] text-muted-foreground uppercase">
                A tiempo
              </p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-amber-500">
                {global.por_vencer}
              </p>
              <p className="text-[10px] text-muted-foreground uppercase">
                Por vencer
              </p>
            </div>
            <div className="text-center">
              <p className="text-xl font-bold text-red-500">
                {global.vencidos}
              </p>
              <p className="text-[10px] text-muted-foreground uppercase">
                Vencidos
              </p>
            </div>
          </div>
        )}
        <div className="divide-y divide-border max-h-[300px] overflow-y-auto">
          {oficinas.map((item, i) => (
            <SemaphoreRow key={i} item={item} />
          ))}
          {oficinas.length === 0 && (
            <p className="text-sm text-muted-foreground py-4 text-center">
              Sin datos de oficinas
            </p>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
