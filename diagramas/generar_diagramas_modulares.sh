#!/usr/bin/env bash
# Diagramas DBML livianos para dbdiagram.io (evitar esquema completo >80 tablas).
set -euo pipefail
cd "$(dirname "$0")/.."

PY="${PY:-venv/bin/python}"
DOC="documentos.EntidadProductora documentos.UnidadAdministrativa documentos.OficinaProductora documentos.MacroProceso documentos.Proceso documentos.SerieDocumental documentos.SubserieDocumental"
AUTH="auth contenttypes"

echo "→ Comunicaciones internas…"
$PY manage.py dbml $AUTH $DOC \
  correspondencia.ComunicacionInterna \
  correspondencia.ComunicacionInternaDestinatario \
  correspondencia.ComunicacionInternaDistribucion \
  correspondencia.HistorialComunicacionInterna \
  correspondencia.AnexoComunicacionInterna \
  --table_names --group_by_app \
  --add_project_name "Comunicaciones Internas" \
  --add_project_notes "Oficios entre dependencias (radicado, destinatarios, anexos, historial)" \
  --output_file diagramas/generados/diagrama_comunicaciones_internas.dbml

echo "→ Correspondencia externa…"
$PY manage.py dbml $AUTH $DOC \
  correspondencia.EntidadExterna correspondencia.EntidadExternaDominio \
  correspondencia.Contacto correspondencia.AuditoriaContacto \
  correspondencia.Correspondencia correspondencia.HistorialCorrespondencia \
  correspondencia.AdjuntoCorrespondenciaRapida correspondencia.AdjuntoCorreo \
  correspondencia.CorreoEntrante correspondencia.CorreoProblematico \
  correspondencia.AdjuntoCorreoEntrante \
  correspondencia.DistribucionInternaUsuario correspondencia.AccesoCorrespondenciaOficina \
  correspondencia.Notificacion correspondencia.ComunicacionInterna \
  correspondencia.CorrespondenciaSalida correspondencia.AdjuntoSalida \
  correspondencia.HistorialSalida correspondencia.SalidaDestinatario \
  correspondencia.GrupoAgenda correspondencia.ComunicacionMasiva \
  correspondencia.ComunicacionDestinatario \
  correspondencia.FirmaCorrespondencia correspondencia.FirmaAuxiliarCorrespondencia \
  correspondencia.CorrespondenciaUrgencia correspondencia.AdjuntoUrgencia \
  correspondencia.TipoTramite correspondencia.TramiteTipo \
  correspondencia.SubserieTramite correspondencia.CalendarioLaboral \
  --table_names --group_by_app \
  --add_project_name "Correspondencia Externa" \
  --add_project_notes "Radicacion entrante/salida, contactos, correo Gmail, firmas, urgencias, SLA" \
  --output_file diagramas/generados/diagrama_correspondencia_externa.dbml

echo "→ Prestamos documentales…"
$PY manage.py dbml $AUTH \
  documentos.PrestamoDocumental documentos.DocumentoEscaneadoPrestamo \
  documentos.NotificacionAvisoPrestamo documentos.HistorialPrestamo \
  documentos.HistorialDescargaPrestamo documentos.RegistroDeArchivo \
  documentos.Documento documentos.FUID documentos.Objeto \
  documentos.SerieDocumental documentos.SubserieDocumental \
  documentos.EntidadProductora documentos.UnidadAdministrativa \
  documentos.OficinaProductora documentos.MacroProceso documentos.Proceso \
  --table_names --group_by_app \
  --add_project_name "Prestamos Documentales" \
  --add_project_notes "Solicitud, aprobacion, escaneos y devolucion de expedientes" \
  --output_file diagramas/generados/diagrama_prestamos_documentales.dbml

echo "Listo. Importar en https://dbdiagram.io/d"
