/**
 * Select2 AJAX para dashboard ventanilla cuando los querysets van vacíos (GET).
 * Reduce el HTML inicial (~196 KB) y evita cargar cientos de <option> por request.
 */
/* global $ */
(function () {
  'use strict';

  var CONTACTO_SELECTORS = [
    '#id_radicar-remitente',
    '#id_rapida_ent-remitente',
    '#id_rapida_sal-destinatario_contacto',
  ];

  var OFICINA_SELECTORS = [
    '#id_radicar-oficina_selector',
    '#id_radicar-oficina_destino',
    '#id_radicar-otras_oficinas',
    '#id_rapida_ent-oficina_destino',
    '#id_rapida_sal-oficina_emisora',
  ];

  var DEFERRED_FIELD_IDS = CONTACTO_SELECTORS.concat(OFICINA_SELECTORS).map(function (selector) {
    return selector.slice(1);
  });

  function getEndpoints() {
    return document.getElementById('dashboard-ventanilla-endpoints');
  }

  function isDeferredMode() {
    var el = getEndpoints();
    return !!(el && el.dataset.deferSelectOptions === '1');
  }

  function isDeferredFieldId(fieldId) {
    return isDeferredMode() && DEFERRED_FIELD_IDS.indexOf(fieldId) !== -1;
  }

  function destroySelect2($el) {
    if (!$el || !$el.length) {
      return;
    }
    if ($el.hasClass('select2-hidden-accessible') || $el.data('select2')) {
      try {
        $el.select2('destroy');
      } catch (e) {
        /* ignore stale Select2 instances */
      }
    }
    $el.removeClass('select2-hidden-accessible');
    $el.next('.select2-container').remove();
  }

  function getPreselectedOptions($el) {
    var data = [];
    $el.find('option').each(function () {
      var val = (this.value || '').trim();
      if (!val) {
        return;
      }
      data.push({ id: val, text: (this.text || '').trim() || val });
    });
    return data;
  }

  function triggerAjaxSearchOnOpen($el) {
    $el.off('select2:open.deferredAjax').on('select2:open.deferredAjax', function () {
      setTimeout(function () {
        var search = document.querySelector('.select2-container--open .select2-search__field');
        if (search && !search.value) {
          search.dispatchEvent(new Event('input', { bubbles: true }));
        }
      }, 0);
    });
  }

  function initContactoAjax($el, modal, url) {
    destroySelect2($el);
    var preselected = getPreselectedOptions($el);
    $el.select2({
      theme: 'bootstrap-5',
      dropdownParent: $(modal),
      placeholder: $el.attr('data-placeholder') || 'Buscar contacto...',
      allowClear: true,
      width: '100%',
      data: preselected,
      minimumInputLength: 2,
      language: {
        inputTooShort: function () {
          return 'Escriba al menos 2 caracteres';
        },
        searching: function () {
          return 'Buscando...';
        },
        noResults: function () {
          return 'No se encontraron resultados';
        },
      },
      ajax: {
        url: url,
        dataType: 'json',
        delay: 250,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        data: function (params) {
          return { q: params.term || '', limit: 20 };
        },
        processResults: function (data) {
          var items = (data && data.contactos) || [];
          return {
            results: items.map(function (c) {
              var label = c.nombre_completo || '';
              if (c.entidad) {
                label += ' — ' + c.entidad;
              }
              return { id: c.id, text: label };
            }),
          };
        },
      },
    });
  }

  function initOficinaAjax($el, modal, url) {
    destroySelect2($el);
    var isMultiple = !!$el.prop('multiple');
    var preselected = getPreselectedOptions($el);
    $el.select2({
      theme: 'bootstrap-5',
      dropdownParent: $(modal),
      placeholder: $el.attr('data-placeholder') || 'Buscar oficina...',
      allowClear: !isMultiple,
      width: '100%',
      data: preselected,
      minimumInputLength: 0,
      minimumResultsForSearch: 0,
      closeOnSelect: !isMultiple,
      language: {
        searching: function () {
          return 'Buscando...';
        },
        noResults: function () {
          return 'No se encontraron resultados';
        },
      },
      ajax: {
        url: url,
        dataType: 'json',
        delay: 200,
        headers: { 'X-Requested-With': 'XMLHttpRequest' },
        data: function (params) {
          var term = (params.term || '').trim();
          return {
            q: term,
            limit: term ? 20 : 50,
          };
        },
        processResults: function (data) {
          return { results: (data && data.results) || [] };
        },
      },
    });
    triggerAjaxSearchOnOpen($el);
  }

  function initDeferredSelects(modal) {
    if (!window.$ || !$.fn.select2 || !isDeferredMode()) {
      return;
    }

    var endpoints = getEndpoints();
    var contactosUrl = endpoints.dataset.contactosUrl;
    var oficinasUrl = endpoints.dataset.oficinasUrl;
    if (!contactosUrl || !oficinasUrl) {
      return;
    }

    CONTACTO_SELECTORS.forEach(function (selector) {
      var $el = $(modal).find(selector);
      if ($el.length) {
        initContactoAjax($el, modal, contactosUrl);
      }
    });

    OFICINA_SELECTORS.forEach(function (selector) {
      var $el = $(modal).find(selector);
      if ($el.length) {
        initOficinaAjax($el, modal, oficinasUrl);
      }
    });

    // Sincronizar oficina_selector → oficina_destino (radicación manual)
    var $oficinaSelector = $(modal).find('#id_radicar-oficina_selector');
    var $oficinaReal = $(modal).find('#id_radicar-oficina_destino');
    if ($oficinaSelector.length && $oficinaReal.length) {
      $oficinaSelector.off('change.deferredOficina').on('change.deferredOficina', function () {
        $oficinaReal.val($(this).val()).trigger('change');
      });
    }
  }

  window.DashboardDeferredSelects = {
    isDeferredMode: isDeferredMode,
    isDeferredFieldId: isDeferredFieldId,
    initModal: initDeferredSelects,
  };

  document.addEventListener('DOMContentLoaded', function () {
    if (!isDeferredMode()) {
      return;
    }
    document.querySelectorAll('.modal').forEach(function (modal) {
      modal.addEventListener('shown.bs.modal', function () {
        // Después de core-modals.js (inmediato) y radicacion.js (100 ms)
        setTimeout(function () {
          initDeferredSelects(modal);
        }, 150);
      });
    });
  });
})();
