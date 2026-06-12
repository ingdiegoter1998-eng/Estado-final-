/**
 * Sistema de Minimización de Modales
 * 
 * Permite minimizar modales (especialmente el de radicación) para que los usuarios
 * puedan navegar sin perder los datos ingresados en el formulario.
 * 
 * FUNCIONALIDADES:
 * - Minimizar/maximizar modales
 * - Guardar estado del modal en localStorage
 * - Guardar datos del formulario en localStorage
 * - Restaurar modal con datos cuando se regresa a la página
 * - Barra minimizada con contador de modales minimizados
 * 
 * ALMACENAMIENTO EN localStorage:
 * - modal_<modalId>_minimized: true/false (estado)
 * - modal_<modalId>_data: JSON con datos del formulario
 */

(function() {
  'use strict';

  class ModalMinimizer {
    constructor() {
      this.minimizedModals = new Map();
      this.initMinimizedBar();
    }

    /**
     * Crea la barra inferior para mostrar modales minimizados
     */
    initMinimizedBar() {
      // Verificar si ya existe
      if (document.getElementById('minimized-modals-bar')) {
        return;
      }

      const bar = document.createElement('div');
      bar.id = 'minimized-modals-bar';
      bar.className = 'minimized-modals-bar';
      bar.innerHTML = `
        <div class="minimized-bar-content">
          <span class="minimized-bar-label">
            <i class="bi bi-window-minimize"></i> Modales Minimizados:
          </span>
          <div class="minimized-bar-buttons" id="minimized-bar-buttons"></div>
        </div>
      `;

      document.body.appendChild(bar);

      // Agregar estilos si no existen
      this.addMinimizedBarStyles();
    }

    /**
     * Agrega estilos CSS para la barra de modales minimizados
     */
    addMinimizedBarStyles() {
      if (document.getElementById('minimized-modals-styles')) {
        return;
      }

      const style = document.createElement('style');
      style.id = 'minimized-modals-styles';
      style.textContent = `
        .minimized-modals-bar {
          position: fixed;
          bottom: 0;
          left: 0;
          right: 0;
          background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
          padding: 12px 20px;
          box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.2);
          z-index: 1040;
          display: none;
          border-top: 2px solid #5a67d8;
        }

        .minimized-modals-bar.active {
          display: block;
          animation: slideUp 0.3s ease-out;
        }

        @keyframes slideUp {
          from {
            transform: translateY(100%);
          }
          to {
            transform: translateY(0);
          }
        }

        .minimized-bar-content {
          display: flex;
          align-items: center;
          gap: 15px;
          max-width: 1400px;
          margin: 0 auto;
        }

        .minimized-bar-label {
          color: white;
          font-weight: 600;
          display: flex;
          align-items: center;
          gap: 8px;
          white-space: nowrap;
        }

        .minimized-bar-buttons {
          display: flex;
          gap: 10px;
          flex-wrap: wrap;
        }

        .minimized-modal-btn {
          background: rgba(255, 255, 255, 0.95);
          color: #667eea;
          border: none;
          padding: 8px 16px;
          border-radius: 4px;
          cursor: pointer;
          font-weight: 600;
          font-size: 0.9rem;
          transition: all 0.2s ease;
          display: flex;
          align-items: center;
          gap: 8px;
        }

        .minimized-modal-btn:hover {
          background: white;
          box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
          transform: translateY(-2px);
        }

        .minimized-modal-btn-close {
          background: rgba(255, 59, 48, 0.9);
          color: white;
          border: none;
          width: 24px;
          height: 24px;
          padding: 0;
          border-radius: 50%;
          cursor: pointer;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.8rem;
          transition: all 0.2s ease;
        }

        .minimized-modal-btn-close:hover {
          background: #ff3722;
          transform: scale(1.1);
        }

        /* Ajuste para modales minimizados */
        .modal.minimized {
          display: none !important;
        }

        body.has-minimized-modals {
          padding-bottom: 60px;
        }
      `;

      document.head.appendChild(style);
    }

    /**
     * Obtiene datos del formulario del modal
     * @param {HTMLElement} modal - Elemento del modal
     * @returns {Object} Datos del formulario
     */
    getFormData(modal) {
      const form = modal.querySelector('form');
      if (!form) return {};

      const data = {};

      // Obtener todos los inputs, textareas y selects
      const fields = form.querySelectorAll('input, textarea, select');
      fields.forEach(field => {
        const name = field.name || field.id;
        if (!name) return;

        if (field.type === 'checkbox') {
          data[name] = field.checked;
        } else if (field.type === 'radio') {
          if (field.checked) {
            data[name] = field.value;
          }
        } else {
          data[name] = field.value;
        }
      });

      // Guardar valores de Select2 si existen
      if (window.$) {
        const $selects = $(modal).find('select');
        $selects.each(function() {
          const $el = $(this);
          const val = $el.val();
          const name = $el.attr('name') || $el.attr('id');
          if (name && val) {
            data[name] = val;
          }
        });
      }

      return data;
    }

    /**
     * Restaura datos guardados en el formulario del modal
     * @param {HTMLElement} modal - Elemento del modal
     * @param {Object} data - Datos a restaurar
     */
    restoreFormData(modal, data) {
      const form = modal.querySelector('form');
      if (!form) return;

      // Restaurar valores de inputs normales
      Object.keys(data).forEach(key => {
        const input = form.querySelector(`[name="${key}"]`);
        if (input) {
          if (input.type === 'checkbox') {
            input.checked = data[key] === 'on' || data[key] === true;
          } else if (input.tagName === 'SELECT') {
            input.value = data[key];
            // Disparar evento change para Select2
            if (window.$) {
              $(input).val(data[key]).trigger('change');
            }
          } else {
            input.value = data[key];
          }
        }
      });

      // Disparar eventos para que JavaScript reaccione
      if (window.$) {
        $(form).find('select').trigger('change');
      }
    }

    /**
     * Minimiza un modal
     * @param {string} modalId - ID del modal a minimizar
     */
    minimizeModal(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;

      // Obtener datos del formulario
      const formData = this.getFormData(modal);

      // Guardar en localStorage
      localStorage.setItem(`modal_${modalId}_minimized`, 'true');
      localStorage.setItem(`modal_${modalId}_data`, JSON.stringify(formData));

      // Ocultar modal visualmente
      modal.classList.add('minimized');
      modal.style.display = 'none';

      // Agregar botón en la barra
      this.addMinimizedButton(modalId, modal);

      // Mostrar barra
      this.showMinimizedBar();

      // Agregar padding al body
      document.body.classList.add('has-minimized-modals');
    }

    /**
     * Maximiza un modal
     * @param {string} modalId - ID del modal a maximizar
     */
    maximizeModal(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;

      // Obtener datos guardados
      const savedData = localStorage.getItem(`modal_${modalId}_data`);
      if (savedData) {
        try {
          const data = JSON.parse(savedData);
          this.restoreFormData(modal, data);
        } catch (e) {
          console.error('Error al restaurar datos del modal:', e);
        }
      }

      // Limpiar localStorage
      localStorage.removeItem(`modal_${modalId}_minimized`);
      localStorage.removeItem(`modal_${modalId}_data`);

      // Mostrar modal
      modal.classList.remove('minimized');
      modal.style.display = '';

      // Usar Bootstrap para mostrar el modal
      if (window.bootstrap) {
        const bsModal = new bootstrap.Modal(modal);
        bsModal.show();
      }

      // Remover botón de la barra
      this.removeMinimizedButton(modalId);

      // Ocultar barra si no hay más modales minimizados
      if (this.minimizedModals.size === 0) {
        this.hideMinimizedBar();
        document.body.classList.remove('has-minimized-modals');
      }
    }

    /**
     * Cierra un modal minimizado
     * @param {string} modalId - ID del modal a cerrar
     */
    closeMinimizedModal(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;

      // Limpiar localStorage
      localStorage.removeItem(`modal_${modalId}_minimized`);
      localStorage.removeItem(`modal_${modalId}_data`);

      // Remover botón de la barra
      this.removeMinimizedButton(modalId);

      // Ocultar modal
      modal.classList.add('minimized');
      modal.style.display = 'none';

      // Ocultar barra si no hay más modales minimizados
      if (this.minimizedModals.size === 0) {
        this.hideMinimizedBar();
        document.body.classList.remove('has-minimized-modals');
      }
    }

    /**
     * Agrega un botón a la barra de modales minimizados
     * @param {string} modalId - ID del modal
     * @param {HTMLElement} modal - Elemento del modal
     */
    addMinimizedButton(modalId, modal) {
      const buttonsContainer = document.getElementById('minimized-bar-buttons');
      if (!buttonsContainer) return;

      // Obtener título del modal
      const title = modal.querySelector('.modal-title')?.textContent || 'Modal';

      // Crear botón
      const button = document.createElement('button');
      button.className = 'minimized-modal-btn';
      button.id = `btn-${modalId}`;
      button.setAttribute('data-modal-id', modalId);
      button.innerHTML = `
        <i class="bi bi-window-maximize"></i>
        <span>${title}</span>
        <button type="button" class="minimized-modal-btn-close" data-modal-id="${modalId}">
          <i class="bi bi-x"></i>
        </button>
      `;

      // Evento para maximizar al hacer click en el botón
      button.addEventListener('click', (e) => {
        if (!e.target.closest('.minimized-modal-btn-close')) {
          this.maximizeModal(modalId);
        }
      });

      // Evento para cerrar al hacer click en la X
      button.querySelector('.minimized-modal-btn-close').addEventListener('click', (e) => {
        e.stopPropagation();
        this.closeMinimizedModal(modalId);
      });

      buttonsContainer.appendChild(button);
      this.minimizedModals.set(modalId, button);
    }

    /**
     * Remueve un botón de la barra de modales minimizados
     * @param {string} modalId - ID del modal
     */
    removeMinimizedButton(modalId) {
      const button = document.getElementById(`btn-${modalId}`);
      if (button) {
        button.remove();
      }
      this.minimizedModals.delete(modalId);
    }

    /**
     * Muestra la barra de modales minimizados
     */
    showMinimizedBar() {
      const bar = document.getElementById('minimized-modals-bar');
      if (bar) {
        bar.classList.add('active');
      }
    }

    /**
     * Oculta la barra de modales minimizados
     */
    hideMinimizedBar() {
      const bar = document.getElementById('minimized-modals-bar');
      if (bar) {
        bar.classList.remove('active');
      }
    }

    /**
     * Inicializa el sistema para un modal específico
     * @param {string} modalId - ID del modal
     */
    initModalMinimization(modalId) {
      const modal = document.getElementById(modalId);
      if (!modal) return;

      // Agregar botón de minimizar al header
      const modalHeader = modal.querySelector('.modal-header');
      if (modalHeader && !modalHeader.querySelector('.btn-minimize')) {
        const minimizeBtn = document.createElement('button');
        minimizeBtn.type = 'button';
        minimizeBtn.className = 'btn-minimize';
        // Detectar si el header tiene fondo oscuro para usar color blanco
        var headerHasDarkBg = modalHeader.classList.contains('bg-primary') ||
                              modalHeader.classList.contains('bg-dark') ||
                              modalHeader.classList.contains('bg-danger') ||
                              modalHeader.classList.contains('bg-success') ||
                              modalHeader.classList.contains('text-white');
        var btnColor = headerHasDarkBg ? 'rgba(255,255,255,0.85)' : '#666';
        minimizeBtn.style.cssText = 'background: none; border: none; font-size: 20px; padding: 0 8px; cursor: pointer; color: ' + btnColor + '; margin-right: 8px;';
        minimizeBtn.innerHTML = '−';
        minimizeBtn.title = 'Minimizar modal';
        minimizeBtn.addEventListener('click', () => {
          // Guardar datos ANTES de cerrar el modal
          this.minimizeModal(modalId);
          
          // Luego cerrar el modal de Bootstrap
          if (window.bootstrap) {
            const bsModal = bootstrap.Modal.getInstance(modal);
            if (bsModal) {
              bsModal.hide();
            }
          }
        });

        // Insertar antes del botón de cerrar
        const closeBtn = modalHeader.querySelector('.btn-close');
        if (closeBtn) {
          modalHeader.insertBefore(minimizeBtn, closeBtn);
        } else {
          modalHeader.appendChild(minimizeBtn);
        }
      }

      // Verificar si estaba minimizado anteriormente
      const wasMinimized = localStorage.getItem(`modal_${modalId}_minimized`) === 'true';
      if (wasMinimized) {
        modal.classList.add('minimized');
        modal.style.display = 'none';
        this.addMinimizedButton(modalId, modal);
        this.showMinimizedBar();
        document.body.classList.add('has-minimized-modals');
      }

      // Limpiar localStorage si el modal se cierra normalmente
      modal.addEventListener('hidden.bs.modal', () => {
        localStorage.removeItem(`modal_${modalId}_minimized`);
        localStorage.removeItem(`modal_${modalId}_data`);
      });
    }
  }

  // Inicialización global
  window.modalMinimizer = new ModalMinimizer();

  document.addEventListener('DOMContentLoaded', function() {
    // Inicializar todos los modales que puedan ser minimizables
    const modals = document.querySelectorAll('[id*="modal"]');
    modals.forEach(modal => {
      window.modalMinimizer.initModalMinimization(modal.id);
    });

    // Observer para modales que se agreguen dinámicamente
    const observer = new MutationObserver(function(mutations) {
      mutations.forEach(function(mutation) {
        mutation.addedNodes.forEach(function(node) {
          if (node.nodeType === 1 && node.id && node.id.includes('modal')) {
            window.modalMinimizer.initModalMinimization(node.id);
          }
        });
      });
    });

    observer.observe(document.body, { childList: true, subtree: true });
  });
})();
