"use client";

import { useState } from "react";
import { Inbox, MailCheck } from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { SalidasCorreoContent } from "@/components/dashboard/salidas-correo-modal";
import { EntradasCorreoContent } from "@/components/dashboard/entradas-correo-modal";

export default function FlujoCorreosModal() {
  const [open, setOpen] = useState(false);
  const [tab, setTab] = useState<"salida" | "entrada">("salida");

  return (
    <>
      <div className="flex w-full flex-col gap-2 sm:w-auto sm:flex-row">
        <button
          type="button"
          onClick={() => {
            setTab("salida");
            setOpen(true);
          }}
          className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-blue-500/30 bg-blue-500/10 px-3 text-xs font-semibold text-blue-300 transition-colors hover:bg-blue-500/15 sm:flex-initial"
        >
          <MailCheck className="h-4 w-4" />
          Flujo salida
        </button>
        <button
          type="button"
          onClick={() => {
            setTab("entrada");
            setOpen(true);
          }}
          className="inline-flex h-10 flex-1 items-center justify-center gap-2 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 text-xs font-semibold text-emerald-300 transition-colors hover:bg-emerald-500/15 sm:flex-initial"
        >
          <Inbox className="h-4 w-4" />
          Flujo entrada
        </button>
      </div>

      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="flex h-[92vh] w-[90vw] max-w-[90vw] flex-col gap-3 overflow-hidden p-4 sm:p-6">
          <DialogHeader className="shrink-0 space-y-1">
            <DialogTitle className="flex items-center gap-2 text-lg">
              {tab === "salida" ? (
                <>
                  <MailCheck className="h-5 w-5 text-blue-400" />
                  Flujo de salida de correos
                </>
              ) : (
                <>
                  <Inbox className="h-5 w-5 text-emerald-400" />
                  Flujo de entrada de correos
                </>
              )}
            </DialogTitle>
            <DialogDescription className="text-xs sm:text-sm">
              {tab === "salida"
                ? "Salidas por destinatario: radicado, oficina, MessageID y entrega Postmark/SMTP."
                : "Entradas al buzón institucional: remitente, ingesta, estado y radicado derivado."}
            </DialogDescription>
          </DialogHeader>

          <Tabs
            value={tab}
            onValueChange={(value) => setTab(value as "salida" | "entrada")}
            className="flex min-h-0 flex-1 flex-col gap-3"
          >
            <TabsList className="grid w-full shrink-0 grid-cols-2 sm:w-auto sm:inline-grid">
              <TabsTrigger value="salida" className="gap-1.5 text-xs">
                <MailCheck className="h-3.5 w-3.5" />
                Salida
              </TabsTrigger>
              <TabsTrigger value="entrada" className="gap-1.5 text-xs">
                <Inbox className="h-3.5 w-3.5" />
                Entrada
              </TabsTrigger>
            </TabsList>
            <TabsContent value="salida" className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden data-[state=inactive]:hidden">
              <SalidasCorreoContent />
            </TabsContent>
            <TabsContent value="entrada" className="mt-0 flex min-h-0 flex-1 flex-col overflow-hidden data-[state=inactive]:hidden">
              <EntradasCorreoContent />
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </>
  );
}
