"use client";

import { createContext, useContext } from "react";

/**
 * Contiene los query-params de rango temporal activo.
 * "" = tiempo real (sin filtro), "rango=semana", "desde=2024-01-01&hasta=2024-01-31", etc.
 */
export const RangoContext = createContext("");

export function useRangoParams() {
  return useContext(RangoContext);
}
