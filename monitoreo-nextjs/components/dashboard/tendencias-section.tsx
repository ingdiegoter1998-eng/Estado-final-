"use client";

import { useTendencias } from "@/hooks/use-monitoreo";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { TrendingUp } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

export default function TendenciasSection() {
  const { data, error, isLoading } = useTendencias();

  if (isLoading) {
    return (
      <Card className="animate-pulse">
        <CardHeader>
          <div className="h-4 w-40 bg-muted rounded" />
        </CardHeader>
        <CardContent>
          <div className="h-[250px] bg-muted rounded" />
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive">
        <CardContent className="pt-6">
          <p className="text-destructive text-sm">
            Error al cargar tendencias
          </p>
        </CardContent>
      </Card>
    );
  }

  const series = data?.series || [];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="flex items-center gap-2">
          <TrendingUp className="h-4 w-4 text-emerald-500" />
          Tendencias (últimos 30 días)
        </CardTitle>
      </CardHeader>
      <CardContent>
        {series.length === 0 ? (
          <div className="h-[250px] flex items-center justify-center text-muted-foreground text-sm">
            Sin datos de tendencias
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={280}>
            <AreaChart data={series}>
              <defs>
                <linearGradient id="colorEntrantes" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(220 70% 50%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(220 70% 50%)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorSalientes" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(160 60% 45%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(160 60% 45%)" stopOpacity={0} />
                </linearGradient>
                <linearGradient id="colorInternos" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="hsl(280 65% 60%)" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="hsl(280 65% 60%)" stopOpacity={0} />
                </linearGradient>
              </defs>
              <CartesianGrid
                strokeDasharray="3 3"
                stroke="hsl(240 3.7% 15.9%)"
              />
              <XAxis
                dataKey="fecha"
                tick={{ fontSize: 10, fill: "hsl(240 5% 64.9%)" }}
                tickLine={false}
                axisLine={false}
              />
              <YAxis
                tick={{ fontSize: 10, fill: "hsl(240 5% 64.9%)" }}
                tickLine={false}
                axisLine={false}
              />
              <Tooltip
                contentStyle={{
                  backgroundColor: "hsl(240 10% 6%)",
                  border: "1px solid hsl(240 3.7% 15.9%)",
                  borderRadius: "8px",
                  fontSize: "12px",
                  color: "hsl(0 0% 98%)",
                }}
              />
              <Legend
                wrapperStyle={{ fontSize: "11px" }}
                iconType="circle"
                iconSize={8}
              />
              <Area
                type="monotone"
                dataKey="entrantes"
                name="Entrantes"
                stroke="hsl(220 70% 50%)"
                fill="url(#colorEntrantes)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="salientes"
                name="Salientes"
                stroke="hsl(160 60% 45%)"
                fill="url(#colorSalientes)"
                strokeWidth={2}
              />
              <Area
                type="monotone"
                dataKey="internos"
                name="Internos"
                stroke="hsl(280 65% 60%)"
                fill="url(#colorInternos)"
                strokeWidth={2}
              />
            </AreaChart>
          </ResponsiveContainer>
        )}
      </CardContent>
    </Card>
  );
}
