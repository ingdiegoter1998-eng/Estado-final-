/**
 * Sistema de Notificaciones con Polling
 * Consulta el servidor cada 20 segundos para obtener nuevas notificaciones
 * Reproduce sonido cuando hay notificaciones nuevas
 */

(function() {
    'use strict';
    
    const POLLING_INTERVAL = 20000; // 20 segundos
    const NOTIFICATION_SOUND_URL = '/static/correspondencia/sounds/notification.mp3';
    
    let lastNotificationCount = 0;
    let pollingInterval = null;
    let notificationSound = null;
    
    // Inicializar
    function init() {
        // Crear elemento de audio para notificaciones
        notificationSound = new Audio(NOTIFICATION_SOUND_URL);
        notificationSound.volume = 0.5; // Volumen al 50%
        
        // Cargar notificaciones inmediatamente
        cargarNotificaciones();
        
        // Iniciar polling
        iniciarPolling();
        
        // Event listeners
        document.getElementById('marcarTodasLeidasBtn')?.addEventListener('click', marcarTodasLeidas);
        
        // Recargar notificaciones al abrir el dropdown
        document.getElementById('notificationsDropdown')?.addEventListener('click', function() {
            cargarNotificaciones();
        });
    }
    
    // Iniciar polling cada 20 segundos
    function iniciarPolling() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
        
        pollingInterval = setInterval(() => {
            cargarNotificaciones();
        }, POLLING_INTERVAL);
        
        console.log('[Notificaciones] Polling iniciado cada', POLLING_INTERVAL / 1000, 'segundos');
    }
    
    // Cargar notificaciones desde el servidor
    async function cargarNotificaciones() {
        try {
            const response = await fetch('/registros/correspondencia/notificaciones/obtener/');
            const data = await response.json();
            
            if (data.success) {
                const totalNoLeidas = data.total_no_leidas;
                
                // Detectar si hay nuevas notificaciones
                if (totalNoLeidas > lastNotificationCount && lastNotificationCount > 0) {
                    reproducirSonido();
                    animarCampana();
                }
                
                lastNotificationCount = totalNoLeidas;
                
                // Actualizar UI
                actualizarBadge(totalNoLeidas);
                renderizarNotificaciones(data.no_leidas, data.leidas);
            }
        } catch (error) {
            console.error('[Notificaciones] Error al cargar:', error);
        }
    }
    
    // Actualizar badge de contador
    function actualizarBadge(count) {
        const badge = document.getElementById('notificationBadge');
        const panelCount = document.getElementById('notificationPanelCount');
        const marcarTodasBtn = document.getElementById('marcarTodasLeidasBtn');
        const countLabel = count > 99 ? '99+' : String(count);
        
        if (badge) {
            if (count > 0) {
                badge.textContent = countLabel;
                badge.style.display = 'block';
                if (marcarTodasBtn) marcarTodasBtn.style.display = 'inline-block';
            } else {
                badge.style.display = 'none';
                if (marcarTodasBtn) marcarTodasBtn.style.display = 'none';
            }
        }

        if (panelCount) {
            panelCount.textContent = count === 1
                ? '1 sin leer'
                : `${countLabel} sin leer`;
        }
    }
    
    // Renderizar notificaciones en el dropdown
    function renderizarNotificaciones(noLeidas, leidas) {
        const container = document.getElementById('notificationsContent');
        if (!container) return;
        
        let html = '';
        
        // Notificaciones no leídas
        if (noLeidas.length > 0) {
            html += '<li class="notifications-group-label">Nuevas</li>';
            noLeidas.forEach((notif, index) => {
                html += renderizarNotificacion(notif, false);
            });
        }
        
        // Notificaciones leídas
        if (leidas.length > 0) {
            if (noLeidas.length > 0) {
                html += '<li><hr class="dropdown-divider"></li>';
            }
            html += '<li class="notifications-group-label">Anteriores</li>';
            leidas.forEach(notif => {
                html += renderizarNotificacion(notif, true);
            });
        }
        
        // Si no hay notificaciones
        if (noLeidas.length === 0 && leidas.length === 0) {
             html = '<li><div class="notifications-empty">' +
                 '<i class="bi bi-bell-slash"></i>' +
                 '<span class="notifications-empty-title">Estás al día</span>' +
                 '<span class="notifications-empty-copy">No tienes avisos pendientes por revisar.</span>' +
                   '</div></li>';
        }
        
        container.innerHTML = html;
        
        // Agregar event listeners a las notificaciones
        container.querySelectorAll('.notificacion-item').forEach(item => {
            item.addEventListener('click', function(e) {
                e.preventDefault();
                const notifId = this.dataset.id;
                const url = this.dataset.url;
                marcarNotificacionLeida(notifId, url);
            });
        });
    }
    
    // Renderizar una notificación individual
    function renderizarNotificacion(notif, leida) {
        const iconos = {
            'asignacion': 'bi-person-check-fill',
            'compartido': 'bi-share-fill',
            'respuesta': 'bi-reply-fill',
            'vencimiento': 'bi-clock-history',
            'comunicacion_interna': 'bi-file-earmark-text-fill',
            'rebote': 'bi-envelope-x-fill',
            'otro': 'bi-info-circle-fill'
        };

        const tipoLabels = {
            'asignacion': 'Asignación',
            'compartido': 'Compartido',
            'respuesta': 'Respuesta',
            'vencimiento': 'Vencimiento',
            'comunicacion_interna': 'Comunicación',
            'rebote': 'Rebote',
            'otro': 'Aviso'
        };
        
        const icono = iconos[notif.tipo] || iconos['otro'];
        const tipoLabel = tipoLabels[notif.tipo] || tipoLabels['otro'];
        const fechaRelativa = calcularTiempoRelativo(notif.fecha_creacion);
        const claseLeida = leida ? 'is-read' : 'is-unread';
        const unreadPill = leida ? '' : '<span class="notif-pill">Nuevo</span>';
        
        return `
            <li>
                <a href="#" class="dropdown-item notificacion-item ${claseLeida}" 
                   data-id="${notif.id}" data-url="${notif.url}">
                    <div class="notif-wrap">
                        <div class="notif-icon">
                            <i class="bi ${icono}"></i>
                        </div>
                        <div class="notif-content">
                            <span class="notif-type">${tipoLabel}</span>
                            <div class="notif-title-row">
                                <div class="notif-title">${escapeHtml(notif.titulo)}</div>
                                ${unreadPill}
                            </div>
                            <div class="notif-message">${escapeHtml(notif.mensaje)}</div>
                            <div class="notif-meta">
                                <span><i class="bi bi-clock me-1"></i>${fechaRelativa}</span>
                                <span class="notif-cta">Ver</span>
                            </div>
                        </div>
                    </div>
                </a>
            </li>
        `;
    }
    
    // Función auxiliar para escapar HTML
    function escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
    
    // Calcular tiempo relativo (ej: "hace 5 minutos")
    function calcularTiempoRelativo(fechaISO) {
        const ahora = new Date();
        const fecha = new Date(fechaISO);
        const diff = Math.floor((ahora - fecha) / 1000); // diferencia en segundos
        
        if (diff < 60) return 'Hace un momento';
        if (diff < 3600) return `Hace ${Math.floor(diff / 60)} minutos`;
        if (diff < 86400) return `Hace ${Math.floor(diff / 3600)} horas`;
        if (diff < 604800) return `Hace ${Math.floor(diff / 86400)} días`;
        return fecha.toLocaleDateString('es-CO');
    }
    
    // Marcar una notificación como leída y navegar
    async function marcarNotificacionLeida(notifId, url) {
        try {
            const csrfToken = getCookie('csrftoken');
            await fetch(`/registros/correspondencia/notificaciones/${notifId}/marcar-leida/`, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            
            // Navegar a la URL de destino
            if (url && url !== '#') {
                window.location.href = url;
            }
        } catch (error) {
            console.error('[Notificaciones] Error al marcar como leída:', error);
            // Navegar de todas formas
            if (url && url !== '#') {
                window.location.href = url;
            }
        }
    }
    
    // Marcar todas las notificaciones como leídas
    async function marcarTodasLeidas() {
        try {
            const csrfToken = getCookie('csrftoken');
            const response = await fetch('/registros/correspondencia/notificaciones/marcar-todas-leidas/', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            if (data.success) {
                // Recargar notificaciones
                cargarNotificaciones();
            }
        } catch (error) {
            console.error('[Notificaciones] Error al marcar todas como leídas:', error);
        }
    }
    
    // Reproducir sonido de notificación
    function reproducirSonido() {
        if (notificationSound) {
            notificationSound.play().catch(error => {
                console.warn('[Notificaciones] No se pudo reproducir el sonido:', error);
            });
        }
    }
    
    // Animar la campana
    function animarCampana() {
        const bell = document.getElementById('bellIcon');
        if (bell) {
            bell.classList.add('animate__animated', 'animate__swing');
            setTimeout(() => {
                bell.classList.remove('animate__animated', 'animate__swing');
            }, 1000);
        }
    }
    
    // Obtener cookie (para CSRF token)
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    
    // Limpiar al cerrar/salir de la página
    window.addEventListener('beforeunload', function() {
        if (pollingInterval) {
            clearInterval(pollingInterval);
        }
    });
    
})();

