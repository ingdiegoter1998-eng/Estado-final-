/**
 * JavaScript para el modal de radicación de correspondencia.
 * 
 * Este archivo maneja toda la lógica JavaScript específica para el modal
 * de radicación manual de correspondencia, incluyendo:
 * 
 * FUNCIONALIDADES IMPLEMENTADAS EN ESTA RUN:
 * - Carga dinámica de subseries basada en serie seleccionada
 * - Selección jerárquica Entidad → Contacto (Remitente)
 * - Selección de oficina destino con dropdown simple
 * - Integración con sistema SLA
 * - Validación de formularios
 * 
 * FLUJO DE SELECCIÓN JERÁRQUICA:
 * 1. Usuario selecciona Entidad → Se cargan contactos de esa entidad
 * 2. Usuario selecciona Contacto → Se establece como remitente
 * 3. Usuario selecciona Oficina → Se establece como oficina destino
 * 4. Usuario selecciona Subserie → Se calcula SLA automáticamente
 * 
 * Dependencias:
 * - jQuery
 * - Bootstrap 5
 * - SLACalculator (sla-calculator.js)
 * 
 * Autor: Sistema de Correspondencia
 * Fecha: 2024
 */

/* global $, SLACalculator */
(function(){
  'use strict';

  /**
   * Inicializa la carga dinámica de subseries basada en la serie seleccionada.
   * 
   * FUNCIONALIDAD:
   * - Escucha cambios en el campo serie
   * - Hace petición AJAX para cargar subseries correspondientes
   * - Actualiza el dropdown de subseries dinámicamente
   * 
   * @param {HTMLElement} modal - Elemento del modal
   */
  function initSubseriesAjax(modal){
    if (!window.$) return;
    var $serie = $('#id_radicar-serie');
    var $subserie = $('#id_radicar-subserie');
    var subseriesUrl = (modal && modal.querySelector('.modal-content')) ? modal.querySelector('.modal-content').getAttribute('data-subseries-url') : null;
    if (!$serie.length || !$subserie.length || !subseriesUrl) return;

    $serie.on('change', function(){
      var serieId = $(this).val();
      if (!serieId) {
        $subserie.empty().append('<option value="">Seleccione serie primero</option>').prop('disabled', true);
        return;
      }
      $.get(subseriesUrl, { serie_id: serieId })
        .done(function(data){
          $subserie.empty().append('<option value="">---------</option>');
          $.each(data, function(_, value){
            $subserie.append('<option value="' + value.id + '">' + value.nombre + '</option>');
          });
          $subserie.prop('disabled', false);
        })
        .fail(function(){
          $subserie.empty().append('<option value="">Error al cargar</option>').prop('disabled', true);
        });
    });
  }

  /**
   * Inicializa el sistema SLA: solo configura el endpoint del calculador global.
   * La lógica de cambio de tipo_tramite la maneja sla-calculator.js vía delegación.
   *
   * @param {HTMLElement} modal - Elemento del modal
   */
  function initSLACalculator(modal){
    var content = modal ? modal.querySelector('.modal-content') : null;
    if (!content) return;
    var endpoint = content.getAttribute('data-sla-endpoint');
    if (!endpoint) return;
    if (!window.slaCalculator) {
      window.slaCalculator = new SLACalculator({ endpoint: endpoint, timeout: 10000, retryAttempts: 3 });
    } else {
      window.slaCalculator.options.endpoint = endpoint;
    }
    // No se agrega handler de change aquí; sla-calculator.js maneja todo
    // vía $(document).on('change', 'select[name*="tipo_tramite"]', ...)
  }

  /**
   * Inicializa Select2 para el campo remitente y maneja la selección de oficina destino.
   * 
   * FUNCIONALIDAD:
   * - Inicializa Select2 en el campo remitente con búsqueda
   * - Maneja la selección de oficina destino
   * - Sincroniza con el campo real del modelo
   */
  function isDashboardDeferredField(fieldId) {
    return window.DashboardDeferredSelects &&
      typeof window.DashboardDeferredSelects.isDeferredFieldId === 'function' &&
      window.DashboardDeferredSelects.isDeferredFieldId(fieldId);
  }

  function initAutocompleteRemitente(){
    if (!window.$) return;
    
    var $remitente = $('#id_radicar-remitente');
    var $oficina = $('#id_radicar-oficina_selector');
    
    // INICIALIZAR SELECT2 EN REMITENTE (omitir si carga diferida AJAX del dashboard):
    if ($remitente.length && !isDashboardDeferredField('id_radicar-remitente')) {
      // Destruir Select2 si ya existe
      if ($remitente.hasClass('select2-hidden-accessible')) {
        $remitente.select2('destroy');
      }
      
      $remitente.select2({
        theme: 'bootstrap-5',
        dropdownParent: $remitente.closest('.modal'),
        placeholder: 'Buscar por nombre, apellido o correo...',
        allowClear: true,
        width: '100%',
        minimumResultsForSearch: 0, // Siempre mostrar caja de búsqueda
        language: {
          noResults: function() {
            return "No se encontraron resultados";
          },
          searching: function() {
            return "Buscando...";
          },
          inputTooShort: function() {
            return "Ingrese más caracteres";
          }
        }
      });
    }
    
    // SELECCIÓN DE OFICINA:
    // Dropdown simple con todas las oficinas disponibles
    if ($oficina.length){
      // Forzar habilitar el campo
      $oficina.prop('disabled', false).prop('readonly', false);
      
      // SINCRONIZACIÓN CON CAMPO REAL: oficina_selector → oficina_destino
      var $oficinaReal = $('#id_radicar-oficina_destino');
      
      // Remover listeners previos para evitar duplicados
      $oficina.off('change.radicacion');
      
      // Evento cuando cambia la oficina seleccionada
      $oficina.on('change.radicacion', function(){
        var oficinaId = $(this).val();
        
        // Sincronizar con el campo real del modelo
        if ($oficinaReal.length) {
          $oficinaReal.val(oficinaId);
        }
      });
      
      // Estado inicial del campo oficina
      if ($oficina.val() && $oficinaReal.length) { 
        // Oficina ya seleccionada - sincronizar con campo real
        $oficinaReal.val($oficina.val());
      }
    }
  }

  function initQuickDistribution(modal) {
    if (!window.$ || !modal) return;

    var $modal = $(modal);
    var $form = $modal.find('form');
    var $content = $modal.find('.modal-content');
    var usersUrl = $content.data('users-url');
    var $toggle = $form.find('input[name$="distribuir_rapido"]');
    var $section = $form.find('#quick-distribution-section');
    var $office = $form.find('select[name$="oficina_destino"]');
    var $user = $form.find('select[name$="usuario_destino_rapido"]');
    var $otherOffices = $form.find('select[name$="otras_oficinas"]');

    if (!$toggle.length || !$section.length) return;

    function initSelect2Field($field, options) {
      if (!$field.length || !$.fn.select2) return;
      if (isDashboardDeferredField($field.attr('id') || '')) return;
      if ($field.hasClass('select2-hidden-accessible')) {
        $field.select2('destroy');
      }
      $field.select2($.extend({
        theme: 'bootstrap-5',
        dropdownParent: $field.closest('.modal'),
        width: '100%'
      }, options || {}));
    }

    function syncOtherOffices() {
      if (!$otherOffices.length) return;
      var officeId = String($office.val() || '');
      $otherOffices.find('option').prop('disabled', false);
      if (officeId) {
        $otherOffices.find('option[value="' + officeId + '"]').prop('disabled', true).prop('selected', false);
      }
      $otherOffices.trigger('change.select2');
    }

    function toggleSection() {
      var enabled = $toggle.is(':checked');
      $section.stop(true, true)[enabled ? 'slideDown' : 'slideUp'](150);
      $section.find('textarea, select, input').not($toggle).prop('disabled', !enabled);
      if (enabled) {
        syncOtherOffices();
        loadUsers();
      }
      $modal.trigger('radicacion:summary-update');
    }

    function loadUsers() {
      if (!usersUrl || !$user.length) return;
      var officeId = $office.val();
      var currentValue = $user.val();

      $user.empty().append('<option value="">Seleccione un usuario...</option>');

      if (!officeId) {
        $user.prop('disabled', true).trigger('change');
        return;
      }

      $user.prop('disabled', false);
      $.get(usersUrl, { oficina_id: officeId })
        .done(function(data) {
          $.each(data || [], function(_, user) {
            var option = new Option(user.nombre, user.id, false, String(user.id) === String(currentValue));
            $user.append(option);
          });
          $user.trigger('change');
        })
        .fail(function() {
          $user.empty().append('<option value="">No fue posible cargar usuarios</option>').prop('disabled', true).trigger('change');
        });
    }

    initSelect2Field($user, {
      placeholder: 'Seleccione un usuario...',
      allowClear: true
    });

    initSelect2Field($otherOffices, {
      placeholder: 'Seleccione oficinas adicionales...',
      closeOnSelect: false
    });

    $toggle.off('change.distribucionRapida').on('change.distribucionRapida', toggleSection);
    $office.off('change.distribucionRapida').on('change.distribucionRapida', function() {
      syncOtherOffices();
      loadUsers();
    });

    syncOtherOffices();
    toggleSection();
  }

  var WIZARD_REQUIRED_MSG = 'Por favor complete todos los campos obligatorios:';
  var wizardStateByModalId = {};

  function initWizardErrorBanner($form) {
    if (!$form || !$form.length) return null;

    var $banner = $form.find('#radicacion-wizard-error');
    var $text = $form.find('#radicacion-wizard-error-text');
    var $list = $form.find('#radicacion-wizard-error-list');

    if (!$banner.length) return null;

    function scrollToBanner() {
      var $body = $form.find('.radicacion-wizard-body');
      if ($body.length) {
        $body.scrollTop(0);
      }
      var bannerEl = $banner.get(0);
      if (bannerEl && bannerEl.scrollIntoView) {
        bannerEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }
    }

    function showWizardError(message, fieldLabels) {
      var labels = Array.isArray(fieldLabels) ? fieldLabels.filter(Boolean) : [];
      $text.text(message || '');
      $list.empty();
      if (labels.length) {
        labels.forEach(function(label) {
          $list.append($('<li></li>').text(label));
        });
        $list.removeClass('d-none');
      } else {
        $list.addClass('d-none');
      }
      $banner.removeClass('d-none');
      scrollToBanner();
    }

    function clearWizardError() {
      $banner.addClass('d-none');
      $text.text('');
      $list.empty().addClass('d-none');
    }

    return {
      showWizardError: showWizardError,
      clearWizardError: clearWizardError
    };
  }

  function getMedioRecepcionSelect($form) {
    if (!$form || !$form.length) return $();
    return $form.find('#id_radicar-medio_recepcion, select[name="radicar-medio_recepcion"], select[name$="-medio_recepcion"]').first();
  }

  function initAdjuntosHints($form) {
    if (!$form || !$form.length) return null;

    var $adjuntosInfo = $form.find('#adjuntos-info');

    function syncAdjuntosInfo() {
      if (!$adjuntosInfo.length) return;
      $adjuntosInfo.toggle(getMedioRecepcionSelect($form).val() === 'FISICO');
    }

    getMedioRecepcionSelect($form).off('change.radicacionAdjuntos').on('change.radicacionAdjuntos', syncAdjuntosInfo);
    syncAdjuntosInfo();

    return { syncAdjuntosInfo: syncAdjuntosInfo };
  }

  function buildWizardErrorFromMissing(missing) {
    if (!missing || !missing.length) {
      return null;
    }
    return {
      message: WIZARD_REQUIRED_MSG,
      fieldLabels: missing.map(function(item) { return item.label; })
    };
  }

  function initWizard(modal) {
    if (!window.$ || !modal) return;

    var $modal = $(modal);
    var $form = $modal.find('form');
    var $step1 = $form.find('#wizard-step-radicacion-1');
    var $step2 = $form.find('#wizard-step-radicacion-2');
    var $next = $modal.find('#radicacion-wizard-next');
    var $back = $modal.find('#radicacion-wizard-back');
    var $submit = $modal.find('#radicacion-wizard-submit');
    var $progressItems = $modal.find('.wizard-progress-item');
    var $toggle = $form.find('input[name$="distribuir_rapido"]');
    var $section = $form.find('#quick-distribution-section');
    var wizardError = initWizardErrorBanner($form);
    initAdjuntosHints($form);

    if (!$step1.length || !$step2.length || !$next.length || !$back.length || !$submit.length) return;

    var currentStep = 1;

    function fieldText(selector, fallback) {
      var $field = $form.find(selector);
      if (!$field.length) return fallback;
      if ($field.is('select')) {
        var value = $field.find('option:selected').text();
        return value && value !== '---------' ? value : fallback;
      }
      var raw = ($field.val() || '').toString().trim();
      return raw || fallback;
    }

    function selectedTexts(selector) {
      return $form.find(selector + ' option:selected').map(function(){
        return ($(this).text() || '').trim();
      }).get().filter(function(text){ return text && text !== '---------'; });
    }

    function updateSummary() {
      var isQuick = $form.find('input[name$="distribuir_rapido"]').is(':checked');
      var responsable = fieldText('select[name$="usuario_destino_rapido"]', 'Sin responsable');
      var otras = selectedTexts('select[name$="otras_oficinas"]');
      var distribucion = 'Radicación convencional';

      if (isQuick) {
        distribucion = 'Asignación inmediata';
        if (responsable && responsable !== 'Sin responsable') {
          distribucion += ' a ' + responsable;
        }
        if (otras.length) {
          distribucion += ' + ' + otras.length + ' oficina(s)';
        }
      }

      $modal.find('[data-summary-field="remitente"]').text(fieldText('select[name$="remitente"]', 'Sin seleccionar'));
      $modal.find('[data-summary-field="asunto"]').text(fieldText('textarea[name$="asunto"]', 'Sin asunto'));
      $modal.find('[data-summary-field="oficina_destino"]').text(fieldText('select[name$="oficina_destino"]', 'Sin seleccionar'));
      $modal.find('[data-summary-field="tipo_tramite"]').text(fieldText('select[name$="tipo_tramite"]', 'No definido'));
      $modal.find('[data-summary-field="distribucion"]').text(distribucion);
    }

    function updateProgress(step) {
      $progressItems.each(function() {
        var $item = $(this);
        var itemStep = Number($item.data('step'));
        $item.removeClass('is-active is-complete');
        if (itemStep === step) {
          $item.addClass('is-active');
        } else if (itemStep < step) {
          $item.addClass('is-complete');
        }
      });
    }

    function goToStep(step) {
      currentStep = step;
      var showStep2 = step === 2;
      $step1.toggleClass('d-none', showStep2).toggleClass('active', !showStep2);
      $step2.toggleClass('d-none', !showStep2).toggleClass('active', showStep2);
      $back.toggleClass('d-none', !showStep2);
      $next.toggleClass('d-none', showStep2);
      $submit.toggleClass('d-none', !showStep2);
      updateProgress(step);
      updateSummary();
    }

    function stepHasVisibleErrors($step) {
      return $step.find('.is-invalid').length > 0 ||
        $step.find('.invalid-feedback').filter(function() {
          return ($(this).text() || '').trim().length > 0;
        }).length > 0;
    }

    function initialWizardStep() {
      if (stepHasVisibleErrors($step2)) {
        return 2;
      }
      if (stepHasVisibleErrors($step1)) {
        return 1;
      }
      if ($form.find('input[name$="distribuir_rapido"]').is(':checked')) {
        return 2;
      }
      return 1;
    }

    function syncSelectValuesForSubmit() {
      $form.find('select').each(function() {
        var $el = $(this);
        var raw = $el.val();
        if (!raw) {
          return;
        }
        var values = Array.isArray(raw) ? raw : [raw];
        values.forEach(function(val) {
          val = String(val);
          if (!val) {
            return;
          }
          var escaped = val.replace(/"/g, '\\"');
          if ($el.find('option[value="' + escaped + '"]').length) {
            return;
          }
          var $selected = $el.find('option:selected').filter(function() {
            return String($(this).val()) === val;
          });
          var text = ($selected.first().text() || '').trim() || val;
          $el.append(new Option(text, val, true, true));
        });
      });
    }

    function enableFieldsForSubmit() {
      var $subserie = $form.find('select[name$="-subserie"]');
      if ($subserie.length && $subserie.val()) {
        $subserie.prop('disabled', false);
      }
      if ($toggle.length && $section.length && $toggle.is(':checked')) {
        $section.find('textarea, select, input').not($toggle).prop('disabled', false);
      }
    }

    function collectMissingRequired() {
      var missing = [];
      var remitente = $form.find('select[name$="-remitente"]').get(0);
      var asunto = $form.find('textarea[name$="-asunto"]').get(0);
      var oficina = $form.find('select[name$="-oficina_destino"]').get(0);
      var distribucionRapida = $form.find('input[name$="distribuir_rapido"]').get(0);
      var usuarioRapido = $form.find('select[name$="usuario_destino_rapido"]').get(0);

      if (!remitente || !remitente.value) missing.push({ label: 'Remitente', step: 1 });
      if (!asunto || !asunto.value.trim()) missing.push({ label: 'Asunto', step: 1 });
      if (!oficina || !oficina.value) missing.push({ label: 'Oficina Destino', step: 1 });
      if (distribucionRapida && distribucionRapida.checked && (!usuarioRapido || !usuarioRapido.value)) {
        missing.push({ label: 'Responsable principal', step: 2 });
      }
      return missing;
    }

    function syncWizardErrorBanner() {
      if (!wizardError) return;
      var missing = collectMissingRequired();
      if (!missing.length) {
        wizardError.clearWizardError();
        return;
      }
      var errorPayload = buildWizardErrorFromMissing(missing);
      if (!errorPayload) return;
      wizardError.showWizardError(errorPayload.message, errorPayload.fieldLabels);
    }

    function focusFirstMissing(missing) {
      if (!missing || !missing.length) return;
      var firstMissing = missing[0];
      if (firstMissing && firstMissing.label === 'Remitente') {
        $form.find('select[name$="-remitente"]').trigger('focus');
      } else if (firstMissing && firstMissing.label === 'Asunto') {
        $form.find('textarea[name$="-asunto"]').trigger('focus');
      } else if (firstMissing && firstMissing.label === 'Oficina Destino') {
        $form.find('select[name$="-oficina_destino"]').trigger('focus');
      } else if (firstMissing && firstMissing.label === 'Responsable principal') {
        $form.find('select[name$="usuario_destino_rapido"]').trigger('focus');
      }
    }

    function validateBeforeSubmit(e) {
      enableFieldsForSubmit();
      syncSelectValuesForSubmit();
      var missing = collectMissingRequired();
      if (!missing.length) {
        if (wizardError) {
          wizardError.clearWizardError();
        }
        return true;
      }
      if (e && typeof e.preventDefault === 'function') {
        e.preventDefault();
      }
      var targetStep = missing.some(function(item) { return item.step === 1; }) ? 1 : 2;
      goToStep(targetStep);
      syncWizardErrorBanner();
      focusFirstMissing(missing);
      return false;
    }

    wizardStateByModalId[modal.id] = {
      validateBeforeSubmit: validateBeforeSubmit
    };

    $next.off('click.radicacionWizard').on('click.radicacionWizard', function() {
      syncSelectValuesForSubmit();
      var missingStep1 = collectMissingRequired().filter(function(item) { return item.step === 1; });
      if (missingStep1.length) {
        syncWizardErrorBanner();
        focusFirstMissing(missingStep1);
        return;
      }
      if (wizardError) {
        wizardError.clearWizardError();
      }
      goToStep(2);
    });

    $back.off('click.radicacionWizard').on('click.radicacionWizard', function() {
      goToStep(1);
    });

    $form.off('input.radicacionSummary change.radicacionSummary').on('input.radicacionSummary change.radicacionSummary', 'input, textarea, select', function() {
      updateSummary();
      syncWizardErrorBanner();
    });
    $modal.off('radicacion:summary-update').on('radicacion:summary-update', updateSummary);
    $form.off('submit.radicacionWizard').on('submit.radicacionWizard', function(e) {
      if (currentStep !== 2) {
        e.preventDefault();
        e.stopImmediatePropagation();
        return false;
      }
      if (!validateBeforeSubmit(e)) {
        e.preventDefault();
        e.stopImmediatePropagation();
        return false;
      }
    });

    $modal.off('shown.bs.modal.radicacionWizard').on('shown.bs.modal.radicacionWizard', function() {
      if (wizardError) {
        wizardError.clearWizardError();
      }
      goToStep(initialWizardStep());
    });

    goToStep(initialWizardStep());
  }

  /**
   * Inicializa validación básica del formulario.
   *
   * FUNCIONALIDAD:
   * - Valida campos obligatorios antes del envío
   * - Muestra banner inline en el modal con campos faltantes
   * - Previene envío si faltan campos requeridos
   */
  function runModalRadicacionInit(modal) {
    initSubseriesAjax(modal);
    initSLACalculator(modal);
    initAutocompleteRemitente();
    initQuickDistribution(modal);
    initWizard(modal);
  }

  /**
   * Función principal para inicializar todo el modal de radicación.
   * 
   * @param {string} modalId - ID del modal a inicializar
   */
  function initModal(modalId) {
    var modal = document.getElementById(modalId);
    if (!modal) {
      return;
    }

    runModalRadicacionInit(modal);

    // Refrescar al mostrar el modal (Select2, wizard, etc.)
    modal.removeEventListener('shown.bs.modal', modal._radicacionHandler);
    modal._radicacionHandler = function() {
      runModalRadicacionInit(modal);
    };
    modal.addEventListener('shown.bs.modal', modal._radicacionHandler);
  }

  function bindRadicacionFormGuardOnce() {
    if (!window.$ || bindRadicacionFormGuardOnce._bound) {
      return;
    }
    bindRadicacionFormGuardOnce._bound = true;
    $(document).off('submit.radicacionWizardGuard', '#form-radicar-correo').on('submit.radicacionWizardGuard', '#form-radicar-correo', function(e) {
      if (e.isDefaultPrevented()) {
        return false;
      }
      var $form = $(this);
      var modalEl = this.closest('[id*="modalRadicar"]');
      var state = modalEl && modalEl.id ? wizardStateByModalId[modalEl.id] : null;
      if (state && typeof state.validateBeforeSubmit === 'function') {
        return;
      }
    });
  }

  // INICIALIZACIÓN CUANDO EL DOM ESTÉ LISTO
  document.addEventListener('DOMContentLoaded', function(){
    bindRadicacionFormGuardOnce();
    
    // Buscar todos los modales que puedan ser de radicación
    var modales = document.querySelectorAll('[id*="modalRadicar"]');
    
    modales.forEach(function(modal) {
      initModal(modal.id);
    });
    
    // También inicializar si no se encontraron modales (puede que se carguen después)
    if (modales.length === 0) {
      // Observer para modales que se agreguen dinámicamente
      var observer = new MutationObserver(function(mutations) {
        mutations.forEach(function(mutation) {
          mutation.addedNodes.forEach(function(node) {
            if (node.nodeType === 1 && node.id && node.id.includes('modalRadicar')) {
              initModal(node.id);
            }
          });
        });
      });
      
      observer.observe(document.body, { childList: true, subtree: true });
    }
    
  });

  // También inicializar inmediatamente si el DOM ya está listo
  if (document.readyState === 'loading') {
    // DOM aún cargando, esperar
  } else {
    // DOM ya listo, inicializar inmediatamente
    bindRadicacionFormGuardOnce();
    var modales = document.querySelectorAll('[id*="modalRadicar"]');
    modales.forEach(function(modal) {
      initModal(modal.id);
    });
  }
})();


