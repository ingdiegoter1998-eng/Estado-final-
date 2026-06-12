"use client";

import { useState } from "react";
import { Calendar } from "lucide-react";

const PRESETS = [
  { value: "", label: "Tiempo real" },
  { value: "hoy", label: "Hoy" },
  { value: "ayer", label: "Ayer" },
  { value: "semana", label: "Esta semana" },
  { value: "mes", label: "Este mes" },
  { value: "7d", label: "Últimos 7 días" },
  { value: "30d", label: "Últimos 30 días" },
];

interface DateRangeFilterProps {
  value: string;
  onChange: (params: string) => void;
}

export default function DateRangeFilter({
  value,
  onChange,
}: DateRangeFilterProps) {
  const [showCustom, setShowCustom] = useState(false);
  const [desde, setDesde] = useState("");
  const [hasta, setHasta] = useState("");

  const handlePreset = (preset: string) => {
    setShowCustom(false);
    onChange(preset ? `rango=${preset}` : "");
  };

  const handleCustomApply = () => {
    if (desde) {
      const params = `desde=${desde}${hasta ? `&hasta=${hasta}` : ""}`;
      onChange(params);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-1.5">
        <Calendar className="h-4 w-4 text-muted-foreground mr-1" />
        {PRESETS.map((p) => {
          const paramValue = p.value ? `rango=${p.value}` : "";
          const isActive = value === paramValue;
          return (
            <button
              key={p.value}
              onClick={() => handlePreset(p.value)}
              className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
                isActive
                  ? "bg-primary text-primary-foreground shadow-sm"
                  : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              {p.value === "" && isActive && (
                <span className="inline-block h-1.5 w-1.5 rounded-full bg-emerald-400 mr-1.5 animate-pulse" />
              )}
              {p.label}
            </button>
          );
        })}
        <button
          onClick={() => setShowCustom(!showCustom)}
          className={`px-3 py-1 rounded-full text-xs font-medium transition-all ${
            showCustom || (value && !PRESETS.some((p) => (p.value ? `rango=${p.value}` : "") === value))
              ? "bg-primary text-primary-foreground shadow-sm"
              : "bg-muted/60 text-muted-foreground hover:bg-muted hover:text-foreground"
          }`}
        >
          Personalizado
        </button>
      </div>
      {showCustom && (
        <div className="flex items-center gap-2 pl-6">
          <input
            type="date"
            value={desde}
            onChange={(e) => setDesde(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <span className="text-xs text-muted-foreground">→</span>
          <input
            type="date"
            value={hasta}
            onChange={(e) => setHasta(e.target.value)}
            className="h-8 rounded-md border border-input bg-background px-3 text-xs focus:outline-none focus:ring-1 focus:ring-ring"
          />
          <button
            onClick={handleCustomApply}
            disabled={!desde}
            className="h-8 px-4 rounded-md bg-primary text-primary-foreground text-xs font-medium disabled:opacity-50 hover:bg-primary/90 transition-colors"
          >
            Aplicar
          </button>
        </div>
      )}
    </div>
  );
}
