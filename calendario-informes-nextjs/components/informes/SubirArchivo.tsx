'use client'

import { useCallback, useState } from 'react'
import { useDropzone } from 'react-dropzone'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { useToast } from '@/hooks/use-toast'
import { Upload, X, FileText, ChevronDown, ChevronUp, CheckCircle2, AlertCircle } from 'lucide-react'
import { subirArchivoFirmado } from '@/lib/api/informes'
import { InformeDiario } from '@/types/informes'
import { cn } from '@/lib/utils'

interface SubirArchivoProps {
  fecha: string
  informeActual: InformeDiario | null
  onUploadSuccess: () => void
}

export function SubirArchivo({ fecha, informeActual, onUploadSuccess }: SubirArchivoProps) {
  const [collapsed, setCollapsed] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const { toast } = useToast()

  const onDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0]

      // Validar tamaño (10MB)
      if (file.size > 10 * 1024 * 1024) {
        toast({
          variant: 'destructive',
          title: 'Archivo muy grande',
          description: 'El archivo no debe superar 10MB',
        })
        return
      }

      setSelectedFile(file)
    }
  }, [toast])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'image/jpeg': ['.jpg', '.jpeg'],
      'image/png': ['.png'],
    },
    maxFiles: 1,
    multiple: false,
  })

  const handleUpload = async () => {
    if (!selectedFile) return

    setUploading(true)
    try {
      await subirArchivoFirmado(fecha, selectedFile)

      toast({
        title: 'Archivo subido exitosamente',
        description: 'El archivo firmado se guardó correctamente',
        className: 'bg-success-light border-success',
      })

      setSelectedFile(null)
      onUploadSuccess()
      setCollapsed(true)
    } catch (error) {
      toast({
        variant: 'destructive',
        title: 'Error al subir archivo',
        description: 'No se pudo guardar el archivo. Intente nuevamente.',
      })
    } finally {
      setUploading(false)
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes'
    const k = 1024
    const sizes = ['Bytes', 'KB', 'MB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  return (
    <Card className="mb-6 shadow-lg border-2 border-slate-200 overflow-hidden">
      {/* Header colapsable */}
      <CardHeader
        className={cn(
          "cursor-pointer transition-all duration-200",
          "bg-gradient-to-r from-success-light/80 to-emerald-50 hover:from-success-light hover:to-emerald-100",
          "border-b-2 border-success/20"
        )}
        onClick={() => setCollapsed(!collapsed)}
      >
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-11 h-11 rounded-xl bg-success/15 flex items-center justify-center shadow-sm">
              <Upload className="w-6 h-6 text-success" strokeWidth={2.5} />
            </div>
            <div>
              <CardTitle className="text-lg font-bold text-slate-800 flex items-center gap-2">
                Subir Archivo Firmado
              </CardTitle>
              <p className="text-sm text-slate-600 font-medium mt-0.5">
                PDF o imagen escaneada de la planilla
              </p>
            </div>
          </div>
          <div className={cn(
            "w-9 h-9 rounded-full bg-white/80 flex items-center justify-center shadow-sm",
            "transition-transform duration-300",
            !collapsed && "rotate-180"
          )}>
            <ChevronDown className="w-5 h-5 text-success" strokeWidth={2.5} />
          </div>
        </div>
      </CardHeader>

      {/* Contenido colapsable */}
      <div
        className={cn(
          "transition-all duration-300 ease-in-out overflow-hidden",
          collapsed ? "max-h-0" : "max-h-[800px]"
        )}
      >
        <CardContent className="pt-6 pb-6">
          {/* Archivo actual si existe */}
          {informeActual?.tiene_archivo && (
            <div className="mb-6 p-4 bg-gradient-to-r from-blue-50 to-cyan-50 rounded-xl border-2 border-blue-200 animate-in fade-in duration-300">
              <div className="flex items-start gap-3">
                <div className="w-10 h-10 rounded-lg bg-blue-100 flex items-center justify-center flex-shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-blue-600" strokeWidth={2.5} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-bold text-blue-900 mb-1">
                    Archivo actual registrado
                  </p>
                  <a
                    href={informeActual.archivo_firmado}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-sm text-blue-700 hover:text-blue-800 underline font-medium inline-flex items-center gap-1"
                  >
                    Ver archivo subido
                    <FileText className="w-4 h-4" />
                  </a>
                  {informeActual.fecha_subida_firma && (
                    <p className="text-xs text-blue-600 mt-1 font-medium">
                      Subido el {new Date(informeActual.fecha_subida_firma).toLocaleString('es-ES', {
                        day: '2-digit',
                        month: 'long',
                        year: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit'
                      })}
                    </p>
                  )}
                </div>
              </div>
            </div>
          )}

          {/* Dropzone */}
          <div
            {...getRootProps()}
            className={cn(
              "relative border-3 border-dashed rounded-2xl p-10 text-center cursor-pointer",
              "transition-all duration-300 ease-out",
              "bg-gradient-to-br from-slate-50 to-white",
              isDragActive
                ? "border-success bg-success-light/30 scale-[1.02] shadow-lg"
                : "border-slate-300 hover:border-success/60 hover:bg-success-light/10 hover:shadow-md"
            )}
          >
            <input {...getInputProps()} />

            {/* Icon */}
            <div className={cn(
              "w-20 h-20 mx-auto mb-5 rounded-2xl flex items-center justify-center",
              "transition-all duration-300",
              isDragActive
                ? "bg-success text-white scale-110 shadow-xl"
                : "bg-slate-100 text-slate-400"
            )}>
              <Upload className={cn(
                "transition-all duration-300",
                isDragActive ? "w-10 h-10 animate-bounce" : "w-9 h-9"
              )} strokeWidth={2} />
            </div>

            {isDragActive ? (
              <div className="space-y-2 animate-in fade-in zoom-in-50 duration-200">
                <p className="text-xl font-bold text-success">
                  ¡Suelta el archivo aquí!
                </p>
                <p className="text-sm text-slate-600">
                  El archivo será cargado automáticamente
                </p>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-lg font-bold text-slate-700">
                  Arrastra el archivo aquí
                </p>
                <p className="text-sm text-slate-500 font-medium">
                  o haz click para seleccionar desde tu dispositivo
                </p>
                <div className="flex items-center justify-center gap-3 pt-2">
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full border border-slate-200 shadow-sm">
                    <div className="w-2 h-2 rounded-full bg-red-500" />
                    <span className="text-xs font-semibold text-slate-600">PDF</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full border border-slate-200 shadow-sm">
                    <div className="w-2 h-2 rounded-full bg-blue-500" />
                    <span className="text-xs font-semibold text-slate-600">JPG</span>
                  </div>
                  <div className="flex items-center gap-1.5 px-3 py-1.5 bg-white rounded-full border border-slate-200 shadow-sm">
                    <div className="w-2 h-2 rounded-full bg-green-500" />
                    <span className="text-xs font-semibold text-slate-600">PNG</span>
                  </div>
                </div>
                <p className="text-xs text-slate-400 pt-1 flex items-center justify-center gap-1">
                  <AlertCircle className="w-3.5 h-3.5" />
                  Tamaño máximo: 10 MB
                </p>
              </div>
            )}

            {/* Decorative corner accents */}
            <div className="absolute top-2 left-2 w-6 h-6 border-t-2 border-l-2 border-slate-300 rounded-tl-lg" />
            <div className="absolute top-2 right-2 w-6 h-6 border-t-2 border-r-2 border-slate-300 rounded-tr-lg" />
            <div className="absolute bottom-2 left-2 w-6 h-6 border-b-2 border-l-2 border-slate-300 rounded-bl-lg" />
            <div className="absolute bottom-2 right-2 w-6 h-6 border-b-2 border-r-2 border-slate-300 rounded-br-lg" />
          </div>

          {/* Preview del archivo seleccionado */}
          {selectedFile && (
            <div className="mt-5 p-5 bg-gradient-to-r from-slate-50 to-blue-50/30 rounded-xl border-2 border-slate-200 animate-in fade-in slide-in-from-bottom-4 duration-300">
              <div className="flex items-center gap-4">
                {/* Icon del archivo */}
                <div className="flex-shrink-0 w-14 h-14 rounded-xl bg-gradient-to-br from-primary-custom to-secondary-custom flex items-center justify-center shadow-md">
                  <FileText className="w-7 h-7 text-white" strokeWidth={2.5} />
                </div>

                {/* Info del archivo */}
                <div className="flex-1 min-w-0">
                  <p className="font-bold text-slate-800 truncate text-sm">
                    {selectedFile.name}
                  </p>
                  <div className="flex items-center gap-3 mt-1">
                    <span className="text-sm text-slate-600 font-semibold tabular-nums">
                      {formatFileSize(selectedFile.size)}
                    </span>
                    <span className="text-xs text-slate-400">•</span>
                    <span className="text-xs text-slate-500 uppercase font-bold">
                      {selectedFile.type.split('/')[1]}
                    </span>
                  </div>
                </div>

                {/* Botón eliminar */}
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setSelectedFile(null)}
                  disabled={uploading}
                  className="flex-shrink-0 hover:bg-red-100 hover:text-red-600 transition-colors"
                >
                  <X className="h-5 w-5" />
                </Button>
              </div>
            </div>
          )}

          {/* Botones de acción */}
          {selectedFile && (
            <div className="mt-6 flex gap-3 justify-end animate-in fade-in slide-in-from-bottom-2 duration-300">
              <Button
                variant="outline"
                onClick={() => setSelectedFile(null)}
                disabled={uploading}
                className="border-slate-300 hover:bg-slate-50"
              >
                Cancelar
              </Button>
              <Button
                onClick={handleUpload}
                disabled={uploading}
                className="bg-gradient-to-r from-success to-emerald-500 hover:from-success/90 hover:to-emerald-500/90 text-white font-semibold shadow-md hover:shadow-lg transition-all hover:scale-105"
              >
                {uploading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2" />
                    Subiendo...
                  </>
                ) : (
                  <>
                    <Upload className="w-4 h-4 mr-2" />
                    Subir Archivo
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </div>
    </Card>
  )
}
