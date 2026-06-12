"use client";

import { useState, useEffect } from "react";
import { format } from "date-fns";
import { es } from "date-fns/locale";
import {
  Monitor,
  RefreshCw,
  Sun,
  Moon,
  LogOut,
  MessageSquare,
  History,
} from "lucide-react";
import { RangoContext } from "@/hooks/use-rango";
import DateRangeFilter from "@/components/dashboard/date-range-filter";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Separator } from "@/components/ui/separator";
import { useResumenChat } from "@/hooks/use-chat";
import PulsoSection from "@/components/dashboard/pulso-section";
import SLASection from "@/components/dashboard/sla-section";
import EnvioSection from "@/components/dashboard/envio-section";
import EmailSyncSection from "@/components/dashboard/email-sync-section";
import DistribucionSection from "@/components/dashboard/distribucion-section";
import InternasSection from "@/components/dashboard/internas-section";
import UrgenciasSection from "@/components/dashboard/urgencias-section";
import TendenciasSection from "@/components/dashboard/tendencias-section";
import ActividadSection from "@/components/dashboard/actividad-section";
import NotificacionesSection from "@/components/dashboard/notificaciones-section";
import DespliegueOficinasSection from "@/components/dashboard/despliegue-oficinas-section";
import RebotesGlobalModal from "@/components/dashboard/rebotes-global-modal";
import SalidasCorreoModal from "@/components/dashboard/salidas-correo-modal";
import { appPath } from "@/lib/app-path";

export default function DashboardPage() {
  const [darkMode, setDarkMode] = useState(true);
  const [isMounted, setIsMounted] = useState(false);
  const [nowLabel, setNowLabel] = useState("");
  const [rangoParams, setRangoParams] = useState("");
  const { data: chatResumen } = useResumenChat();

  useEffect(() => {
    const updateNowLabel = () => {
      setNowLabel(format(new Date(), "EEEE, d MMM yyyy HH:mm:ss", { locale: es }));
    };

    setIsMounted(true);
    updateNowLabel();

    const timer = setInterval(updateNowLabel, 1000);
    return () => clearInterval(timer);
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return (
    <TooltipProvider>
      <div className="min-h-screen bg-background text-foreground">
        {/* Header */}
        <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
          <div className="dashboard-shell flex h-14 items-center justify-between">
            <div className="flex items-center gap-3">
              <Monitor className="h-5 w-5 text-blue-500" />
              <div>
                <h1 className="text-sm font-bold tracking-tight">
                  Monitoreo | Gestión Documental
                </h1>
                <p className="text-[10px] text-muted-foreground">
                  E.S.E Hospital Sarare
                </p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <span
                className="text-xs text-muted-foreground font-mono"
                suppressHydrationWarning
              >
                {isMounted ? nowLabel : ""}
              </span>
              <Separator orientation="vertical" className="h-5" />
              <a
                href={appPath("/chat")}
                className="relative p-1.5 rounded-md hover:bg-muted transition-colors"
                title="Centro de Soporte"
              >
                <MessageSquare className="h-4 w-4" />
                {chatResumen && chatResumen.no_leidos > 0 && (
                  <span className="absolute -top-0.5 -right-0.5 bg-red-500 text-white text-[8px] font-bold rounded-full w-3.5 h-3.5 flex items-center justify-center">
                    {chatResumen.no_leidos > 9 ? "9+" : chatResumen.no_leidos}
                  </span>
                )}
              </a>
              <button
                onClick={() => setDarkMode(!darkMode)}
                className="p-1.5 rounded-md hover:bg-muted transition-colors"
                title={darkMode ? "Modo claro" : "Modo oscuro"}
              >
                {darkMode ? (
                  <Sun className="h-4 w-4" />
                ) : (
                  <Moon className="h-4 w-4" />
                )}
              </button>
              <button
                onClick={() =>
                  (window.location.href =
                    "/registros/correspondencia/logout/")
                }
                className="p-1.5 rounded-md hover:bg-muted transition-colors"
                title="Cerrar sesión"
              >
                <LogOut className="h-4 w-4" />
              </button>
            </div>
          </div>
        </header>

        {/* Main content */}
        <main className="dashboard-shell py-6 space-y-6">
          {/* Date range filter */}
          <DateRangeFilter value={rangoParams} onChange={setRangoParams} />

          <RangoContext.Provider value={rangoParams}>
          {/* Botón global de errores de envío */}
          <RebotesGlobalModal />

          {/* Zone 1: Pulso */}
          <PulsoSection />

          <Separator />

          {/* Tabs for the rest of sections */}
          <Tabs defaultValue="operaciones" className="w-full">
            <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
              <TabsList className="grid w-full grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 lg:w-auto lg:inline-grid">
                <TabsTrigger value="operaciones">Operaciones</TabsTrigger>
                <TabsTrigger value="comunicaciones">Comunicaciones</TabsTrigger>
                <TabsTrigger value="tendencias">Tendencias</TabsTrigger>
                <TabsTrigger value="despliegue">Despliegue</TabsTrigger>
                <TabsTrigger value="sistema">Sistema</TabsTrigger>
              </TabsList>
              <SalidasCorreoModal />
            </div>

            <TabsContent value="operaciones" className="space-y-6 mt-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <SLASection />
                <UrgenciasSection />
              </div>
              <DistribucionSection />
            </TabsContent>

            <TabsContent value="comunicaciones" className="space-y-6 mt-6">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <EnvioSection />
                <InternasSection />
              </div>
              <NotificacionesSection />
            </TabsContent>

            <TabsContent value="tendencias" className="space-y-6 mt-6">
              <TendenciasSection />
              <ActividadSection />
            </TabsContent>

            <TabsContent value="despliegue" className="space-y-6 mt-6">
              <DespliegueOficinasSection />
            </TabsContent>

            <TabsContent value="sistema" className="space-y-6 mt-6">
              <EmailSyncSection />
            </TabsContent>
          </Tabs>
          </RangoContext.Provider>
        </main>

        {/* Footer */}
        <footer className="border-t py-4">
          <div className="dashboard-shell flex items-center justify-between text-[10px] text-muted-foreground">
            <span>
              Monitoreo en tiempo real — Solo superusuarios
            </span>
            <span className="flex items-center gap-1">
              {rangoParams ? (
                <>
                  <History className="h-3 w-3" />
                  Vista histórica
                </>
              ) : (
                <>
                  <RefreshCw className="h-3 w-3" />
                  Auto-refresh activo
                </>
              )}
            </span>
          </div>
        </footer>
      </div>
    </TooltipProvider>
  );
}
