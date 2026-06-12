"use client";

import { usePulso } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  FileText,
  ArrowUpRight,
  ArrowDownLeft,
  Building2,
  Repeat,
  Clock,
} from "lucide-react";

function StatCard({
  label,
  value,
  icon: Icon,
  sub,
  color,
}: {
  label: string;
  value: number | string;
  icon: React.ElementType;
  sub?: string;
  color?: string;
}) {
  return (
    <Card className="relative overflow-hidden">
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
          {label}
        </CardTitle>
        <Icon className={`h-4 w-4 ${color || "text-muted-foreground"}`} />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {sub && (
          <p className="text-xs text-muted-foreground mt-1">{sub}</p>
        )}
      </CardContent>
    </Card>
  );
}

export default function PulsoSection() {
  const { data, error, isLoading } = usePulso();

  if (isLoading) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {Array.from({ length: 6 }).map((_, i) => (
          <Card key={i} className="animate-pulse">
            <CardHeader className="pb-2">
              <div className="h-3 w-20 bg-muted rounded" />
            </CardHeader>
            <CardContent>
              <div className="h-7 w-12 bg-muted rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">Error al cargar pulso del sistema</p>
        </CardContent>
      </Card>
    );
  }

  const d = data;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <div className="h-2 w-2 rounded-full bg-emerald-500 animate-pulse-slow" />
        <h2 className="text-lg font-semibold">Pulso del Sistema</h2>
        <Badge variant="outline" className="text-[10px]">
          Tiempo real
        </Badge>
      </div>
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <StatCard
          label="Hoy"
          value={d?.radicados_hoy ?? 0}
          icon={FileText}
          sub="Radicados hoy"
          color="text-blue-500"
        />
        <StatCard
          label="Entrantes"
          value={d?.entrantes_hoy ?? 0}
          icon={ArrowDownLeft}
          sub="Recibidos"
          color="text-emerald-500"
        />
        <StatCard
          label="Salientes"
          value={d?.salientes_hoy ?? 0}
          icon={ArrowUpRight}
          sub="Enviados"
          color="text-amber-500"
        />
        <StatCard
          label="Internos"
          value={d?.internos_hoy ?? 0}
          icon={Building2}
          sub="Comunicaciones"
          color="text-purple-500"
        />
        <StatCard
          label="Interoficina"
          value={d?.interoficina_hoy ?? 0}
          icon={Repeat}
          sub="Entre oficinas"
          color="text-cyan-500"
        />
        <StatCard
          label="Pendientes"
          value={d?.sin_responder ?? 0}
          icon={Clock}
          sub={`${d?.plazo_vencido ?? 0} fuera de plazo`}
          color="text-red-500"
        />
      </div>
    </div>
  );
}
