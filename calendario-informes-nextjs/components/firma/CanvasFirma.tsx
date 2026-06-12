'use client'

import { forwardRef, useImperativeHandle } from 'react'
import { useFirmaCanvas } from '@/lib/hooks/useFirmaCanvas'
import { Button } from '@/components/ui/button'
import { Eraser, CheckCircle2 } from 'lucide-react'
import { cn } from '@/lib/utils'

interface CanvasFirmaProps {
  onFirmaClear?: () => void
}

export interface CanvasFirmaRef {
  getBase64: () => string | null
  clearCanvas: () => void
  isEmpty: boolean
}

export const CanvasFirma = forwardRef<CanvasFirmaRef, CanvasFirmaProps>(
  ({ onFirmaClear }, ref) => {
    const {
      canvasRef,
      isEmpty,
      startDrawing,
      draw,
      stopDrawing,
      handleTouchStart,
      handleTouchMove,
      handleTouchEnd,
      clearCanvas,
      getBase64,
    } = useFirmaCanvas()

    // Exponer métodos al componente padre
    useImperativeHandle(ref, () => ({
      getBase64,
      clearCanvas,
      isEmpty,
    }))

    const handleClear = () => {
      clearCanvas()
      onFirmaClear?.()
    }

    return (
      <div className="space-y-4">
        {/* Canvas container */}
        <div
          className="relative border-3 border-dashed rounded-xl overflow-hidden bg-white shadow-inner"
          style={{ touchAction: 'none' }} // Evitar scroll en touch
        >
          {/* Guía de firma */}
          <div className="absolute inset-0 pointer-events-none flex items-center justify-center">
            <p className={cn(
              "text-slate-300 text-sm font-medium transition-opacity duration-300",
              !isEmpty && "opacity-0"
            )}>
              Dibuja tu firma aquí
            </p>
          </div>

          <canvas
            ref={canvasRef}
            onMouseDown={startDrawing}
            onMouseMove={draw}
            onMouseUp={stopDrawing}
            onMouseLeave={stopDrawing}
            onTouchStart={handleTouchStart}
            onTouchMove={handleTouchMove}
            onTouchEnd={handleTouchEnd}
            className="cursor-crosshair w-full block"
          />
        </div>

        {/* Controls */}
        <div className="flex justify-between items-center">
          <div className="flex items-center gap-2">
            {!isEmpty && (
              <div className="flex items-center gap-2 text-success animate-in fade-in slide-in-from-left duration-300">
                <CheckCircle2 className="w-4 h-4" strokeWidth={2.5} />
                <span className="text-sm font-semibold">
                  Firma capturada
                </span>
              </div>
            )}
            {isEmpty && (
              <p className="text-sm text-slate-500 font-medium">
                Usa tu dedo o mouse para firmar
              </p>
            )}
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleClear}
            disabled={isEmpty}
            className={cn(
              "transition-all",
              !isEmpty && "hover:bg-red-50 hover:text-red-600 hover:border-red-300"
            )}
          >
            <Eraser className="h-4 w-4 mr-2" />
            Limpiar
          </Button>
        </div>
      </div>
    )
  }
)

CanvasFirma.displayName = 'CanvasFirma'
