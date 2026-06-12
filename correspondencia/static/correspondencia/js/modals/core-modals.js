/* global $, bootstrap */
(function(){
  'use strict';

  function shouldSkipDeferredField($el) {
    if (window.DashboardDeferredSelects && typeof window.DashboardDeferredSelects.isDeferredFieldId === 'function') {
      return window.DashboardDeferredSelects.isDeferredFieldId($el.attr('id') || '');
    }
    return false;
  }

  function initSelect2InModal(modalEl){
    if (!window.$ || !$.fn.select2) return;
    $(modalEl).find('.select2').each(function(){
      var $el = $(this);
      if (shouldSkipDeferredField($el)) {
        return;
      }
      var parent = $(modalEl);
      
      // Destruir Select2 si ya existe para reinicializar
      if ($el.data('select2')) {
        $el.select2('destroy');
      }
      
      // Configuración mejorada para Select2 con placeholders y búsqueda
      var config = {
        theme: 'bootstrap-5', 
        dropdownParent: parent,
        placeholder: $el.attr('data-placeholder') || 'Seleccionar...',
        allowClear: $el.attr('data-allow-clear') === 'true',
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
      };
      
      $el.select2(config);
    });
  }

  function maybeOpenOnFlag(modalEl){
    var shouldOpen = (modalEl.getAttribute('data-open') || '').toString() === 'true';
    if (shouldOpen && window.bootstrap) {
      new bootstrap.Modal(modalEl).show();
    }
  }

  document.addEventListener('DOMContentLoaded', function(){
    var modals = document.querySelectorAll('.modal');
    modals.forEach(function(modal){
      modal.addEventListener('shown.bs.modal', function(){ initSelect2InModal(modal); });
      maybeOpenOnFlag(modal);
    });
  });
})();


