/**
 * Sistema de Notificaciones Toast Personalizado
 * Reemplaza alert() y confirm() del navegador con notificaciones visuales
 */

// Verificar que Bootstrap esté disponible
function checkBootstrap() {
    if (typeof bootstrap === 'undefined' || typeof bootstrap.Toast === 'undefined') {
        console.error('Bootstrap Toast no está disponible. Asegúrate de que Bootstrap 5 esté cargado.');
        return false;
    }
    return true;
}

// Contenedor de toasts (se crea automáticamente si no existe)
function getToastContainer() {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'toast-container position-fixed top-0 end-0 p-2';
        container.style.zIndex = '9999';
        document.body.appendChild(container);

        // Inyectar estilos de toast mejorado una sola vez
        if (!document.getElementById('custom-toast-styles')) {
            const style = document.createElement('style');
            style.id = 'custom-toast-styles';
            style.textContent = `
                #toast-container {
                    display: grid;
                    gap: 0.55rem;
                    width: min(calc(100vw - 1rem), 380px);
                }
                .custom-toast {
                    --toast-accent: #1877f2;
                    --toast-soft-bg: rgba(24, 119, 242, 0.12);
                    width: 100%;
                    min-width: 0;
                    max-width: 360px;
                    border-radius: 18px !important;
                    border: 1px solid rgba(15, 23, 42, 0.08) !important;
                    background: rgba(255, 255, 255, 0.98) !important;
                    color: #1c1e21 !important;
                    overflow: hidden;
                    box-shadow: 0 14px 34px rgba(15, 23, 42, 0.14) !important;
                    backdrop-filter: blur(14px);
                    animation: toastEnter 0.22s cubic-bezier(0.22, 1, 0.36, 1) both;
                }
                .custom-toast::before {
                    content: '';
                    position: absolute;
                    inset: 0 auto 0 0;
                    width: 4px;
                    background: var(--toast-accent);
                }
                .custom-toast--success {
                    --toast-accent: #31a24c;
                    --toast-soft-bg: rgba(49, 162, 76, 0.12);
                }
                .custom-toast--error {
                    --toast-accent: #e04f5f;
                    --toast-soft-bg: rgba(224, 79, 95, 0.12);
                }
                .custom-toast--warning {
                    --toast-accent: #d9822b;
                    --toast-soft-bg: rgba(217, 130, 43, 0.14);
                }
                .custom-toast--info {
                    --toast-accent: #1877f2;
                    --toast-soft-bg: rgba(24, 119, 242, 0.12);
                }
                .custom-toast--rebote {
                    --toast-accent: #dc2626;
                    --toast-soft-bg: rgba(220, 38, 38, 0.12);
                }
                .custom-toast .toast-header {
                    display: flex;
                    align-items: flex-start;
                    gap: 0.75rem;
                    padding: 0.8rem 0.95rem 0.3rem 1rem;
                    background: transparent !important;
                    color: inherit !important;
                    border-bottom: none !important;
                }
                .custom-toast .toast-icon-wrap {
                    width: 2rem;
                    height: 2rem;
                    flex: 0 0 2rem;
                    display: inline-flex;
                    align-items: center;
                    justify-content: center;
                    border-radius: 999px;
                    background: var(--toast-soft-bg);
                    color: var(--toast-accent);
                }
                .custom-toast .toast-header i {
                    font-size: 0.95rem;
                    filter: none;
                }
                .custom-toast .toast-header-copy {
                    min-width: 0;
                    flex: 1;
                }
                .custom-toast .toast-title-row {
                    display: flex;
                    align-items: center;
                    gap: 0.45rem;
                    min-width: 0;
                }
                .custom-toast .toast-title {
                    font-size: 0.9rem;
                    font-weight: 700;
                    color: #1c1e21;
                }
                .custom-toast .toast-meta {
                    font-size: 0.72rem;
                    font-weight: 600;
                    color: #65676b;
                    white-space: nowrap;
                }
                .custom-toast .btn-close {
                    margin: 0.05rem 0 0 auto;
                    padding: 0.25rem;
                    transform: scale(0.82);
                    opacity: 0.5;
                    box-shadow: none !important;
                }
                .custom-toast .toast-body {
                    padding: 0 0.95rem 0.85rem 3.75rem;
                    font-size: 0.86rem;
                    line-height: 1.4;
                    color: #3a3b3c;
                }
                .custom-toast .toast-progress {
                    height: 2px;
                    width: 100%;
                    position: relative;
                    background: var(--toast-soft-bg);
                }
                .custom-toast .toast-progress-bar {
                    height: 100%;
                    width: 100%;
                    background: var(--toast-accent);
                    border-radius: 0 0 18px 18px;
                    animation: toastCountdown var(--toast-duration, 5s) linear forwards;
                }
                @keyframes toastEnter {
                    0% {
                        opacity: 0;
                        transform: translate3d(0, -8px, 0) scale(0.985);
                    }
                    100% {
                        opacity: 1;
                        transform: translate3d(0, 0, 0) scale(1);
                    }
                }
                @keyframes toastCountdown {
                    from { width: 100%; }
                    to { width: 0%; }
                }
                .toast-icon-shake { animation: toastPulse 0.34s ease-out 0.12s; }
                @keyframes toastPulse {
                    0% { transform: scale(1); }
                    45% { transform: scale(1.08); }
                    100% { transform: scale(1); }
                }
                @media (max-width: 576px) {
                    #toast-container {
                        width: calc(100vw - 0.75rem);
                    }
                    .custom-toast {
                        max-width: none;
                    }
                    .custom-toast .toast-header {
                        padding: 0.75rem 0.85rem 0.25rem 0.95rem;
                    }
                    .custom-toast .toast-body {
                        padding: 0 0.85rem 0.8rem 3.55rem;
                    }
                }
            `;
            document.head.appendChild(style);
        }
    }
    return container;
}

/**
 * Muestra una notificación toast
 * @param {string} message - Mensaje a mostrar
 * @param {string} type - Tipo: 'success', 'error', 'warning', 'info'
 * @param {number} duration - Duración en milisegundos (default: 5000)
 */
function showToast(message, type = 'info', duration = 5000) {
    // Verificar Bootstrap antes de continuar
    if (!checkBootstrap()) {
        // Fallback a alert si Bootstrap no está disponible
        alert(message);
        return null;
    }
    
    const container = getToastContainer();
    const toastId = 'toast-' + Date.now();
    
    // Mapeo de tipos a clases Bootstrap
    // Iconos según el tipo
    const icons = {
        'success': 'bi-check-circle-fill',
        'error': 'bi-exclamation-triangle-fill',
        'danger': 'bi-exclamation-triangle-fill',
        'warning': 'bi-exclamation-triangle-fill',
        'info': 'bi-info-circle-fill',
        'rebote': 'bi-envelope-x-fill'
    };

    // Títulos más descriptivos
    const titles = {
        'success': 'Operacion exitosa',
        'error': 'Ha ocurrido un error',
        'danger': 'Ha ocurrido un error',
        'warning': 'Atencion requerida',
        'info': 'Informacion',
        'rebote': 'Envío rebotado'
    };

    // Clase extra para icono de error/warning
    const shakeTypes = ['error', 'danger', 'warning', 'rebote'];

    const normalizedType = type === 'danger' ? 'error' : type;
    const typeClass = `custom-toast--${normalizedType in icons ? normalizedType : 'info'}`;
    const icon = icons[normalizedType] || icons['info'];
    const title = titles[normalizedType] || titles['info'];
    const iconExtra = shakeTypes.includes(type) ? ' toast-icon-shake' : '';
    const durationSec = (duration / 1000) + 's';
    
    const toastHTML = `
        <div id="${toastId}" class="toast custom-toast ${typeClass}" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="${duration}" style="--toast-duration:${durationSec}">
            <div class="toast-header border-0">
                <span class="toast-icon-wrap">
                    <i class="bi ${icon}${iconExtra}"></i>
                </span>
                <div class="toast-header-copy">
                    <div class="toast-title-row">
                        <strong class="toast-title me-auto">${title}</strong>
                        <span class="toast-meta">Ahora</span>
                    </div>
                </div>
                <button type="button" class="btn-close" data-bs-dismiss="toast" aria-label="Cerrar"></button>
            </div>
            <div class="toast-body">
                ${message}
            </div>
            <div class="toast-progress"><div class="toast-progress-bar"></div></div>
        </div>
    `;
    
    container.insertAdjacentHTML('beforeend', toastHTML);
    const toastElement = document.getElementById(toastId);
    const toast = new bootstrap.Toast(toastElement, {
        autohide: true,
        delay: duration,
        animation: false
    });
    
    toast.show();
    
    // Limpiar el elemento después de que se oculte
    toastElement.addEventListener('hidden.bs.toast', function() {
        toastElement.remove();
    });
    
    return toast;
}

/**
 * Muestra un modal de confirmación personalizado
 * @param {string} message - Mensaje a mostrar
 * @param {string} title - Título del modal (opcional)
 * @returns {Promise<boolean>} - Promise que resuelve a true si se confirma, false si se cancela
 */
function showConfirmModal(message, title = 'Confirmar acción') {
    // Verificar Bootstrap antes de continuar
    if (!checkBootstrap()) {
        // Fallback a confirm si Bootstrap no está disponible
        return Promise.resolve(confirm(message));
    }
    
    return new Promise((resolve) => {
        // Crear modal si no existe
        let modalElement = document.getElementById('confirmModalCustom');
        if (!modalElement) {
            modalElement = document.createElement('div');
            modalElement.id = 'confirmModalCustom';
            modalElement.className = 'modal fade';
            modalElement.innerHTML = `
                <div class="modal-dialog modal-dialog-centered">
                    <div class="modal-content">
                        <div class="modal-header bg-warning text-dark">
                            <h5 class="modal-title">
                                <i class="bi bi-question-circle-fill me-2"></i>
                                ${title}
                            </h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cerrar"></button>
                        </div>
                        <div class="modal-body">
                            <p id="confirmModalMessage" class="mb-0">${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal" id="confirmModalCancel">
                                <i class="bi bi-x-circle me-1"></i>Cancelar
                            </button>
                            <button type="button" class="btn btn-primary" id="confirmModalOk">
                                <i class="bi bi-check-circle me-1"></i>Confirmar
                            </button>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modalElement);
        } else {
            // Actualizar mensaje si el modal ya existe
            document.getElementById('confirmModalMessage').textContent = message;
            const titleElement = modalElement.querySelector('.modal-title');
            if (titleElement) {
                titleElement.innerHTML = `<i class="bi bi-question-circle-fill me-2"></i>${title}`;
            }
        }
        
        const modal = new bootstrap.Modal(modalElement);
        
        // Limpiar listeners anteriores y agregar nuevos
        const okBtn = document.getElementById('confirmModalOk');
        const cancelBtn = document.getElementById('confirmModalCancel');
        
        // Función para limpiar y agregar listeners
        const setupListeners = () => {
            // Remover todos los listeners previos clonando los botones
            const newOkBtn = okBtn.cloneNode(true);
            const newCancelBtn = cancelBtn.cloneNode(true);
            okBtn.parentNode.replaceChild(newOkBtn, okBtn);
            cancelBtn.parentNode.replaceChild(newCancelBtn, cancelBtn);
            
            // Agregar nuevos listeners
            document.getElementById('confirmModalOk').addEventListener('click', function() {
                modalElement.dataset.resolved = 'true';
                modal.hide();
                resolve(true);
            });
            
            document.getElementById('confirmModalCancel').addEventListener('click', function() {
                modalElement.dataset.resolved = 'true';
                modal.hide();
                resolve(false);
            });
        };
        
        setupListeners();
        
        // Si se cierra el modal de otra forma (X, fuera del modal, ESC)
        const handleHidden = function() {
            if (modalElement.dataset.resolved !== 'true') {
                modalElement.dataset.resolved = 'true';
                resolve(false);
            }
            modalElement.removeEventListener('hidden.bs.modal', handleHidden);
        };
        
        modalElement.addEventListener('hidden.bs.modal', handleHidden);
        
        modal.show();
    });
}

// Funciones de conveniencia - Asegurar que estén disponibles globalmente INMEDIATAMENTE
// Estas funciones deben estar disponibles tan pronto como se carga el script
window.showSuccess = function(message) { 
    return showToast(message, 'success'); 
};
window.showError = function(message) { 
    return showToast(message, 'error'); 
};
window.showWarning = function(message) { 
    return showToast(message, 'warning'); 
};
window.showInfo = function(message) { 
    return showToast(message, 'info'); 
};
window.showConfirm = showConfirmModal;

// Log de confirmación (solo en desarrollo)
if (typeof console !== 'undefined' && console.log) {
    console.log('[Notificaciones Toast] Funciones definidas:', {
        showSuccess: typeof window.showSuccess,
        showError: typeof window.showError,
        showWarning: typeof window.showWarning,
        showInfo: typeof window.showInfo,
        showConfirm: typeof window.showConfirm
    });
}

