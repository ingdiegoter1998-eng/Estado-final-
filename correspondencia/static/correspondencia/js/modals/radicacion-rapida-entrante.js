/**
 * JavaScript para el modal de radicación rápida entrante.
 * 
 * Cálculo automático de fecha límite de respuesta según tipo de trámite
 * y fecha de recepción del documento.
 * 
 * Compatible con Select2 (usa jQuery .on('change') para selects).
 */

(function() {
  'use strict';

  let TIPOS_TRAMITE_CACHE = null;

  async function cargarTiposTramite() {
    if (TIPOS_TRAMITE_CACHE) return TIPOS_TRAMITE_CACHE;
    try {
      const response = await fetch('/registros/correspondencia/api/tipos-tramite/');
      if (!response.ok) throw new Error('Error al cargar tipos de trámite');
      TIPOS_TRAMITE_CACHE = await response.json();
      return TIPOS_TRAMITE_CACHE;
    } catch (error) {
      console.error('Error cargando tipos de trámite:', error);
      return {};
    }
  }

  function calcularDiasHabiles(fechaInicio, diasHabiles) {
    let fechaActual = new Date(fechaInicio);
    let diasAgregados = 0;
    while (diasAgregados < diasHabiles) {
      fechaActual.setDate(fechaActual.getDate() + 1);
      if (fechaActual.getDay() !== 0 && fechaActual.getDay() !== 6) {
        diasAgregados++;
      }
    }
    return fechaActual;
  }

  function formatearFecha(fecha) {
    const year = fecha.getFullYear();
    const month = String(fecha.getMonth() + 1).padStart(2, '0');
    const day = String(fecha.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  }

  /**
   * Función principal: recalcula fecha límite.
   * Lee el tipo de trámite y la fecha de recepción del DOM y actualiza fecha_limite.
   */
  async function recalcularFechaLimite(prefix) {
    const tipoTramiteField = document.getElementById(`id_${prefix}-tipo_tramite`);
    const fechaLimiteField = document.getElementById(`id_${prefix}-fecha_limite_respuesta_manual`);
    const fechaRecepcionField = document.getElementById(`id_${prefix}-fecha_recepcion_documento`);

    if (!tipoTramiteField || !fechaLimiteField) return;

    const tipoTramite = tipoTramiteField.value;
    if (!tipoTramite) return;

    const tiposTramite = await cargarTiposTramite();
    if (!tiposTramite[tipoTramite]) return;

    const diasRespuesta = tiposTramite[tipoTramite].dias_respuesta;
    if (diasRespuesta === null || diasRespuesta === undefined) {
      fechaLimiteField.value = '';
      return;
    }

    // Fecha base: fecha_recepcion_documento o fecha actual
    let fechaBase;
    let origenFecha;

    if (fechaRecepcionField && fechaRecepcionField.value) {
      fechaBase = new Date(fechaRecepcionField.value + 'T00:00:00');
      origenFecha = fechaRecepcionField.value;
    } else {
      fechaBase = new Date();
      origenFecha = 'hoy';
    }

    const fechaLimite = calcularDiasHabiles(fechaBase, diasRespuesta);
    const fechaLimiteStr = formatearFecha(fechaLimite);

    fechaLimiteField.value = fechaLimiteStr;
    console.log(`Fecha límite: ${fechaLimiteStr} (${diasRespuesta} días hábiles desde ${origenFecha})`);

    // Efecto visual
    fechaLimiteField.style.borderColor = '#198754';
    fechaLimiteField.style.boxShadow = '0 0 0 0.2rem rgba(25, 135, 84, 0.25)';
    setTimeout(() => {
      fechaLimiteField.style.borderColor = '';
      fechaLimiteField.style.boxShadow = '';
    }, 1500);

    // Notificación
    mostrarNotificacion(
      `Fecha límite: ${fechaLimiteStr} (${diasRespuesta} días hábiles desde ${origenFecha})`,
      'info'
    );
  }

  function mostrarNotificacion(mensaje, tipo) {
    // Remover notificaciones anteriores de este tipo
    document.querySelectorAll('.notif-fecha-limite').forEach(el => el.remove());

    const notif = document.createElement('div');
    notif.className = `alert alert-${tipo} alert-dismissible fade show position-fixed notif-fecha-limite`;
    notif.style.cssText = 'top: 20px; right: 20px; z-index: 99999; min-width: 300px; max-width: 500px;';
    notif.innerHTML = `
      <i class="bi bi-calendar-check me-2"></i>${mensaje}
      <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    document.body.appendChild(notif);
    setTimeout(() => {
      notif.classList.remove('show');
      setTimeout(() => notif.remove(), 150);
    }, 4000);
  }

  /**
   * Configura los listeners. Se llama cuando el modal se muestra (shown.bs.modal)
   * para que Select2 ya esté inicializado.
   */
  function configurarListeners(prefix) {
    const tipoTramiteField = document.getElementById(`id_${prefix}-tipo_tramite`);
    const fechaRecepcionField = document.getElementById(`id_${prefix}-fecha_recepcion_documento`);

    if (!tipoTramiteField) {
      console.warn('Campo tipo_tramite no encontrado');
      return;
    }

    // Limpiar listeners anteriores usando un namespace
    const ns = 'radicacionRapida';

    // Select2: usar jQuery .on('change') — funciona con Select2
    if (typeof jQuery !== 'undefined') {
      const $tipo = jQuery(tipoTramiteField);
      $tipo.off(`change.${ns}`);
      $tipo.on(`change.${ns}`, function() {
        console.log('Tipo de trámite cambió (jQuery):', this.value);
        recalcularFechaLimite(prefix);
      });
      console.log('Listener jQuery configurado en tipo_tramite');
    } else {
      // Fallback sin jQuery
      tipoTramiteField.removeEventListener('change', tipoTramiteField._recalcHandler);
      tipoTramiteField._recalcHandler = () => recalcularFechaLimite(prefix);
      tipoTramiteField.addEventListener('change', tipoTramiteField._recalcHandler);
      console.log('Listener nativo configurado en tipo_tramite');
    }

    // Fecha de recepción: input nativo (no usa Select2)
    if (fechaRecepcionField) {
      fechaRecepcionField.removeEventListener('change', fechaRecepcionField._recalcHandler);
      fechaRecepcionField._recalcHandler = () => {
        console.log('Fecha recepción cambió:', fechaRecepcionField.value);
        recalcularFechaLimite(prefix);
      };
      fechaRecepcionField.addEventListener('change', fechaRecepcionField._recalcHandler);
      console.log('Listener configurado en fecha_recepcion_documento');
    }
  }

  // Inicialización
  document.addEventListener('DOMContentLoaded', function() {
    // Pre-cargar tipos de trámite
    cargarTiposTramite();

    const modalElement = document.getElementById('modalRadicacionRapidaEntrante');
    if (modalElement) {
      // Configurar listeners DESPUÉS de que el modal se muestre (Select2 ya está listo)
      modalElement.addEventListener('shown.bs.modal', function() {
        // Pequeño delay para asegurar que Select2 terminó de inicializarse
        setTimeout(() => {
          configurarListeners('rapida_ent');
        }, 100);
      });
    } else {
      // Si no hay modal (página directa), configurar inmediatamente
      configurarListeners('rapida_ent');
    }
  });

})();
