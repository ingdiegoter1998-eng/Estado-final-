/**
 * JavaScript para el modal de correspondencia de salida independiente.
 * Adaptado de responder-correspondencia.js
 */

// Variables globales para el estado (exponer en window para acceso global)
window.salidaContactosSeleccionados = null;
window.salidaEmailsSeleccionados = null;
let salidaContactosSeleccionados = window.salidaContactosSeleccionados;
let salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;

// Escuchar evento personalizado como respaldo (definido inmediatamente)
// Usar capture phase para asegurar que se capture el evento
document.addEventListener('agenda-contactos-seleccionados', function(e) {
    console.log('Evento agenda-contactos-seleccionados recibido:', e.detail);
    if (e.detail && e.detail.context === 'salida' && Array.isArray(e.detail.contactos)) {
        console.log('Procesando evento para salida:', e.detail.contactos);
        // Llamar directamente a la función si está disponible
        if (typeof window.modalCorrespondenciaSalidaAgregarContactos === 'function') {
            console.log('Llamando a modalCorrespondenciaSalidaAgregarContactos desde evento');
            window.modalCorrespondenciaSalidaAgregarContactos(e.detail.contactos);
        } else {
            console.warn('Función modalCorrespondenciaSalidaAgregarContactos no disponible, intentando agregar directamente');
            // Si la función no está disponible, agregar directamente
            const chipsContainer = document.getElementById('salida_chips_dest');
            const hiddenDest = document.getElementById('salida_hidden_dest_inputs');
            const contador = document.getElementById('salida_contador_chips');
            
            if (chipsContainer && hiddenDest && contador) {
                if (!window.salidaContactosSeleccionados) {
                    window.salidaContactosSeleccionados = new Map();
                }
                e.detail.contactos.forEach(contacto => {
                    if (contacto && contacto.id != null) {
                        const key = String(contacto.id);
                        window.salidaContactosSeleccionados.set(key, {
                            id: key,
                            nombre: contacto.nombre || 'Contacto sin nombre',
                            email: contacto.email || ''
                        });
                    }
                });
                actualizarChipsYHiddenInputsSalida(chipsContainer, hiddenDest, contador);
            }
        }
    }
}, true); // Usar capture phase

// Función global para agregar contactos desde el modal de agenda
window.modalCorrespondenciaSalidaAgregarContactos = function(contactos) {
    console.log('modalCorrespondenciaSalidaAgregarContactos llamado con:', contactos);
    
    // Obtener referencias a los elementos del DOM
    const chipsContainer = document.getElementById('salida_chips_dest');
    const hiddenDest = document.getElementById('salida_hidden_dest_inputs');
    const contador = document.getElementById('salida_contador_chips');
    
    if (!chipsContainer || !hiddenDest || !contador) {
        console.error('No se encontraron los elementos del DOM para agregar contactos');
        return;
    }
    
    // Inicializar Maps si no existen (usar las globales)
    if (!window.salidaContactosSeleccionados) {
        window.salidaContactosSeleccionados = new Map();
    }
    if (!window.salidaEmailsSeleccionados) {
        window.salidaEmailsSeleccionados = new Set();
    }
    // Sincronizar referencias locales
    salidaContactosSeleccionados = window.salidaContactosSeleccionados;
    salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
    
    if (!Array.isArray(contactos) || contactos.length === 0) {
        console.warn('No se recibieron contactos válidos');
        return;
    }
    
    contactos.forEach(contacto => {
        if (!contacto || contacto.id == null) {
            console.warn('Contacto inválido:', contacto);
            return;
        }
        const formEl = document.getElementById('formCorrespondenciaSalida');
        if (window.CorrespondenciaBlockedRecipients &&
            !window.CorrespondenciaBlockedRecipients.canAddContact(contacto, formEl)) {
            return;
        }
        const key = String(contacto.id);
        window.salidaContactosSeleccionados.set(key, {
            id: key,
            nombre: contacto.nombre || 'Contacto sin nombre',
            email: contacto.email || ''
        });
        // Sincronizar referencia local
        salidaContactosSeleccionados = window.salidaContactosSeleccionados;
    });
    
    console.log('Contactos seleccionados después de agregar:', Array.from(window.salidaContactosSeleccionados.entries()));
    
    // Actualizar la UI
    actualizarChipsYHiddenInputsSalida(chipsContainer, hiddenDest, contador);
};

function actualizarChipsYHiddenInputsSalida(chipsContainer, hiddenDest, contador) {
    if (!chipsContainer || !hiddenDest || !contador) return;
    // Usar la variable global
    const contactos = window.salidaContactosSeleccionados || salidaContactosSeleccionados;
    const emails = window.salidaEmailsSeleccionados || salidaEmailsSeleccionados;
    
    if (!contactos) {
        window.salidaContactosSeleccionados = new Map();
        salidaContactosSeleccionados = window.salidaContactosSeleccionados;
    }
    if (!emails) {
        window.salidaEmailsSeleccionados = new Set();
        salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
    }

    chipsContainer.innerHTML = '';
    hiddenDest.innerHTML = '';
    
    const contactosMap = window.salidaContactosSeleccionados || salidaContactosSeleccionados;
    const emailsSet = window.salidaEmailsSeleccionados || salidaEmailsSeleccionados;
    
    contactosMap.forEach((contacto, id) => {
        chipsContainer.innerHTML += `<span class="badge bg-primary me-1 mb-1">${contacto.nombre} <button type="button" class="btn-close btn-close-white ms-1" data-tipo="contacto" data-id="${id}"></button></span>`;
        hiddenDest.innerHTML += `<input type="hidden" name="destinatarios_contacto" value="${id}">`;
    });

    emailsSet.forEach(email => {
        chipsContainer.innerHTML += `<span class="badge bg-success me-1 mb-1">${email} <button type="button" class="btn-close btn-close-white ms-1" data-tipo="email" data-id="${email}"></button></span>`;
        hiddenDest.innerHTML += `<input type="hidden" name="destinatarios_email" value="${email}">`;
    });
    
    contador.textContent = contactosMap.size + emailsSet.size;
}

// Exponer la función globalmente
window.actualizarChipsYHiddenInputsSalida = actualizarChipsYHiddenInputsSalida;

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('formCorrespondenciaSalida');
    if (!form) return;

    const ADJUNTOS_UPLOAD_MAX_BYTES = parseInt(form.dataset.adjuntosUploadMaxBytes || '', 10) || (25 * 1024 * 1024);
    const ADJUNTOS_POSTMARK_MAX_BYTES = parseInt(form.dataset.adjuntosPostmarkMaxBytes || '', 10) || (10 * 1024 * 1024);
    const ENVIO_USA_POSTMARK = form.dataset.envioPostmark === '1';
    const ADJUNTOS_UPLOAD_MB = Math.round(ADJUNTOS_UPLOAD_MAX_BYTES / (1024 * 1024));
    const ADJUNTOS_POSTMARK_MB = Math.round(ADJUNTOS_POSTMARK_MAX_BYTES / (1024 * 1024));
    const ADJUNTOS_ERROR_CODES = new Set([
        'ADJUNTOS_SUPERAN_LIMITE_CARGA',
        'ADJUNTOS_SUPERAN_LIMITE',
        'ADJUNTOS_SUPERAN_25MB',
    ]);

    // Evitar reinicialización
    if (form.dataset.initialized === '1') return;
    form.dataset.initialized = '1';

    // --- Elementos del DOM ---
    // General
    const modalElement = document.getElementById('modalCorrespondenciaSalida');

    // Destinatarios manuales
    const buscadorInput = document.getElementById('salida_buscador_destinatarios');
    const resultadosDiv = document.getElementById('salida_sugerencias_dest');
    const chipsContainer = document.getElementById('salida_chips_dest');
    const hiddenDest = document.getElementById('salida_hidden_dest_inputs');
    const contador = document.getElementById('salida_contador_chips');
    const btnLimpiarChips = document.getElementById('salida_btn_limpiar_chips');
    const adjuntosInput = document.getElementById('salida_adjuntos');
    const adjuntosDriveAlert = document.getElementById('salidaAdjuntosDriveAlert');
    
    // Categorías
    const btnAbrirCategorias = document.getElementById('salida_btn_abrir_categorias');
    const categoriaIdInput = document.getElementById('salida_grupo_agenda_id');
    const categoriaWrap = document.getElementById('salida_categoria_seleccionada');
    const categoriaNombre = document.getElementById('salida_categoria_nombre');
    const categoriaCount = document.getElementById('salida_categoria_count');
    const btnQuitarCategoria = document.getElementById('salida_btn_quitar_categoria');
    const buscarCategoriaInput = document.getElementById('salida_buscar_categoria_input');
    const resultadosCategorias = document.getElementById('salida_resultados_categorias');
    const btnTextoCategoria = document.getElementById('salida_btn_texto_categoria');

    // --- Endpoints ---
    const salidaEndpoint = form.dataset.salidaEndpoint;
    const buscarContactosEndpoint = form.dataset.buscarContactosEndpoint;
    const buscarCategoriasEndpoint = form.dataset.buscarCategoriasEndpoint;
    const buscarEntidadesEndpoint = form.dataset.buscarEntidadesEndpoint;

    // --- Filtro por entidad ---
    const filtroEntidadSelect = document.getElementById('salida_filtro_entidad');
    let entidadSeleccionada = '';

    function cargarEntidadesSelect() {
        if (!filtroEntidadSelect || !buscarEntidadesEndpoint) return;
        fetch(buscarEntidadesEndpoint, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(res => res.json())
            .then(data => {
                if (data.success && Array.isArray(data.entidades)) {
                    filtroEntidadSelect.innerHTML = '<option value="">Todas las entidades</option>' +
                        data.entidades.map(ent => `<option value="${ent.id}">${ent.nombre}</option>`).join('');
                }
            })
            .catch(() => {
                filtroEntidadSelect.innerHTML = '<option value="">Todas las entidades</option>';
            });
    }

    function calcularTamanoTotalAdjuntos() {
        if (!adjuntosInput || !adjuntosInput.files) return 0;
        return Array.from(adjuntosInput.files).reduce((total, archivo) => total + (archivo.size || 0), 0);
    }

    function formatearTamano(bytes) {
        if (!bytes) return '0 MB';
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
    }

    function limpiarAlertaAdjuntosDrive() {
        if (!adjuntosDriveAlert) return;
        adjuntosDriveAlert.innerHTML = '';
        adjuntosDriveAlert.classList.remove('is-visible');
    }

    function mostrarAlertaAdjuntosDrive(totalBytes, mensajeBase) {
        if (!adjuntosDriveAlert) return;

        const mensaje = mensajeBase || `El tamaño total de adjuntos supera el límite de carga (máx. ${ADJUNTOS_UPLOAD_MB} MB).`;
        adjuntosDriveAlert.innerHTML = `
            <div class="d-flex flex-column gap-2">
                <div><strong>${mensaje}</strong></div>
                <div>Seleccionó aproximadamente <strong>${formatearTamano(totalBytes)}</strong>. Para continuar, cargue el archivo en su Drive personal, pegue el enlace en el cuerpo del correo y retire el archivo pesado del campo de adjuntos.</div>
                <div class="d-flex flex-wrap gap-2">
                    <button type="button" class="btn btn-sm btn-outline-danger" data-drive-tutorial-open>Ver tutorial paso a paso</button>
                </div>
            </div>`;
        adjuntosDriveAlert.classList.add('is-visible');

        const tutorialBtn = adjuntosDriveAlert.querySelector('[data-drive-tutorial-open]');
        if (tutorialBtn) {
            tutorialBtn.addEventListener('click', function() {
                if (typeof window.abrirTutorialAdjuntosDrive === 'function') {
                    window.abrirTutorialAdjuntosDrive();
                }
            });
        }
    }

    function validarTamanoAdjuntosSeleccionados() {
        const totalBytes = calcularTamanoTotalAdjuntos();
        if (totalBytes > ADJUNTOS_UPLOAD_MAX_BYTES) {
            mostrarAlertaAdjuntosDrive(
                totalBytes,
                `El tamaño total de adjuntos supera el límite de carga (máx. ${ADJUNTOS_UPLOAD_MB} MB).`
            );
            return false;
        }
        if (ENVIO_USA_POSTMARK && totalBytes > ADJUNTOS_POSTMARK_MAX_BYTES) {
            mostrarAlertaAdjuntosDrive(
                totalBytes,
                `Los adjuntos superan el límite de Postmark (máx. ${ADJUNTOS_POSTMARK_MB} MB). Puede cargarlos, pero el envío será rechazado hasta reducirlos o usar enlace Drive.`
            );
            return true;
        }
        limpiarAlertaAdjuntosDrive();
        return true;
    }

    function esErrorTamanoAdjuntos(data) {
        return !!(data && (
            ADJUNTOS_ERROR_CODES.has(data.error_code) ||
            /l[ií]mite de carga/i.test(data.error || '') ||
            /Postmark/i.test(data.error || '') ||
            /supera\s*(25|10)\s*mb/i.test(data.error || '')
        ));
    }

    if (filtroEntidadSelect) {
        cargarEntidadesSelect();
        // El filtro de entidad ya no es necesario sin el buscador manual
        // filtroEntidadSelect.addEventListener('change', function() {
        //     entidadSeleccionada = this.value;
        //     const query = buscadorInput ? buscadorInput.value.trim() : '';
        //     if (query.length >= 2) {
        //         buscarContactosManuales(query);
        //     }
        // });
    }

    if (adjuntosInput) {
        adjuntosInput.addEventListener('change', validarTamanoAdjuntosSeleccionados);
    }

    // --- Estado ---
    let categoriaSeleccionada = null;
    // Usar las variables globales si existen, sino crear nuevas
    if (!window.salidaContactosSeleccionados) {
        window.salidaContactosSeleccionados = new Map(); // Usar Map para guardar más datos {id, nombre, email}
    }
    if (!window.salidaEmailsSeleccionados) {
        window.salidaEmailsSeleccionados = new Set();
    }
    // Sincronizar referencias locales con las globales
    salidaContactosSeleccionados = window.salidaContactosSeleccionados;
    salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
    // Referencias locales para facilitar el código
    let contactosSeleccionados = salidaContactosSeleccionados;
    let emailsSeleccionados = salidaEmailsSeleccionados;

    // =================================================================
    // LÓGICA DE CATEGORÍAS (GRUPOS)
    // =================================================================
    
    function resetCategoriasUI() {
        categoriaSeleccionada = null;
        if(categoriaIdInput) categoriaIdInput.value = '';
        if(categoriaWrap) categoriaWrap.style.display = 'none';
        if(btnTextoCategoria) btnTextoCategoria.textContent = 'Seleccionar categoría';
        if(btnAbrirCategorias) {
            btnAbrirCategorias.classList.remove('btn-success', 'text-white');
            btnAbrirCategorias.classList.add('btn-outline-warning');
        }
    }

    function fetchCategorias(query = '') {
        const url = `${buscarCategoriasEndpoint}?q=${encodeURIComponent(query)}`;
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(res => res.json())
            .then(data => {
                if (data.success && resultadosCategorias) {
                    resultadosCategorias.innerHTML = data.categorias.length ? 
                        data.categorias.map(cat => `
                            <a href="#" class="list-group-item list-group-item-action categoria-item" data-id="${cat.id}" data-nombre="${cat.nombre}" data-total="${cat.contactos_count}">
                                <strong>${cat.nombre}</strong><br>
                                <small class="text-muted">${cat.contactos_count} contactos</small>
                            </a>
                        `).join('') : '<p class="text-muted p-2">No se encontraron categorías.</p>';
                }
            })
            .catch(() => { if(resultadosCategorias) resultadosCategorias.innerHTML = '<p class="text-danger p-2">Error al cargar.</p>'; });
    }

    if(btnAbrirCategorias) {
        btnAbrirCategorias.addEventListener('shown.bs.dropdown', () => {
            fetchCategorias();
            if(buscarCategoriaInput) buscarCategoriaInput.focus();
        });
    }

    if(buscarCategoriaInput) {
        buscarCategoriaInput.addEventListener('input', debounce(() => fetchCategorias(buscarCategoriaInput.value), 300));
    }

    if(resultadosCategorias) {
        resultadosCategorias.addEventListener('click', e => {
            e.preventDefault();
            const item = e.target.closest('.categoria-item');
            if (item) {
                categoriaSeleccionada = { id: item.dataset.id, nombre: item.dataset.nombre, total: item.dataset.total };
                if(categoriaIdInput) categoriaIdInput.value = categoriaSeleccionada.id;
                if(categoriaNombre) categoriaNombre.textContent = categoriaSeleccionada.nombre;
                if(categoriaCount) categoriaCount.textContent = `${categoriaSeleccionada.total} contactos`;
                if(categoriaWrap) categoriaWrap.style.display = 'block';
                if(btnTextoCategoria) btnTextoCategoria.textContent = categoriaSeleccionada.nombre;
                if(btnAbrirCategorias) {
                    btnAbrirCategorias.classList.remove('btn-outline-warning');
                    btnAbrirCategorias.classList.add('btn-success', 'text-white');
                    bootstrap.Dropdown.getInstance(btnAbrirCategorias).hide();
                }
                limpiarDestinatariosManuales();
            }
        });
    }

    if(btnQuitarCategoria) btnQuitarCategoria.addEventListener('click', resetCategoriasUI);

    // =================================================================
    // LÓGICA DE DESTINATARIOS MANUALES
    // =================================================================

    function limpiarDestinatariosManuales() {
        window.salidaContactosSeleccionados.clear();
        window.salidaEmailsSeleccionados.clear();
        // Sincronizar referencias locales
        salidaContactosSeleccionados = window.salidaContactosSeleccionados;
        salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
        contactosSeleccionados = salidaContactosSeleccionados;
        emailsSeleccionados = salidaEmailsSeleccionados;
        actualizarChipsYHiddenInputs();
    }
    
    function actualizarChipsYHiddenInputs() {
        actualizarChipsYHiddenInputsSalida(chipsContainer, hiddenDest, contador);
    }

    function buildContactosUrl(query) {
        if (!buscarContactosEndpoint) return null;
        const params = new URLSearchParams({ q: query });
        if (entidadSeleccionada) {
            params.append('entidad_id', entidadSeleccionada);
        }
        return `${buscarContactosEndpoint}?${params.toString()}`;
    }

    function buscarContactosManuales(query) {
        const url = buildContactosUrl(query);
        if (!url || !resultadosDiv) return;
        fetch(url, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    resultadosDiv.innerHTML = data.contactos.length ?
                        data.contactos.map(c => `
                            <a href="#" class="list-group-item list-group-item-action contacto-item" data-id="${c.id}" data-nombre="${c.nombre_completo}" data-email="${c.email || ''}">
                                <strong>${c.nombre_completo}</strong><br>
                                <small>${c.email || 'Sin email'}</small>
                                ${c.entidad ? `<br><small class="text-muted">${c.entidad}</small>` : ''}
                            </a>`).join('')
                        : '<p class="text-muted p-2">No hay resultados.</p>';
                    resultadosDiv.style.display = 'block';
                }
            });
    }

    if(buscadorInput) {
        buscadorInput.addEventListener('input', debounce(() => {
            const query = buscadorInput.value.trim();
            if (query.length < 2) {
                if(resultadosDiv) resultadosDiv.style.display = 'none';
                return;
            }
            buscarContactosManuales(query);
        }, 300));

        buscadorInput.addEventListener('keydown', e => {
            if (e.key === 'Enter') {
                e.preventDefault();
                const value = buscadorInput.value.trim();
                if (value.includes('@')) {
                    if (window.CorrespondenciaBlockedRecipients &&
                        !window.CorrespondenciaBlockedRecipients.canAddRecipient(value, form)) {
                        return;
                    }
                    window.salidaEmailsSeleccionados.add(value);
                    // Sincronizar referencia local
                    salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
                    emailsSeleccionados = salidaEmailsSeleccionados;
                    actualizarChipsYHiddenInputs();
                    buscadorInput.value = '';
                    if(resultadosDiv) resultadosDiv.style.display = 'none';
                    resetCategoriasUI();
                }
            }
        });
    }

    if(resultadosDiv) {
        resultadosDiv.addEventListener('click', e => {
            e.preventDefault();
            const item = e.target.closest('.contacto-item');
            if (item) {
                const contacto = { id: item.dataset.id, nombre: item.dataset.nombre, email: item.dataset.email };
                if (window.CorrespondenciaBlockedRecipients &&
                    !window.CorrespondenciaBlockedRecipients.canAddContact(contacto, form)) {
                    return;
                }
                window.salidaContactosSeleccionados.set(contacto.id, contacto);
                // Sincronizar referencia local
                salidaContactosSeleccionados = window.salidaContactosSeleccionados;
                contactosSeleccionados = salidaContactosSeleccionados;
                actualizarChipsYHiddenInputs();
                buscadorInput.value = '';
                resultadosDiv.style.display = 'none';
                resetCategoriasUI();
            }
        });
    }
    
    if(chipsContainer) {
        chipsContainer.addEventListener('click', e => {
            if (e.target.matches('.btn-close')) {
                const tipo = e.target.dataset.tipo;
                const id = e.target.dataset.id;
                if (tipo === 'contacto') {
                    window.salidaContactosSeleccionados.delete(id);
                    salidaContactosSeleccionados = window.salidaContactosSeleccionados;
                    contactosSeleccionados = salidaContactosSeleccionados;
                }
                if (tipo === 'email') {
                    window.salidaEmailsSeleccionados.delete(id);
                    salidaEmailsSeleccionados = window.salidaEmailsSeleccionados;
                    emailsSeleccionados = salidaEmailsSeleccionados;
                }
                actualizarChipsYHiddenInputs();
            }
        });
    }

    if(btnLimpiarChips) btnLimpiarChips.addEventListener('click', limpiarDestinatariosManuales);

    // Ocultar sugerencias si se hace clic fuera (ya no necesario sin buscador)
    // document.addEventListener('click', (e) => {
    //     if (resultadosDiv && !resultadosDiv.contains(e.target) && e.target !== buscadorInput) {
    //         resultadosDiv.style.display = 'none';
    //     }
    // });

    // La función ya está definida globalmente arriba, solo actualizamos la UI local
    const originalAgregarContactos = window.modalCorrespondenciaSalidaAgregarContactos;
    window.modalCorrespondenciaSalidaAgregarContactos = function(contactos) {
        originalAgregarContactos(contactos);
        // Actualizar UI local si los elementos existen
        if (chipsContainer && hiddenDest && contador) {
            actualizarChipsYHiddenInputs();
        }
    };

    // El listener de eventos ya está definido globalmente arriba

    // =================================================================
    // ENVÍO DEL FORMULARIO
    // =================================================================

    form.addEventListener('submit', function(e) {
        e.preventDefault();
        if (form.dataset.submitting === '1') return;

        const tieneCategoria = categoriaIdInput && categoriaIdInput.value;
        const contactosMap = window.salidaContactosSeleccionados || new Map();
        const emailsSet = window.salidaEmailsSeleccionados || new Set();
        const tieneDestinatarios = contactosMap.size > 0 || emailsSet.size > 0;

        if (!tieneCategoria && !tieneDestinatarios) {
            if (window.showWarning) {
                showWarning('Debe seleccionar al menos un destinatario o una categoría.');
            } else {
            alert('Debe seleccionar al menos un destinatario o una categoría.');
            }
            return;
        }

        if (window.CorrespondenciaBlockedRecipients) {
            const bloqueados = window.CorrespondenciaBlockedRecipients.findBlockedInSelection(
                contactosMap, emailsSet, form
            );
            if (bloqueados.length) {
                window.CorrespondenciaBlockedRecipients.notifyBlocked(bloqueados[0], window.CorrespondenciaBlockedRecipients.readConfig(form));
                return;
            }
        }

        if (!validarTamanoAdjuntosSeleccionados()) {
            if (typeof window.showWarning === 'function') {
                window.showWarning(`Los adjuntos superan el límite de carga (${ADJUNTOS_UPLOAD_MB} MB). Revise la guía para enviarlos por Drive personal.`);
            }
            return;
        }
        
        form.dataset.submitting = '1';
        const submitBtn = form.querySelector('button[type="submit"]');
        if(submitBtn) submitBtn.disabled = true;

        const formData = new FormData(form);
        fetch(salidaEndpoint, {
            method: 'POST',
            body: formData,
            headers: { 'X-Requested-With': 'XMLHttpRequest' }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Error en la respuesta del servidor');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                // Intentar usar toast personalizado
                const successMsg = data.message || 'Operación exitosa.';
                if (typeof window.showSuccess === 'function') {
                    window.showSuccess(successMsg);
                } else if (typeof showSuccess === 'function') {
                    showSuccess(successMsg);
                } else {
                    console.warn('showSuccess no disponible, usando alert como fallback');
                    alert(successMsg);
                }
                if(modalElement) bootstrap.Modal.getInstance(modalElement).hide();
                setTimeout(() => window.location.reload(), 1500);
            } else {
                // Intentar usar toast de error
                const errorMsg = 'Error: ' + (data.error || 'Ocurrió un error desconocido.');
                if (esErrorTamanoAdjuntos(data)) {
                    mostrarAlertaAdjuntosDrive(calcularTamanoTotalAdjuntos(), data.error);
                }
                if (typeof window.showError === 'function') {
                    window.showError(errorMsg);
                } else if (typeof showError === 'function') {
                    showError(errorMsg);
                } else {
                    console.warn('showError no disponible, usando alert como fallback');
                    alert(errorMsg);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            const errorMsg = 'Error de conexión al enviar el formulario. Por favor, intente nuevamente.';
            if (typeof window.showError === 'function') {
                window.showError(errorMsg);
            } else if (typeof showError === 'function') {
                showError(errorMsg);
            } else {
                console.warn('showError no disponible, usando alert como fallback');
            alert('Error de conexión al enviar el formulario.');
            }
        })
        .finally(() => {
            form.dataset.submitting = '0';
            if(submitBtn) submitBtn.disabled = false;
        });
    });

    // =================================================================
    // UTILIDADES
    // =================================================================
    function debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
});
