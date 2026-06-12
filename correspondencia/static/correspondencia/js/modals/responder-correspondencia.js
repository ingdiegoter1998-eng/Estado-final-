/**
 * JavaScript para el modal de responder correspondencia
 * Incluye funcionalidad para seleccionar categorías (grupos de agenda)
 */

// Variables globales para el estado
let respuestaContactosSeleccionados = null;
let respuestaEmailsSeleccionados = null;

// Agregar remitente original sin depender del init del modal
window.agregarRemitenteOriginalDesdeBoton = function(btn) {
    if (!btn || !btn.dataset) return;
    const id = parseInt(btn.dataset.id, 10);
    const nombre = btn.dataset.nombre;
    const email = btn.dataset.email || '';

    if (!id || !nombre) return;

    // Si la función global existe, usarla
    if (typeof window.seleccionarDestinatario === 'function') {
        window.seleccionarDestinatario(id, nombre, email, 'contacto');
        return;
    }

    // Fallback: agregar directamente y actualizar chips
    if (!respuestaContactosSeleccionados) respuestaContactosSeleccionados = new Map();
    if (!respuestaEmailsSeleccionados) respuestaEmailsSeleccionados = new Set();
    respuestaContactosSeleccionados.set(id, { nombre: nombre, email: email });

    const chipsContainer = document.getElementById('chips_dest');
    const hiddenDest = document.getElementById('hidden_dest_inputs');
    const contador = document.getElementById('contador-chips');
    if (chipsContainer && hiddenDest && contador) {
        actualizarChipsDestinatariosRespuesta(chipsContainer, hiddenDest, contador);
    }
};

// Escuchar evento personalizado como respaldo (definido inmediatamente)
// Usar capture phase para asegurar que se capture el evento
document.addEventListener('agenda-contactos-seleccionados', function(e) {
    console.log('Evento agenda-contactos-seleccionados recibido:', e.detail);
    if (e.detail && e.detail.context === 'respuesta' && Array.isArray(e.detail.contactos)) {
        console.log('Procesando evento para respuesta:', e.detail.contactos);
        // Llamar directamente a la función si está disponible
        if (typeof window.modalRespuestaAgregarContactos === 'function') {
            console.log('Llamando a modalRespuestaAgregarContactos desde evento');
            window.modalRespuestaAgregarContactos(e.detail.contactos);
        } else {
            console.warn('Función modalRespuestaAgregarContactos no disponible, intentando agregar directamente');
            // Si la función no está disponible, agregar directamente
            const chipsContainer = document.getElementById('chips_dest');
            const hiddenDest = document.getElementById('hidden_dest_inputs');
            const contador = document.getElementById('contador-chips');
            
            if (chipsContainer && hiddenDest && contador) {
                if (!respuestaContactosSeleccionados) {
                    respuestaContactosSeleccionados = new Map();
                }
                e.detail.contactos.forEach(contacto => {
                    if (contacto && contacto.id != null) {
                        const id = parseInt(contacto.id, 10);
                        if (!isNaN(id)) {
                            respuestaContactosSeleccionados.set(id, {
                                nombre: contacto.nombre || 'Contacto sin nombre',
                                email: contacto.email || ''
                            });
                        }
                    }
                });
                actualizarChipsDestinatariosRespuesta(chipsContainer, hiddenDest, contador);
            }
        }
    }
}, true); // Usar capture phase

// Función global para agregar contactos desde el modal de agenda
window.modalRespuestaAgregarContactos = function(contactos) {
    console.log('modalRespuestaAgregarContactos llamado con:', contactos);
    
    if (!Array.isArray(contactos) || contactos.length === 0) {
        console.warn('No se recibieron contactos válidos');
        return;
    }
    
    // Inicializar Maps si no existen
    if (!respuestaContactosSeleccionados) {
        respuestaContactosSeleccionados = new Map();
    }
    if (!respuestaEmailsSeleccionados) {
        respuestaEmailsSeleccionados = new Set();
    }
    
    contactos.forEach(contacto => {
        if (!contacto || contacto.id == null) {
            console.warn('Contacto inválido:', contacto);
            return;
        }
        // Convertir ID a número porque contactosSeleccionados usa números como clave
        const id = parseInt(contacto.id, 10);
        if (isNaN(id)) {
            console.warn('ID de contacto inválido:', contacto.id);
            return;
        }
        console.log('Agregando contacto:', { id, nombre: contacto.nombre, email: contacto.email });
        
        const formEl = document.getElementById('formResponderCorrespondencia');
        if (window.CorrespondenciaBlockedRecipients &&
            !window.CorrespondenciaBlockedRecipients.canAddContact(contacto, formEl)) {
            return;
        }

        // Usar la función global seleccionarDestinatario si existe, sino agregar directamente
        if (typeof window.seleccionarDestinatario === 'function') {
            window.seleccionarDestinatario(id, contacto.nombre || 'Contacto sin nombre', contacto.email || '', 'contacto');
        } else {
            // Agregar directamente al Map
            respuestaContactosSeleccionados.set(id, {
                nombre: contacto.nombre || 'Contacto sin nombre',
                email: contacto.email || ''
            });
            // Intentar actualizar la UI
            const chipsContainer = document.getElementById('chips_dest');
            const hiddenDest = document.getElementById('hidden_dest_inputs');
            const contador = document.getElementById('contador-chips');
            if (chipsContainer && hiddenDest && contador) {
                actualizarChipsDestinatariosRespuesta(chipsContainer, hiddenDest, contador);
            }
        }
    });
    console.log('Contactos seleccionados después de agregar:', Array.from(respuestaContactosSeleccionados.entries()));
};

function actualizarChipsDestinatariosRespuesta(chipsContainer, hiddenDest, contador) {
    if (!chipsContainer || !hiddenDest || !contador) return;
    if (!respuestaContactosSeleccionados) respuestaContactosSeleccionados = new Map();
    if (!respuestaEmailsSeleccionados) respuestaEmailsSeleccionados = new Set();

    chipsContainer.innerHTML = '';
    hiddenDest.innerHTML = '';

    respuestaContactosSeleccionados.forEach((contacto, id) => {
        const chip = document.createElement('span');
        chip.className = 'badge bg-primary me-2 mb-2';
        chip.innerHTML = `${contacto.nombre} <button type="button" class="btn-close btn-close-white ms-1" onclick="quitarDestinatario(${id}, 'contacto')"></button>`;
        chipsContainer.appendChild(chip);

        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'destinatarios_contacto';
        hidden.value = id;
        hiddenDest.appendChild(hidden);
    });

    respuestaEmailsSeleccionados.forEach(email => {
        const chip = document.createElement('span');
        chip.className = 'badge bg-success me-2 mb-2';
        chip.innerHTML = `${email} <button type="button" class="btn-close btn-close-white ms-1" onclick="quitarDestinatario('${email}', 'email')"></button>`;
        chipsContainer.appendChild(chip);

        const hidden = document.createElement('input');
        hidden.type = 'hidden';
        hidden.name = 'destinatarios_email';
        hidden.value = email;
        hiddenDest.appendChild(hidden);
    });

    const total = respuestaContactosSeleccionados.size + respuestaEmailsSeleccionados.size;
    contador.textContent = total;
}

function inicializarNuevoModalResponder() {
    const form = document.getElementById('formResponderCorrespondencia');
    if (!form) {
        return;
    }
    const esRespuestaDiscrecional = form.dataset.esRespuestaDiscrecional === '1';

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

    // #region agent log
    fetch('http://localhost:7242/ingest/c9ff4165-5596-432d-8ee8-9d3aa5b2d1d2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'responder-correspondencia.js:142',message:'init modal responder',data:{hasForm:!!form,formId:form.id},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H1'})}).catch(()=>{});
    // #endregion

    // Evitar inicializaciones múltiples (que causan doble submit)
    if (form.dataset.initialized === '1') {
        return;
    }
    form.dataset.initialized = '1';

    // Elementos del formulario principal
    const buscadorInput = document.getElementById('buscador_destinatarios');
    const resultadosDiv = document.getElementById('sugerencias_dest');
    const chipsContainer = document.getElementById('chips_dest');
    const hiddenDest = document.getElementById('hidden_dest_inputs');
    const contador = document.getElementById('contador-chips');
    const btnBuscarDest = document.getElementById('btn-buscar-dest');
    const adjuntosInput = document.getElementById('adjuntos_respuesta');
    const adjuntosDriveAlert = document.getElementById('respuestaAdjuntosDriveAlert');
    
    // Elementos de categorías
    const btnAbrirCategorias = document.getElementById('btn-abrir-categorias');
    const categoriaIdInput = document.getElementById('grupo_agenda_id');
    const categoriaWrap = document.getElementById('categoria-seleccionada');
    const categoriaNombre = document.getElementById('categoria-nombre');
    const categoriaCount = document.getElementById('categoria-count');
    const btnQuitarCategoria = document.getElementById('btn-quitar-categoria');
    
    // Elementos del dropdown de categorías
    const dropdownCategorias = document.getElementById('dropdown-categorias');
    const buscarCategoriaInput = document.getElementById('buscar_categoria_input');
    const btnBuscarCategoria = document.getElementById('btn-buscar-categoria');
    const resultadosCategorias = document.getElementById('resultados_categorias');
    

    
    // Endpoints
    const buscarCategoriasEndpoint = form.dataset.buscarCategoriasEndpoint || '';
    const categoriaDetalleEndpoint = form.dataset.categoriaDetalleEndpoint || '';
    const buscarContactosEndpoint = form.dataset.buscarContactosEndpoint || '';
    const buscarGruposEndpoint = form.dataset.buscarGruposEndpoint || '';
    const grupoDetalleEndpointTpl = form.dataset.grupoDetalleEndpoint || '';
    const buscarEntidadesEndpoint = form.dataset.buscarEntidadesEndpoint || '';

    const filtroEntidadSelect = document.getElementById('filtro_entidad_respuesta');
    let entidadSeleccionada = '';

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
        adjuntosDriveAlert.classList.add('d-none');
    }

    function mostrarAlertaAdjuntosDrive(totalBytes, mensajeBase) {
        if (!adjuntosDriveAlert) return;

        const mensaje = mensajeBase || `El tamaño total de adjuntos supera el límite de carga (máx. ${ADJUNTOS_UPLOAD_MB} MB).`;
        adjuntosDriveAlert.innerHTML = `
            <div class="d-flex flex-column gap-2">
                <div><strong>${mensaje}</strong></div>
                <div>Seleccionó aproximadamente <strong>${formatearTamano(totalBytes)}</strong>. Para enviar esta respuesta, suba el archivo a su Drive personal, pegue el enlace en el cuerpo del mensaje y quite el archivo pesado del adjunto.</div>
                <div>
                    <button type="button" class="btn btn-sm btn-outline-warning bg-white" data-drive-tutorial-open>Ver tutorial paso a paso</button>
                </div>
            </div>`;
        adjuntosDriveAlert.classList.remove('d-none');

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

    function cargarEntidadesAgenda(selectEl, endpoint) {
        if (!selectEl || !endpoint) return;
        fetch(endpoint, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
            .then(res => res.json())
            .then(data => {
                if (data.success) {
                    selectEl.innerHTML = '<option value="">Todas las entidades</option>' +
                        data.entidades.map(ent => `<option value="${ent.id}">${ent.nombre}</option>`).join('');
                }
            })
            .catch(() => {
                selectEl.innerHTML = '<option value="">Todas las entidades</option>';
            });
    }

    if (filtroEntidadSelect && buscarEntidadesEndpoint) {
        cargarEntidadesAgenda(filtroEntidadSelect, buscarEntidadesEndpoint);
        filtroEntidadSelect.addEventListener('change', function() {
            entidadSeleccionada = this.value;
            const current = buscadorInput ? buscadorInput.value.trim() : '';
            if (current.length >= 2) {
                buscarDestinatarios();
            }
        });
    }

    if (adjuntosInput) {
        adjuntosInput.addEventListener('change', validarTamanoAdjuntosSeleccionados);
    }

    let categoriaSeleccionada = null;
    // Usar las variables globales si existen, sino crear nuevas
    if (!respuestaContactosSeleccionados) {
        respuestaContactosSeleccionados = new Map(); // Cambiado a Map para guardar {id: {nombre, email}}
    }
    if (!respuestaEmailsSeleccionados) {
        respuestaEmailsSeleccionados = new Set();
    }
    // Referencias locales para facilitar el código
    const contactosSeleccionados = respuestaContactosSeleccionados;
    const emailsSeleccionados = respuestaEmailsSeleccionados;

    // ===== FUNCIONES DE CATEGORÍAS =====

    // Inicializar dropdown de categorías
    if (btnAbrirCategorias && dropdownCategorias) {
        // Cuando se abre el dropdown, cargar categorías y enfocar el campo de búsqueda
        btnAbrirCategorias.addEventListener('click', function() {
            setTimeout(() => {
                if (buscarCategoriaInput) {
                    buscarCategoriaInput.focus();
                }
                // Cargar todas las categorías al abrir el dropdown
                cargarTodasLasCategorias();
            }, 100);
        });
    }

    // Buscar categorías
    if (btnBuscarCategoria) {
        btnBuscarCategoria.addEventListener('click', buscarCategorias);
    }
    if (buscarCategoriaInput) {
        // Búsqueda en tiempo real mientras el usuario escribe
        buscarCategoriaInput.addEventListener('input', debounce(buscarCategorias, 300));
        
        // También buscar al presionar Enter
        buscarCategoriaInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                buscarCategorias();
            }
        });
    }

    function cargarTodasLasCategorias() {
        fetch(`${buscarCategoriasEndpoint}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mostrarResultadosCategorias(data.categorias);
                } else {
                    mostrarResultadosCategorias([]);
                }
            })
            .catch(error => {
                console.error('Error cargando categorías:', error);
                mostrarResultadosCategorias([]);
            });
    }

    function buscarCategorias() {
        const query = buscarCategoriaInput.value.trim();
        if (query.length < 2) {
            // Si la búsqueda está vacía, mostrar todas las categorías
            cargarTodasLasCategorias();
            return;
        }

        fetch(`${buscarCategoriasEndpoint}?q=${encodeURIComponent(query)}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mostrarResultadosCategorias(data.categorias);
                } else {
                    mostrarResultadosCategorias([]);
                }
            })
            .catch(error => {
                console.error('Error buscando categorías:', error);
                mostrarResultadosCategorias([]);
            });
    }

    function mostrarResultadosCategorias(categorias) {
        if (!resultadosCategorias) return;

        if (categorias.length === 0) {
            resultadosCategorias.innerHTML = '<p class="text-muted">No se encontraron categorías</p>';
            return;
        }

        const html = categorias.map(cat => `
            <div class="list-group-item list-group-item-action categoria-item" data-id="${cat.id}" style="cursor: pointer;">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <strong>${cat.nombre}</strong>
                        ${cat.descripcion ? `<br><small class="text-muted">${cat.descripcion}</small>` : ''}
                    </div>
                    <div class="text-end">
                        <span class="badge bg-secondary">${cat.contactos_count} contactos</span>
                        <button type="button" class="btn btn-sm btn-outline-success ms-2" onclick="seleccionarCategoria(${cat.id}, '${cat.nombre}', ${cat.contactos_count})">
                            Seleccionar
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

        resultadosCategorias.innerHTML = html;
    }

    // Función global para seleccionar categoría
    window.seleccionarCategoria = function(categoriaId, nombre, contactosCount) {
        categoriaSeleccionada = {
            id: categoriaId,
            nombre: nombre,
            contactos_count: contactosCount
        };
        
        // Actualizar el input hidden
        if (categoriaIdInput) {
            categoriaIdInput.value = categoriaId;
        }
        
        // Mostrar la categoría seleccionada
        if (categoriaNombre) {
            categoriaNombre.textContent = nombre;
        }
        if (categoriaCount) {
            categoriaCount.textContent = contactosCount + ' contactos';
        }
        if (categoriaWrap) {
            categoriaWrap.style.display = 'block';
        }
        
        // Actualizar el enlace del botón de ver detalles
        const btnVerDetalle = document.getElementById('btn-ver-detalle-categoria');
        if (btnVerDetalle) {
            btnVerDetalle.href = `/registros/correspondencia/categorias/${categoriaId}/detalle/`;
        }
        
        // Actualizar el texto del botón
        const btnTexto = document.getElementById('btn-texto-categoria');
        if (btnTexto) {
            btnTexto.textContent = nombre;
        }
        
        // Cambiar el estilo del botón
        if (btnAbrirCategorias) {
            btnAbrirCategorias.classList.remove('btn-outline-warning');
            btnAbrirCategorias.classList.add('btn-success', 'text-white');
        }
        
        // Cerrar el dropdown
        const dropdown = bootstrap.Dropdown.getInstance(btnAbrirCategorias);
        if (dropdown) {
            dropdown.hide();
        }
        
        // Limpiar la búsqueda
        if (buscarCategoriaInput) {
            buscarCategoriaInput.value = '';
        }
        if (resultadosCategorias) {
            resultadosCategorias.innerHTML = '';
        }
    };



    // Quitar categoría seleccionada
    if (btnQuitarCategoria) {
        btnQuitarCategoria.addEventListener('click', function() {
            categoriaSeleccionada = null;
            
            // Limpiar el input hidden
            if (categoriaIdInput) {
                categoriaIdInput.value = '';
            }
            
            // Ocultar la categoría seleccionada
            if (categoriaWrap) {
                categoriaWrap.style.display = 'none';
            }
            
            // Limpiar el enlace del botón de ver detalles
            const btnVerDetalle = document.getElementById('btn-ver-detalle-categoria');
            if (btnVerDetalle) {
                btnVerDetalle.href = '#';
            }
        });
    }

    // ===== FUNCIONES DE DESTINATARIOS MANUALES =====

    // Búsqueda de contactos y grupos
    if (buscadorInput) {
        buscadorInput.addEventListener('input', debounce(buscarDestinatarios, 300));
        buscadorInput.addEventListener('keydown', function(e) {
            if (e.key === 'Enter') {
                e.preventDefault();
                // Permitir agregar email manual
                const valor = this.value.trim();
                if (valor.includes('@')) {
                    agregarEmail(valor);
                    this.value = '';
                } else {
                    buscarDestinatarios();
                }
            }
        });
    }
    if (btnBuscarDest) {
        btnBuscarDest.addEventListener('click', function() {
            buscarDestinatarios();
        });
    }

    function buildContactosUrl(query) {
        const params = new URLSearchParams({ q: query });
        if (entidadSeleccionada) {
            params.append('entidad_id', entidadSeleccionada);
        }
        return `${buscarContactosEndpoint}?${params.toString()}`;
    }

    function buscarDestinatarios() {
        const query = buscadorInput.value.trim();
        if (query.length < 2) {
            mostrarResultados([]);
            return;
        }

        fetch(buildContactosUrl(query), {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    mostrarResultados(data.contactos);
                } else {
                    mostrarResultados([]);
                }
            })
            .catch(error => {
                console.error('Error buscando contactos:', error);
                mostrarResultados([]);
            });
    }

    function mostrarResultados(resultados) {
        if (!resultadosDiv) return;

        if (resultados.length === 0) {
            resultadosDiv.innerHTML = '<p class="text-muted m-2">No se encontraron resultados</p>';
            resultadosDiv.style.display = 'block';
            return;
        }

        const html = resultados.map(item => `
            <div class="resultado-item list-group-item list-group-item-action" onclick="seleccionarDestinatario(${item.id}, '${item.nombre_completo}', '${item.email}', 'contacto')" style="cursor:pointer;">
                <strong>${item.nombre_completo}</strong>
                <br><small class="text-muted">${item.email}</small>
                ${item.entidad ? `<br><small class="text-muted">${item.entidad}</small>` : ''}
            </div>
        `).join('');

        resultadosDiv.innerHTML = html;
        resultadosDiv.style.display = 'block';
    }

    // Función global para seleccionar destinatario
    window.seleccionarDestinatario = function(id, nombre, email, tipo) {
        if (tipo === 'contacto') {
            if (window.CorrespondenciaBlockedRecipients &&
                !window.CorrespondenciaBlockedRecipients.canAddRecipient(email, form)) {
                return;
            }
            contactosSeleccionados.set(id, {nombre: nombre, email: email});
        } else if (tipo === 'email') {
            if (window.CorrespondenciaBlockedRecipients &&
                !window.CorrespondenciaBlockedRecipients.canAddRecipient(email, form)) {
                return;
            }
            emailsSeleccionados.add(email);
        }
        
        actualizarChipsDestinatarios();
        if (resultadosDiv) resultadosDiv.style.display = 'none';
        if (buscadorInput) buscadorInput.value = '';
    };

    function agregarEmail(email) {
        if (window.CorrespondenciaBlockedRecipients &&
            !window.CorrespondenciaBlockedRecipients.canAddRecipient(email, form)) {
            return;
        }
        emailsSeleccionados.add(email);
        actualizarChipsDestinatarios();
    }

    function actualizarChipsDestinatarios() {
        actualizarChipsDestinatariosRespuesta(chipsContainer, hiddenDest, contador);
    }

    // Función global para quitar destinatario
    window.quitarDestinatario = function(id, tipo) {
        if (tipo === 'contacto') {
            contactosSeleccionados.delete(parseInt(id)); // Convertir a número para coincidir con la clave del Map
        } else if (tipo === 'email') {
            emailsSeleccionados.delete(id);
        }
        actualizarChipsDestinatarios();
    };

    // Botón limpiar chips - usar delegación de eventos para mayor confiabilidad
    document.addEventListener('click', function(e) {
        if (e.target && e.target.id === 'btn-limpiar-chips') {
            contactosSeleccionados.clear();
            emailsSeleccionados.clear();
            actualizarChipsDestinatarios();
        }
    });

    // Botón agregar remitente original como destinatario
    const btnAgregarRemitente = document.getElementById('btn-agregar-remitente-original');
    // #region agent log
    fetch('http://localhost:7242/ingest/c9ff4165-5596-432d-8ee8-9d3aa5b2d1d2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'responder-correspondencia.js:536',message:'btn remitente lookup',data:{found:!!btnAgregarRemitente},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H2'})}).catch(()=>{});
    // #endregion
    if (btnAgregarRemitente) {
        btnAgregarRemitente.addEventListener('click', function() {
            // #region agent log
            fetch('http://localhost:7242/ingest/c9ff4165-5596-432d-8ee8-9d3aa5b2d1d2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'responder-correspondencia.js:539',message:'btn remitente click',data:{hasDataset:!!this.dataset,hasId:!!this.dataset.id,hasNombre:!!this.dataset.nombre,contactsSize:contactosSeleccionados ? contactosSeleccionados.size : null},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H3'})}).catch(()=>{});
            // #endregion
            const id = parseInt(this.dataset.id, 10);
            const nombre = this.dataset.nombre;
            const email = this.dataset.email;
            
            if (id && nombre) {
                if (window.CorrespondenciaBlockedRecipients &&
                    !window.CorrespondenciaBlockedRecipients.canAddRecipient(email, form)) {
                    return;
                }
                // Agregar al Map de contactos seleccionados
                contactosSeleccionados.set(id, { nombre: nombre, email: email || '' });
                actualizarChipsDestinatarios();

                // #region agent log
                fetch('http://localhost:7242/ingest/c9ff4165-5596-432d-8ee8-9d3aa5b2d1d2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'responder-correspondencia.js:551',message:'remitente agregado',data:{idIsNumber:!isNaN(id),contactsSize:contactosSeleccionados.size},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H4'})}).catch(()=>{});
                // #endregion
                
                // Feedback visual: cambiar el botón brevemente
                this.classList.remove('btn-outline-primary');
                this.classList.add('btn-success');
                this.innerHTML = '<i class="bi bi-check"></i>';
                
                setTimeout(() => {
                    this.classList.remove('btn-success');
                    this.classList.add('btn-outline-primary');
                    this.innerHTML = '<i class="bi bi-plus-circle"></i>';
                }, 1500);
            }
        });
        // #region agent log
        fetch('http://localhost:7242/ingest/c9ff4165-5596-432d-8ee8-9d3aa5b2d1d2',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({location:'responder-correspondencia.js:565',message:'btn remitente handler attached',data:{attached:true},timestamp:Date.now(),sessionId:'debug-session',runId:'pre-fix',hypothesisId:'H2'})}).catch(()=>{});
        // #endregion
    }

    // La función ya está definida globalmente arriba, solo actualizamos la UI local
    const originalAgregarContactos = window.modalRespuestaAgregarContactos;
    window.modalRespuestaAgregarContactos = function(contactos) {
        originalAgregarContactos(contactos);
        // Actualizar UI local si los elementos existen
        if (chipsContainer && hiddenDest && contador) {
            actualizarChipsDestinatarios();
        }
    };

    // El listener de eventos ya está definido globalmente arriba

    // Función para quitar categoría seleccionada
    if (btnQuitarCategoria) {
        btnQuitarCategoria.addEventListener('click', function() {
            categoriaSeleccionada = null;
            
            // Limpiar el input hidden
            if (categoriaIdInput) {
                categoriaIdInput.value = '';
            }
            
            // Ocultar la categoría seleccionada
            if (categoriaWrap) {
                categoriaWrap.style.display = 'none';
            }
            
            // Restaurar el texto del botón
            const btnTexto = document.getElementById('btn-texto-categoria');
            if (btnTexto) {
                btnTexto.textContent = 'Seleccionar categoría de contactos';
            }
            
            // Restaurar el estilo del botón
            if (btnAbrirCategorias) {
                btnAbrirCategorias.classList.remove('btn-success', 'text-white');
                btnAbrirCategorias.classList.add('btn-outline-warning');
            }
        });
    }

    // ===== FUNCIÓN DEBOUCE =====
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

    // ===== MANEJO DEL FORMULARIO =====
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();

            // Prevención de doble envío
            if (form.dataset.submitting === '1') {
                return;
            }
            form.dataset.submitting = '1';
            const submitBtn = form.querySelector('button[type="submit"]');
            if (submitBtn) {
                submitBtn.disabled = true;
            }
            
            // Validar que haya al menos un tipo de destinatario
            const tieneCategoria = categoriaIdInput.value.trim() !== '';
            const contactosMap = window.respuestaContactosSeleccionados || new Map();
            const emailsSet = window.respuestaEmailsSeleccionados || new Set();
            // También revisar las variables locales si las globales están vacías (por si acaso)
            const localMap = contactosSeleccionados || new Map();
            const localSet = emailsSeleccionados || new Set();
            
            const tieneDestinatarios = contactosMap.size > 0 || emailsSet.size > 0 || localMap.size > 0 || localSet.size > 0;
            
            if (!tieneCategoria && !tieneDestinatarios) {
                const warningMsg = 'Debe seleccionar al menos un destinatario o una categoría.';
                if (typeof window.showWarning === 'function') {
                    window.showWarning(warningMsg);
                } else if (typeof showWarning === 'function') {
                    showWarning(warningMsg);
                } else {
                    alert(warningMsg);
                }
                form.dataset.submitting = '0';
                if (submitBtn) submitBtn.disabled = false;
                return;
            }

            if (window.CorrespondenciaBlockedRecipients) {
                const mergedMap = new Map([...localMap, ...contactosMap]);
                const mergedSet = new Set([...localSet, ...emailsSet]);
                const bloqueados = window.CorrespondenciaBlockedRecipients.findBlockedInSelection(
                    mergedMap, mergedSet, form
                );
                if (bloqueados.length) {
                    window.CorrespondenciaBlockedRecipients.notifyBlocked(
                        bloqueados[0],
                        window.CorrespondenciaBlockedRecipients.readConfig(form)
                    );
                    form.dataset.submitting = '0';
                    if (submitBtn) submitBtn.disabled = false;
                    return;
                }
            }

            if (!validarTamanoAdjuntosSeleccionados()) {
                const warningMsg = `Los adjuntos superan el límite de carga (${ADJUNTOS_UPLOAD_MB} MB). Revise la guía para enviarlos mediante Drive personal.`;
                if (typeof window.showWarning === 'function') {
                    window.showWarning(warningMsg);
                } else if (typeof showWarning === 'function') {
                    showWarning(warningMsg);
                } else {
                    alert(warningMsg);
                }
                form.dataset.submitting = '0';
                if (submitBtn) submitBtn.disabled = false;
                return;
            }

            if (esRespuestaDiscrecional) {
                const motivoField = document.getElementById('motivo_respuesta_discrecional');
                const motivo = motivoField ? motivoField.value.trim() : '';
                if (!motivo) {
                    const warningMsg = 'Debe indicar el motivo de la respuesta discrecional.';
                    if (typeof window.showWarning === 'function') {
                        window.showWarning(warningMsg);
                    } else if (typeof showWarning === 'function') {
                        showWarning(warningMsg);
                    } else {
                        alert(warningMsg);
                    }
                    if (motivoField) {
                        motivoField.focus();
                    }
                    form.dataset.submitting = '0';
                    if (submitBtn) submitBtn.disabled = false;
                    return;
                }
            }

            // Enviar formulario
            const formData = new FormData(form);
            
            fetch(form.dataset.responderEndpoint, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest'
                }
            })
            .then(response => {
                if (!response.ok) {
                    throw new Error('Error en la respuesta del servidor');
                }
                return response.json();
            })
            .then(data => {
                if (data.success) {
                    const successMsg = data.message || 'Respuesta creada exitosamente.';
                    // Intentar usar toast personalizado - verificar múltiples formas
                    let toastShown = false;
                    if (typeof window.showSuccess === 'function') {
                        try {
                            window.showSuccess(successMsg);
                            toastShown = true;
                        } catch (e) {
                            console.error('Error al mostrar toast:', e);
                        }
                    }
                    
                    if (!toastShown && typeof showSuccess === 'function') {
                        try {
                            showSuccess(successMsg);
                            toastShown = true;
                        } catch (e) {
                            console.error('Error al mostrar toast (sin window):', e);
                        }
                    }
                    
                    // Fallback solo si no se pudo mostrar el toast
                    if (!toastShown) {
                        console.warn('[Responder] showSuccess no disponible, usando alert como fallback');
                        alert(successMsg);
                    }
                    
                    // Cerrar modal y recargar página
                    const modal = bootstrap.Modal.getInstance(document.getElementById('modalResponderCorrespondencia'));
                    if (modal) modal.hide();
                    setTimeout(() => location.reload(), 1500);
                } else {
                    // Intentar usar toast de error
                    const errorMsg = 'Error: ' + (data.error || 'Ocurrió un error desconocido.');
                    if (esErrorTamanoAdjuntos(data)) {
                        mostrarAlertaAdjuntosDrive(calcularTamanoTotalAdjuntos(), data.error);
                    }
                    let errorShown = false;
                    
                    if (typeof window.showError === 'function') {
                        try {
                            window.showError(errorMsg);
                            errorShown = true;
                        } catch (e) {
                            console.error('Error al mostrar toast de error:', e);
                        }
                    }
                    
                    if (!errorShown && typeof showError === 'function') {
                        try {
                            showError(errorMsg);
                            errorShown = true;
                        } catch (e) {
                            console.error('Error al mostrar toast de error (sin window):', e);
                        }
                    }
                    
                    if (!errorShown) {
                        console.warn('[Responder] showError no disponible, usando alert como fallback');
                        alert(errorMsg);
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                const errorMsg = 'Error al enviar la respuesta. Por favor, intente nuevamente.';
                if (typeof window.showError === 'function') {
                    window.showError(errorMsg);
                } else if (typeof showError === 'function') {
                    showError(errorMsg);
                } else {
                    console.warn('showError no disponible, usando alert como fallback');
                alert('Error al enviar la respuesta');
                }
            })
            .finally(() => {
                form.dataset.submitting = '0';
                if (submitBtn) {
                    submitBtn.disabled = false;
                }
            });
        });
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    inicializarNuevoModalResponder();
});


