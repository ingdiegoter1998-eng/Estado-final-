/**
 * JavaScript para el modal de comunicación interna.
 * Maneja diferentes tipos de distribución: USUARIO, OFICINA, PROCESO, ENTIDAD
 */

(function() {
    'use strict';

    const form = document.getElementById('formComunicacionInterna');
    if (!form) return;

    const modalElement = document.getElementById('modalComunicacionInterna');
    const internaEndpoint = form.dataset.internaEndpoint;
    const usuariosEndpoint = form.dataset.usuariosEndpoint;
    const oficinasEndpoint = form.dataset.oficinasEndpoint;
    const procesosEndpoint = form.dataset.procesosEndpoint;
    
    // Elementos del formulario
    const tipoDistribucionSelect = document.getElementById('interna_tipo_distribucion');
    const campoUsuario = document.getElementById('interna_campo_usuario');
    const campoOficina = document.getElementById('interna_campo_oficina');
    const campoProceso = document.getElementById('interna_campo_proceso');
    const warningFirma = document.getElementById('interna_warning_firma');
    const infoTipoDistribucion = document.getElementById('interna_info_tipo_distribucion');
    
    // Campos de usuario específico (obsoletos, mantenidos para compatibilidad)
    const oficinaSelect = document.getElementById('interna_destinatario_oficina');
    const usuarioSelect = document.getElementById('interna_destinatario_usuario');
    
    // Campos de selección múltiple (nuevos)
    const oficinaFiltroSelect = document.getElementById('interna_destinatario_oficina_filtro');
    const usuarioMultipleSelect = document.getElementById('interna_destinatario_usuario_multiple');
    const oficinaMultipleSelect = document.getElementById('interna_destinatario_oficina_multiple');
    const chipsDestinatarios = document.getElementById('interna_chips_destinatarios');
    const contadorDestinatarios = document.getElementById('interna_contador_destinatarios');
    const hiddenDestinatarios = document.getElementById('interna_hidden_destinatarios');
    const btnLimpiarDestinatarios = document.getElementById('interna_btn_limpiar_destinatarios');
    const btnAgregarDestinatarioSugerido = document.getElementById('respuesta_agregar_destinatario_btn');
    const btnAgregarDestinatarioSugeridoTexto = document.getElementById('respuesta_agregar_destinatario_texto');
    const btnAgregarDestinatarioSugeridoIcono = document.getElementById('respuesta_agregar_destinatario_icon');
    
    // Estado de destinatarios seleccionados
    let destinatariosSeleccionados = {
        usuarios: new Map(), // Map<id, {id, nombre, oficina_nombre}>
        oficinas: new Map()  // Map<id, {id, nombre}>
    };
    
    // Campos de oficina completa
    const oficinaCompletaSelect = document.getElementById('interna_destinatario_oficina_completa');
    
    // Campo de proceso
    const procesoSelect = document.getElementById('interna_destinatario_proceso');
    
    // Campo oculto para compatibilidad
    const esTodaEntidadHidden = document.getElementById('interna_es_a_toda_entidad');
    
    const btnEnviar = document.getElementById('interna_btn_enviar');

    // Inicializar fecha de hoy
    if (form) {
        const fechaInput = document.getElementById('interna_fecha_documento');
        if (fechaInput && !fechaInput.value) {
            const today = new Date().toISOString().split('T')[0];
            fechaInput.value = today;
        }
    }

    // ===== FUNCIONALIDAD SERIE/SUBSERIE/TRD =====
    const subseriesEndpoint = '/registros/cargar_subseries/';
    const seriesEndpoint = '/registros/cargar_series/';
    const trdScopeQuery = 'scope=comunicacion_interna';

    // Función para obtener elementos del DOM
    function getSerieElements() {
        return {
            serieSelect: document.getElementById('interna_serie'),
            subserieSelect: document.getElementById('interna_subserie'),
            codigoTrdInput: document.getElementById('interna_trd')
        };
    }

    // Cargar series al inicializar
    function cargarSeries() {
        const elements = getSerieElements();
        const serieSelect = elements.serieSelect;
        
        if (!serieSelect) {
            console.warn('No se encontró el select de serie');
            return;
        }
        
        console.log('Cargando series desde:', seriesEndpoint);
        
        fetch(`${seriesEndpoint}?${trdScopeQuery}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Series recibidas:', data);
                // Limpiar opciones existentes excepto la primera
                serieSelect.innerHTML = '<option value="">Seleccione una serie...</option>';
                if (data && data.length > 0) {
                    data.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.id; // Usar ID para cargar subseries
                        option.textContent = item.nombre;
                        option.dataset.codigoTrd = item.codigo_trd || '';
                        serieSelect.appendChild(option);
                    });
                    if (data.length === 1) {
                        serieSelect.value = String(data[0].id);
                        cargarSubseries(data[0].id);
                    }
                    console.log('Series cargadas exitosamente');
                } else {
                    console.warn('No se recibieron series');
                }
            })
            .catch(error => {
                console.error('Error al cargar series:', error);
            });
    }

    // Cargar subseries cuando cambie la serie
    function cargarSubseries(serieId) {
        const elements = getSerieElements();
        const subserieSelect = elements.subserieSelect;
        const codigoTrdInput = elements.codigoTrdInput;
        
        if (!subserieSelect || !serieId) {
            if (subserieSelect) {
                subserieSelect.innerHTML = '<option value="">Seleccione una serie primero...</option>';
                subserieSelect.disabled = true;
            }
            if (codigoTrdInput) {
                codigoTrdInput.value = '';
            }
            return;
        }

        // Resetear subseries
        subserieSelect.innerHTML = '<option value="">Cargando...</option>';
        subserieSelect.disabled = true;

        console.log('Cargando subseries para serie_id:', serieId);

        fetch(`${subseriesEndpoint}?serie_id=${encodeURIComponent(serieId)}&${trdScopeQuery}`, {
            method: 'GET',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
            },
            credentials: 'same-origin'
        })
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                console.log('Subseries recibidas:', data);
                subserieSelect.innerHTML = '<option value="">Seleccione una subserie...</option>';
                if (data && data.length > 0) {
                    data.forEach(item => {
                        const option = document.createElement('option');
                        option.value = item.id;
                        option.textContent = item.nombre;
                        option.dataset.codigoTrd = item.codigo_trd || '';
                        subserieSelect.appendChild(option);
                    });
                    subserieSelect.disabled = false;
                    if (data.length === 1) {
                        subserieSelect.value = String(data[0].id);
                        subserieSelect.dispatchEvent(new Event('change'));
                    }
                    console.log('Subseries cargadas exitosamente');
                } else {
                    subserieSelect.innerHTML = '<option value="">No hay subseries disponibles</option>';
                }
            })
            .catch(error => {
                console.error('Error al cargar subseries:', error);
                subserieSelect.innerHTML = '<option value="">Error al cargar subseries</option>';
            });
    }

    // Inicializar series y eventos cuando el modal se abra
    function inicializarSerieSubserie() {
        const elements = getSerieElements();
        const serieSelect = elements.serieSelect;
        const subserieSelect = elements.subserieSelect;
        const codigoTrdInput = elements.codigoTrdInput;

        if (!serieSelect || !subserieSelect) {
            console.warn('No se encontraron los elementos de serie/subserie');
            return;
        }

        if (serieSelect.dataset.trdBound === '1') {
            return;
        }
        serieSelect.dataset.trdBound = '1';

        // Evento cuando cambia la serie
        serieSelect.addEventListener('change', () => {
            cargarSubseries(serieSelect.value);
        });

        // Evento cuando cambia la subserie - autocompletar TRD
        if (codigoTrdInput) {
            subserieSelect.addEventListener('change', () => {
                const usuarioOficinaTrd = modalElement ? modalElement.dataset.usuarioOficinaTrd : '';
                const usuarioOficinaTrdDisplay = modalElement ? modalElement.dataset.usuarioOficinaTrdDisplay : 'sin trd por falta de mapeo';

                codigoTrdInput.value = usuarioOficinaTrd || usuarioOficinaTrdDisplay;
            });
        }
    }

    // Función para configurar eventos del modal
    function configurarModal() {
        const modal = document.getElementById('modalComunicacionInterna');
        if (!modal) {
            // Si el modal no existe aún, intentar de nuevo después de un breve delay
            setTimeout(configurarModal, 100);
            return;
        }

        console.log('Configurando eventos del modal');
        
        // Cargar series cuando se abre el modal
        modal.addEventListener('shown.bs.modal', () => {
            console.log('Modal abierto, inicializando serie/subserie');
            
            // Pequeño delay para asegurar que el DOM esté completamente renderizado
            setTimeout(() => {
                inicializarSerieSubserie();
                
                const elements = getSerieElements();
                // Limpiar campos
                if (elements.serieSelect) {
                    elements.serieSelect.innerHTML = '<option value="">Seleccione una serie...</option>';
                }
                if (elements.subserieSelect) {
                    elements.subserieSelect.innerHTML = '<option value="">Seleccione una serie primero...</option>';
                    elements.subserieSelect.disabled = true;
                }
                if (elements.codigoTrdInput) {
                    elements.codigoTrdInput.value = '';
                }
                // Cargar series
                cargarSeries();
            }, 100);
        });

        // Limpiar campos cuando se cierra el modal
        modal.addEventListener('hidden.bs.modal', () => {
            const elements = getSerieElements();
            if (elements.serieSelect) {
                elements.serieSelect.innerHTML = '<option value="">Seleccione una serie...</option>';
            }
            if (elements.subserieSelect) {
                elements.subserieSelect.innerHTML = '<option value="">Seleccione una serie primero...</option>';
                elements.subserieSelect.disabled = true;
            }
            if (elements.codigoTrdInput) {
                elements.codigoTrdInput.value = '';
            }
            
            // Restaurar estado del modal para próxima apertura
            modoActual = 'crear';
            comunicacionIdResponder = null;
            
            // Restaurar título
            const tituloModal = document.getElementById('modal-interna-titulo');
            if (tituloModal) {
                tituloModal.textContent = 'Nueva Comunicación Interna';
            }
            
            // Restaurar botón de submit
            const btnEnviar = document.getElementById('interna_btn_enviar');
            if (btnEnviar) {
                btnEnviar.innerHTML = '<i class="bi bi-send me-1"></i>Crear y Enviar';
            }
            
            // Limpiar formulario
            const form = document.getElementById('formComunicacionInterna');
            if (form) form.reset();
            
            // Limpiar destinatarios
            destinatariosSeleccionados.usuarios.clear();
            destinatariosSeleccionados.oficinas.clear();
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', configurarModal);
    } else {
        configurarModal();
    }
    // ===== FIN FUNCIONALIDAD SERIE/SUBSERIE/TRD =====

    // Función para actualizar campos según tipo de distribución
    function actualizarCamposPorTipo() {
        const tipo = tipoDistribucionSelect?.value || 'USUARIO';
        
        // Ocultar todos los campos primero
        if (campoUsuario) campoUsuario.style.display = 'none';
        if (campoOficina) campoOficina.style.display = 'none';
        if (campoProceso) campoProceso.style.display = 'none';
        
        // Actualizar campo oculto para compatibilidad
        if (esTodaEntidadHidden) {
            esTodaEntidadHidden.value = (tipo === 'ENTIDAD') ? '1' : '0';
        }
        
        // Mostrar warning de firma para tipos que la requieren (OFICINA, PROCESO, ENTIDAD)
        if (warningFirma) {
            if (['OFICINA', 'PROCESO', 'ENTIDAD'].includes(tipo)) {
                warningFirma.style.display = 'block';
                // Actualizar texto según tipo
                let textoFirma = '';
                if (tipo === 'ENTIDAD') {
                    textoFirma = 'Esta comunicación requerirá que el líder suba el documento firmado digitalmente antes de ser distribuida a toda la entidad.';
                } else if (tipo === 'PROCESO') {
                    textoFirma = 'Esta comunicación requerirá que el líder suba el documento firmado digitalmente antes de ser distribuida al proceso completo.';
                } else if (tipo === 'OFICINA') {
                    textoFirma = 'Esta comunicación requerirá que el líder suba el documento firmado digitalmente antes de ser distribuida a la oficina completa.';
                }
                const warningText = warningFirma.querySelector('strong');
                if (warningText && warningText.nextSibling) {
                    warningText.nextSibling.textContent = ' ' + textoFirma;
                }
            } else {
                warningFirma.style.display = 'none';
            }
        }
        
        // Actualizar información del tipo
        const infoTexts = {
            'USUARIO': 'Seleccione múltiples usuarios de una o varias oficinas, o seleccione oficinas completas.',
            'OFICINA': 'Se enviará a todos los funcionarios del subproceso seleccionado. Requiere firma del líder.',
            'PROCESO': 'Se enviará a todos los funcionarios de todas las oficinas del proceso. Requiere firma del líder. No se pueden crear respuestas.',
            'ENTIDAD': 'Se enviará a todos los usuarios del sistema. Requiere firma del líder.'
        };
        if (infoTipoDistribucion) {
            infoTipoDistribucion.textContent = infoTexts[tipo] || infoTexts['USUARIO'];
        }
        
        // Mostrar campos según tipo
        switch(tipo) {
            case 'USUARIO':
                if (campoUsuario) campoUsuario.style.display = 'block';
                // Hacer requeridos los campos de usuario
                if (oficinaSelect) oficinaSelect.removeAttribute('required');
                if (usuarioSelect) usuarioSelect.removeAttribute('required');
                // Cargar oficinas cuando se muestra el campo USUARIO
                // Usar un timeout más largo para asegurar que el DOM esté listo
                setTimeout(() => {
                    console.log('Cargando oficinas para selección múltiple...');
                    cargarOficinasParaSeleccion();
                }, 300);
                break;
                
            case 'OFICINA':
                if (campoOficina) campoOficina.style.display = 'block';
                // Cargar oficinas cuando se muestra el campo OFICINA
                setTimeout(() => {
                    console.log('Cargando oficinas para selección múltiple (tipo OFICINA)...');
                    cargarOficinasParaSeleccion();
                }, 300);
                break;
                
            case 'PROCESO':
                if (campoProceso) campoProceso.style.display = 'block';
                if (procesoSelect) procesoSelect.setAttribute('required', 'required');
                break;
                
            case 'ENTIDAD':
                // No mostrar campos adicionales
                break;
        }
        
        // Limpiar selecciones de campos no visibles
        if (tipo !== 'USUARIO') {
            // Limpiar usuarios
            destinatariosSeleccionados.usuarios.clear();
            actualizarChipsDestinatarios();
            
            // Actualizar todas las tarjetas de usuarios
            document.querySelectorAll('.user-card').forEach(card => {
                card.className = 'card user-card border-secondary';
                const checkbox = card.querySelector('.form-check-input');
                if (checkbox) checkbox.checked = false;
                const iconCheck = card.querySelector('.bi-check-circle-fill');
                if (iconCheck) iconCheck.remove();
            });
        }
        if (tipo !== 'OFICINA') {
            // Limpiar oficinas
            destinatariosSeleccionados.oficinas.clear();
            actualizarChipsOficinas();
            
            // Actualizar todas las tarjetas de oficinas
            document.querySelectorAll('.oficina-card').forEach(card => {
                card.className = 'card oficina-card border-secondary';
                const checkbox = card.querySelector('.form-check-input');
                if (checkbox) checkbox.checked = false;
                const iconCheck = card.querySelector('.bi-check-circle-fill');
                if (iconCheck) iconCheck.remove();
            });
        }
        if (tipo !== 'PROCESO') {
            if (procesoSelect) procesoSelect.value = '';
        }
    }

    // Inicializar estado
    if (tipoDistribucionSelect) {
        actualizarCamposPorTipo();
        tipoDistribucionSelect.addEventListener('change', actualizarCamposPorTipo);
    }

    // Cargar oficinas disponibles
    function cargarOficinas() {
        if (!oficinasEndpoint) return;
        
        const selects = [oficinaSelect, oficinaCompletaSelect].filter(s => s);
        
        selects.forEach(select => {
            if (!select) return;
            
            fetch(oficinasEndpoint)
                .then(response => response.json())
                .then(data => {
                    select.innerHTML = '<option value="">Seleccionar Oficina...</option>';
                    if (Array.isArray(data)) {
                        data.forEach(oficina => {
                            const option = document.createElement('option');
                            option.value = oficina.id;
                            option.textContent = oficina.text;
                            select.appendChild(option);
                        });
                    }
                })
                .catch(error => {
                    console.error('Error cargando oficinas:', error);
                });
        });
    }

    // Cargar procesos disponibles
    function cargarProcesos() {
        if (!procesoSelect || !procesosEndpoint) return;
        
        fetch(procesosEndpoint)
            .then(response => response.json())
            .then(data => {
                procesoSelect.innerHTML = '<option value="">Seleccionar Proceso...</option>';
                if (Array.isArray(data)) {
                    data.forEach(proceso => {
                        const option = document.createElement('option');
                        option.value = proceso.id;
                        option.textContent = proceso.text;
                        procesoSelect.appendChild(option);
                    });
                }
            })
            .catch(error => {
                console.error('Error cargando procesos:', error);
            });
    }

    // Detectar modo (crear o responder)
    let modoActual = 'crear';
    let comunicacionIdResponder = null;

    function obtenerRemitenteOriginalComoUsuario() {
        if (!window.remitenteOriginalId) {
            return null;
        }

        return {
            id: String(window.remitenteOriginalId),
            nombre: window.remitenteOriginalNombre || 'Usuario',
            oficina_nombre: window.remitenteOriginalOficina || ''
        };
    }

    function actualizarBotonDestinatarioSugerido() {
        if (!btnAgregarDestinatarioSugerido) return;

        const remitenteOriginal = obtenerRemitenteOriginalComoUsuario();
        const estaSeleccionado = remitenteOriginal
            ? destinatariosSeleccionados.usuarios.has(remitenteOriginal.id)
            : false;

        btnAgregarDestinatarioSugerido.disabled = false;
        btnAgregarDestinatarioSugerido.removeAttribute('disabled');
        btnAgregarDestinatarioSugerido.classList.toggle('btn-outline-primary', !estaSeleccionado);
        btnAgregarDestinatarioSugerido.classList.toggle('btn-success', estaSeleccionado);
        btnAgregarDestinatarioSugerido.classList.toggle('btn-outline-danger', false);

        if (btnAgregarDestinatarioSugeridoTexto) {
            btnAgregarDestinatarioSugeridoTexto.textContent = estaSeleccionado
                ? 'Quitar del destino'
                : 'Agregar como destino';
        }

        if (btnAgregarDestinatarioSugeridoIcono) {
            btnAgregarDestinatarioSugeridoIcono.className = estaSeleccionado
                ? 'bi bi-person-dash-fill me-1'
                : 'bi bi-person-plus-fill me-1';
        }

        btnAgregarDestinatarioSugerido.setAttribute(
            'aria-label',
            estaSeleccionado ? 'Quitar del destino' : 'Agregar como destino'
        );
    }

    function agregarRemitenteOriginalComoDestino() {
        const remitenteOriginal = obtenerRemitenteOriginalComoUsuario();
        if (!remitenteOriginal) return;

        destinatariosSeleccionados.usuarios.set(remitenteOriginal.id, remitenteOriginal);
        actualizarChipsDestinatarios();

        const card = document.querySelector(`[data-user-id="${remitenteOriginal.id}"]`);
        if (card) {
            card.className = 'card user-card border-primary bg-primary bg-opacity-10';
            const checkbox = card.querySelector('.form-check-input');
            if (checkbox) checkbox.checked = true;
            const iconCheck = card.querySelector('.bi-check-circle-fill');
            if (!iconCheck) {
                const newIcon = document.createElement('i');
                newIcon.className = 'bi bi-check-circle-fill text-primary';
                card.querySelector('.card-body > div').appendChild(newIcon);
            }
        }
    }

    function quitarRemitenteOriginalComoDestino() {
        const remitenteOriginal = obtenerRemitenteOriginalComoUsuario();
        if (!remitenteOriginal) return;

        destinatariosSeleccionados.usuarios.delete(remitenteOriginal.id);
        actualizarChipsDestinatarios();

        const card = document.querySelector(`[data-user-id="${remitenteOriginal.id}"]`);
        if (card) {
            card.className = 'card user-card border-secondary';
            const checkbox = card.querySelector('.form-check-input');
            if (checkbox) checkbox.checked = false;
            const iconCheck = card.querySelector('.bi-check-circle-fill');
            if (iconCheck) {
                iconCheck.remove();
            }
        }
    }
    
    // Detectar cuando se abre el modal desde un botón de responder
    document.addEventListener('click', function(e) {
        const btn = e.target.closest('[data-bs-target="#modalComunicacionInterna"]');
        if (btn && btn.dataset.mode === 'responder') {
            modoActual = 'responder';
            comunicacionIdResponder = btn.dataset.comunicacionPk;
            
            // Guardar datos del remitente original para pre-seleccionar
            window.remitenteOriginalId = btn.dataset.remitenteId;
            window.remitenteOriginalNombre = btn.dataset.remitenteNombre;
            window.remitenteOriginalOficina = btn.dataset.remitenteOficina;
            window.remitenteOriginalOficinaId = btn.dataset.remitenteOficinaId;
            
            // Actualizar título del modal
            const tituloModal = document.getElementById('modal-interna-titulo');
            if (tituloModal) {
                tituloModal.textContent = 'Responder Comunicación Interna';
            }
            
            // Mostrar sección de respuesta con remitente y destinatario
            const seccionRespuesta = document.getElementById('interna_seccion_respuesta');
            if (seccionRespuesta) {
                seccionRespuesta.style.display = 'block';
            }
            
            // Cargar datos del remitente original en la sección informativa
            if (btn.dataset.remitenteNombre) {
                const remitenteNombreEl = document.getElementById('respuesta_destinatario_nombre');
                const remitenteOficinaEl = document.getElementById('respuesta_destinatario_oficina');
                if (remitenteNombreEl) remitenteNombreEl.textContent = btn.dataset.remitenteNombre;
                if (remitenteOficinaEl) remitenteOficinaEl.textContent = btn.dataset.remitenteOficina || '-';
            }

            actualizarBotonDestinatarioSugerido();
            
            // Ocultar campos de tipo de distribución (las respuestas siempre van a USUARIO)
            if (tipoDistribucionSelect && tipoDistribucionSelect.closest('.mb-3')) {
                tipoDistribucionSelect.closest('.mb-3').style.display = 'none';
                tipoDistribucionSelect.value = 'USUARIO';  // Forzar tipo USUARIO
            }
            
            // MOSTRAR campo de usuarios para permitir selección
            if (campoUsuario) campoUsuario.style.display = 'block';
            if (campoOficina) campoOficina.style.display = 'none';
            if (campoProceso) campoProceso.style.display = 'none';
            
            // Pre-llenar asunto con RE:
            const asuntoInput = document.getElementById('interna_asunto');
            if (asuntoInput && btn.dataset.comunicacionAsunto) {
                asuntoInput.value = `RE: ${btn.dataset.comunicacionAsunto}`;
            }
        } else if (btn) {
            modoActual = 'crear';
            comunicacionIdResponder = null;
            window.remitenteOriginalId = null;
            window.remitenteOriginalNombre = null;
            window.remitenteOriginalOficina = null;
            window.remitenteOriginalOficinaId = null;

            const remitenteNombreEl = document.getElementById('respuesta_destinatario_nombre');
            const remitenteOficinaEl = document.getElementById('respuesta_destinatario_oficina');
            if (remitenteNombreEl) remitenteNombreEl.textContent = '-';
            if (remitenteOficinaEl) remitenteOficinaEl.textContent = '-';
            actualizarBotonDestinatarioSugerido();
            
            // Ocultar sección de respuesta
            const seccionRespuesta = document.getElementById('interna_seccion_respuesta');
            if (seccionRespuesta) {
                seccionRespuesta.style.display = 'none';
            }
            
            // Restaurar título
            const tituloModal = document.getElementById('modal-interna-titulo');
            if (tituloModal) {
                tituloModal.textContent = 'Nueva Comunicación Interna';
            }
            
            // Mostrar campos de tipo de distribución
            if (tipoDistribucionSelect && tipoDistribucionSelect.closest('.mb-3')) {
                tipoDistribucionSelect.closest('.mb-3').style.display = 'block';
            }
        }
    });
    
    // Cargar datos al abrir el modal
    if (modalElement) {
        modalElement.addEventListener('show.bs.modal', function() {
            if (modoActual === 'crear') {
                cargarOficinas();
                cargarProcesos();
                // Cargar datos para selección múltiple
                // Limpiar formulario
                if (form) form.reset();
                // Limpiar destinatarios seleccionados
                destinatariosSeleccionados.usuarios.clear();
                destinatariosSeleccionados.oficinas.clear();
                actualizarChipsDestinatarios();
                // Restablecer fecha
                const fechaInput = document.getElementById('interna_fecha_documento');
                if (fechaInput) {
                    const today = new Date().toISOString().split('T')[0];
                    fechaInput.value = today;
                }
                // Restablecer ciudad
                const ciudadInput = document.getElementById('interna_ciudad');
                if (ciudadInput && !ciudadInput.value) {
                    ciudadInput.value = 'Saravena';
                }
                // Restablecer tipo de distribución
                if (tipoDistribucionSelect) {
                    tipoDistribucionSelect.value = 'USUARIO';
                }
                actualizarCamposPorTipo();
                // Cargar oficinas después de actualizar campos (para que los elementos estén visibles)
                setTimeout(() => {
                    cargarOficinasParaSeleccion();
                }, 200);
            } else {
                // Modo responder: cargar datos y pre-seleccionar remitente original
                cargarOficinas();
                
                // Limpiar destinatarios previos
                destinatariosSeleccionados.usuarios.clear();
                destinatariosSeleccionados.oficinas.clear();
                
                const fechaInput = document.getElementById('interna_fecha_documento');
                if (fechaInput) {
                    const today = new Date().toISOString().split('T')[0];
                    fechaInput.value = today;
                }
                const ciudadInput = document.getElementById('interna_ciudad');
                if (ciudadInput) {
                    ciudadInput.value = 'Saravena';
                }
                
                // Pre-seleccionar al remitente original como destinatario
                if (window.remitenteOriginalId) {
                    agregarRemitenteOriginalComoDestino();
                    
                    // Filtrar por la oficina del remitente original
                    const filtroOficina = document.getElementById('interna_destinatario_oficina_filtro');
                    if (filtroOficina && window.remitenteOriginalOficinaId) {
                        setTimeout(() => {
                            filtroOficina.value = window.remitenteOriginalOficinaId;
                            cargarUsuariosPorOficina(window.remitenteOriginalOficinaId);
                        }, 300);
                    }
                }
            }
        });
    }

    // =================================================================
    // FUNCIONES PARA MANEJO DE DESTINATARIOS MÚLTIPLES
    // =================================================================
    
    // Función para actualizar chips y campos hidden de USUARIOS (tipo USUARIO)
    function actualizarChipsDestinatarios() {
        const chipsDestinatarios = document.getElementById('interna_chips_destinatarios');
        const hiddenDestinatarios = document.getElementById('interna_hidden_destinatarios');
        const contadorDestinatarios = document.getElementById('interna_contador_destinatarios');
        if (!chipsDestinatarios || !hiddenDestinatarios || !contadorDestinatarios) return;
        
        chipsDestinatarios.innerHTML = '';
        hiddenDestinatarios.innerHTML = '';
        
        let total = 0;
        
        // Agregar chips de usuarios
        destinatariosSeleccionados.usuarios.forEach((usuario, id) => {
            const chip = document.createElement('span');
            chip.className = 'badge bg-primary me-1 mb-1 p-2';
            chip.draggable = true;
            chip.dataset.tipo = 'usuario';
            chip.dataset.id = id;
            chip.style.cursor = 'move';
            chip.innerHTML = `
                <i class="bi bi-grip-vertical me-1"></i>
                <i class="bi bi-person-fill me-1"></i>
                ${usuario.nombre}${usuario.oficina_nombre ? ` <small>(${usuario.oficina_nombre})</small>` : ''}
                <button type="button" class="btn-close btn-close-white ms-2" data-tipo="usuario" data-id="${id}" style="font-size: 0.65em;"></button>
            `;
            
            // Event listeners para drag & drop
            chip.addEventListener('dragstart', handleDragStart);
            chip.addEventListener('dragover', handleDragOver);
            chip.addEventListener('drop', handleDrop);
            chip.addEventListener('dragend', handleDragEnd);
            
            chipsDestinatarios.appendChild(chip);
            
            // Agregar campo hidden
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'destinatarios_usuarios';
            input.value = id;
            hiddenDestinatarios.appendChild(input);
            
            total++;
        });
        
        contadorDestinatarios.textContent = total;
        
        if (total === 0) {
            chipsDestinatarios.innerHTML = `
                <div class="text-center text-muted py-2">
                    <i class="bi bi-inbox me-1"></i> No hay usuarios seleccionados
                </div>
            `;
        }

        actualizarBotonDestinatarioSugerido();
    }
    
    // Función para actualizar chips y campos hidden de OFICINAS (tipo OFICINA)
    function actualizarChipsOficinas() {
        const chipsOficinas = document.getElementById('interna_chips_oficinas');
        const hiddenOficinas = document.getElementById('interna_hidden_oficinas');
        const contadorOficinas = document.getElementById('interna_contador_oficinas');
        if (!chipsOficinas || !hiddenOficinas || !contadorOficinas) return;
        
        chipsOficinas.innerHTML = '';
        hiddenOficinas.innerHTML = '';
        
        let total = 0;
        
        // Agregar chips de oficinas
        destinatariosSeleccionados.oficinas.forEach((oficina, id) => {
            const chip = document.createElement('span');
            chip.className = 'badge bg-info me-1 mb-1 p-2';
            chip.draggable = true;
            chip.dataset.tipo = 'oficina';
            chip.dataset.id = id;
            chip.style.cursor = 'move';
            chip.innerHTML = `
                <i class="bi bi-grip-vertical me-1"></i>
                <i class="bi bi-building-fill me-1"></i>
                ${oficina.nombre} <small>(Oficina completa)</small>
                <button type="button" class="btn-close btn-close-white ms-2" data-tipo="oficina" data-id="${id}" style="font-size: 0.65em;"></button>
            `;
            
            // Event listeners para drag & drop
            chip.addEventListener('dragstart', handleDragStart);
            chip.addEventListener('dragover', handleDragOver);
            chip.addEventListener('drop', handleDrop);
            chip.addEventListener('dragend', handleDragEnd);
            
            chipsOficinas.appendChild(chip);
            
            // Agregar campo hidden
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = 'destinatarios_oficinas';
            input.value = id;
            hiddenOficinas.appendChild(input);
            
            total++;
        });
        
        contadorOficinas.textContent = total;
        
        if (total === 0) {
            chipsOficinas.innerHTML = `
                <div class="text-center text-muted py-2">
                    <i class="bi bi-inbox me-1"></i> No hay oficinas seleccionadas
                </div>
            `;
        }
    }
    
    // Variables para drag & drop
    let draggedElement = null;
    
    function handleDragStart(e) {
        draggedElement = this;
        this.style.opacity = '0.4';
        e.dataTransfer.effectAllowed = 'move';
        e.dataTransfer.setData('text/html', this.innerHTML);
    }
    
    function handleDragOver(e) {
        if (e.preventDefault) {
            e.preventDefault();
        }
        e.dataTransfer.dropEffect = 'move';
        return false;
    }
    
    function handleDrop(e) {
        if (e.stopPropagation) {
            e.stopPropagation();
        }
        
        if (draggedElement !== this) {
            // Intercambiar posiciones
            const parent = this.parentNode;
            const draggedIndex = Array.from(parent.children).indexOf(draggedElement);
            const targetIndex = Array.from(parent.children).indexOf(this);
            
            if (draggedIndex < targetIndex) {
                parent.insertBefore(draggedElement, this.nextSibling);
            } else {
                parent.insertBefore(draggedElement, this);
            }
        }
        
        return false;
    }
    
    function handleDragEnd(e) {
        this.style.opacity = '1';
        draggedElement = null;
    }
    
    // Función para cargar usuarios de una oficina como tarjetas
    function cargarUsuariosPorOficina(oficinaId = null) {
        const listaTarjetas = document.getElementById('interna_lista_usuarios_tarjetas');
        if (!listaTarjetas || !usuariosEndpoint) {
            console.warn('Lista de tarjetas de usuarios o endpoint no disponible');
            return;
        }
        
        // Si no hay oficina seleccionada, mostrar mensaje
        if (!oficinaId) {
            listaTarjetas.innerHTML = `
                <div class="col-12 text-center text-muted py-3">
                    <i class="bi bi-info-circle me-1"></i> Seleccione una oficina para ver usuarios
                </div>
            `;
            return;
        }
        
        // Mostrar loading
        listaTarjetas.innerHTML = `
            <div class="col-12 text-center text-muted py-3">
                <div class="spinner-border spinner-border-sm me-2" role="status"></div>
                Cargando usuarios...
            </div>
        `;
        
        const url = `${usuariosEndpoint}?oficina_id=${oficinaId}`;
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.error) {
                    console.error('Error:', data.error);
                    listaTarjetas.innerHTML = `
                        <div class="col-12 text-center text-danger py-3">
                            <i class="bi bi-exclamation-triangle me-1"></i> Error cargando usuarios
                        </div>
                    `;
                    return;
                }
                
                if (Array.isArray(data) && data.length > 0) {
                    listaTarjetas.innerHTML = '';
                    data.forEach(user => {
                        const estaSeleccionado = destinatariosSeleccionados.usuarios.has(String(user.id));
                        const tarjeta = crearTarjetaUsuario(user, estaSeleccionado);
                        listaTarjetas.appendChild(tarjeta);
                    });
                } else {
                    listaTarjetas.innerHTML = `
                        <div class="col-12 text-center text-muted py-3">
                            <i class="bi bi-inbox me-1"></i> No hay usuarios en esta oficina
                        </div>
                    `;
                }
            })
            .catch(error => {
                console.error('Error cargando usuarios:', error);
                listaTarjetas.innerHTML = `
                    <div class="col-12 text-center text-danger py-3">
                        <i class="bi bi-exclamation-triangle me-1"></i> Error cargando usuarios
                    </div>
                `;
            });
    }
    
    // Función para crear tarjeta de usuario
    function crearTarjetaUsuario(user, seleccionado = false) {
        const col = document.createElement('div');
        col.className = 'col-12';
        
        const card = document.createElement('div');
        card.className = `card user-card ${seleccionado ? 'border-primary bg-primary bg-opacity-10' : 'border-secondary'}`;
        card.style.cursor = 'pointer';
        card.dataset.userId = user.id;
        card.dataset.userNombre = user.nombre;
        
        card.innerHTML = `
            <div class="card-body py-2 px-3">
                <div class="d-flex align-items-center">
                    <div class="form-check me-2">
                        <input class="form-check-input" type="checkbox" ${seleccionado ? 'checked' : ''} disabled>
                    </div>
                    <div class="flex-grow-1">
                        <i class="bi bi-person-fill me-1"></i>
                        <span class="fw-semibold">${user.nombre}</span>
                    </div>
                    ${seleccionado ? '<i class="bi bi-check-circle-fill text-primary"></i>' : ''}
                </div>
            </div>
        `;
        
        // Event listener para clic en la tarjeta
        card.addEventListener('click', function() {
            toggleUsuario(user);
        });
        
        col.appendChild(card);
        return col;
    }
    
    // Función para toggle de usuario
    function toggleUsuario(user) {
        const userId = String(user.id);
        const oficinaFiltro = document.getElementById('interna_destinatario_oficina_filtro');
        const oficinaFiltroNombre = oficinaFiltro?.selectedOptions[0]?.textContent || null;
        
        if (destinatariosSeleccionados.usuarios.has(userId)) {
            destinatariosSeleccionados.usuarios.delete(userId);
        } else {
            destinatariosSeleccionados.usuarios.set(userId, {
                id: userId,
                nombre: user.nombre,
                oficina_nombre: oficinaFiltroNombre
            });
        }
        
        // Actualizar UI
        actualizarChipsDestinatarios();
        
        // Actualizar tarjeta
        const card = document.querySelector(`[data-user-id="${userId}"]`);
        if (card) {
            const estaSeleccionado = destinatariosSeleccionados.usuarios.has(userId);
            card.className = `card user-card ${estaSeleccionado ? 'border-primary bg-primary bg-opacity-10' : 'border-secondary'}`;
            
            const checkbox = card.querySelector('.form-check-input');
            if (checkbox) checkbox.checked = estaSeleccionado;
            
            const iconCheck = card.querySelector('.bi-check-circle-fill');
            if (estaSeleccionado && !iconCheck) {
                const newIcon = document.createElement('i');
                newIcon.className = 'bi bi-check-circle-fill text-primary';
                card.querySelector('.card-body > div').appendChild(newIcon);
            } else if (!estaSeleccionado && iconCheck) {
                iconCheck.remove();
            }
        }
    }

    if (btnAgregarDestinatarioSugerido) {
        btnAgregarDestinatarioSugerido.addEventListener('click', function() {
            const remitenteOriginal = obtenerRemitenteOriginalComoUsuario();
            if (!remitenteOriginal) return;

            if (destinatariosSeleccionados.usuarios.has(remitenteOriginal.id)) {
                quitarRemitenteOriginalComoDestino();
            } else {
                agregarRemitenteOriginalComoDestino();
            }
        });
    }
    
    // Función para cargar todas las oficinas
    function cargarOficinasParaSeleccion() {
        // Re-obtener referencias a los elementos
        const oficinaFiltro = document.getElementById('interna_destinatario_oficina_filtro');
        const listaTarjetasOficinas = document.getElementById('interna_lista_oficinas_tarjetas');
        
        if (!oficinaFiltro || !oficinasEndpoint) {
            console.warn('Elementos de oficinas no encontrados o endpoint no disponible');
            return;
        }
        
        console.log('Fetching oficinas desde:', oficinasEndpoint);
        fetch(oficinasEndpoint)
            .then(response => {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(data => {
                // Guardar selección actual del filtro
                const seleccionadoFiltro = oficinaFiltro.value;
                
                // Limpiar filtro
                oficinaFiltro.innerHTML = '<option value="">Todas las oficinas</option>';
                
                console.log('Oficinas recibidas:', data);
                if (Array.isArray(data) && data.length > 0) {
                    // Llenar filtro
                    data.forEach(oficina => {
                        const optFiltro = document.createElement('option');
                        optFiltro.value = oficina.id;
                        optFiltro.textContent = oficina.text;
                        if (seleccionadoFiltro === String(oficina.id)) {
                            optFiltro.selected = true;
                        }
                        oficinaFiltro.appendChild(optFiltro);
                    });
                    
                    // Llenar tarjetas de oficinas
                    if (listaTarjetasOficinas) {
                        listaTarjetasOficinas.innerHTML = '';
                        data.forEach(oficina => {
                            const estaSeleccionada = destinatariosSeleccionados.oficinas.has(String(oficina.id));
                            const tarjeta = crearTarjetaOficina(oficina, estaSeleccionada);
                            listaTarjetasOficinas.appendChild(tarjeta);
                        });
                    }
                    
                    console.log(`Cargadas ${data.length} oficinas`);
                } else {
                    console.warn('No se recibieron oficinas del endpoint o el array está vacío');
                    oficinaFiltro.innerHTML = '<option value="">No hay oficinas disponibles</option>';
                    if (listaTarjetasOficinas) {
                        listaTarjetasOficinas.innerHTML = `
                            <div class="col-12 text-center text-muted py-3">
                                <i class="bi bi-inbox me-1"></i> No hay oficinas disponibles
                            </div>
                        `;
                    }
                }
            })
            .catch(error => {
                console.error('Error cargando oficinas:', error);
                if (oficinaFiltro) {
                    oficinaFiltro.innerHTML = '<option value="">Error cargando oficinas</option>';
                }
                if (listaTarjetasOficinas) {
                    listaTarjetasOficinas.innerHTML = `
                        <div class="col-12 text-center text-danger py-3">
                            <i class="bi bi-exclamation-triangle me-1"></i> Error cargando oficinas
                        </div>
                    `;
                }
            });
    }
    
    // Función para crear tarjeta de oficina
    function crearTarjetaOficina(oficina, seleccionada = false) {
        const col = document.createElement('div');
        col.className = 'col-12';
        
        const card = document.createElement('div');
        card.className = `card oficina-card ${seleccionada ? 'border-info bg-info bg-opacity-10' : 'border-secondary'}`;
        card.style.cursor = 'pointer';
        card.dataset.oficinaId = oficina.id;
        card.dataset.oficinaNombre = oficina.text;
        
        card.innerHTML = `
            <div class="card-body py-2 px-3">
                <div class="d-flex align-items-center">
                    <div class="form-check me-2">
                        <input class="form-check-input" type="checkbox" ${seleccionada ? 'checked' : ''} disabled>
                    </div>
                    <div class="flex-grow-1">
                        <i class="bi bi-building-fill me-1"></i>
                        <span class="fw-semibold">${oficina.text}</span>
                        <small class="text-muted d-block">Oficina completa</small>
                    </div>
                    ${seleccionada ? '<i class="bi bi-check-circle-fill text-info"></i>' : ''}
                </div>
            </div>
        `;
        
        // Event listener para clic en la tarjeta
        card.addEventListener('click', function() {
            toggleOficina(oficina);
        });
        
        col.appendChild(card);
        return col;
    }
    
    // Función para toggle de oficina
    function toggleOficina(oficina) {
        const oficinaId = String(oficina.id);
        
        if (destinatariosSeleccionados.oficinas.has(oficinaId)) {
            destinatariosSeleccionados.oficinas.delete(oficinaId);
        } else {
            destinatariosSeleccionados.oficinas.set(oficinaId, {
                id: oficinaId,
                nombre: oficina.text
            });
        }
        
        // Actualizar UI
        actualizarChipsOficinas();
        
        // Actualizar tarjeta
        const card = document.querySelector(`[data-oficina-id="${oficinaId}"]`);
        if (card) {
            const estaSeleccionada = destinatariosSeleccionados.oficinas.has(oficinaId);
            card.className = `card oficina-card ${estaSeleccionada ? 'border-info bg-info bg-opacity-10' : 'border-secondary'}`;
            
            const checkbox = card.querySelector('.form-check-input');
            if (checkbox) checkbox.checked = estaSeleccionada;
            
            const iconCheck = card.querySelector('.bi-check-circle-fill');
            if (estaSeleccionada && !iconCheck) {
                const newIcon = document.createElement('i');
                newIcon.className = 'bi bi-check-circle-fill text-info';
                card.querySelector('.card-body > div').appendChild(newIcon);
            } else if (!estaSeleccionada && iconCheck) {
                iconCheck.remove();
            }
        }
    }
    
    // Event listener específico para el filtro de oficinas (usando delegación desde el documento)
    document.addEventListener('change', function(e) {
        if (e.target && e.target.id === 'interna_destinatario_oficina_filtro') {
            const oficinaId = e.target.value;
            cargarUsuariosPorOficina(oficinaId || null);
        }
    });
    
    // Manejar clicks en chips de usuarios para eliminarlos (usando delegación de eventos)
    document.addEventListener('click', function(e) {
        const chipsDestinatarios = document.getElementById('interna_chips_destinatarios');
        if (chipsDestinatarios && chipsDestinatarios.contains(e.target)) {
            if (e.target.matches('.btn-close') || e.target.closest('.btn-close')) {
                const btn = e.target.closest('.btn-close') || e.target;
                const id = btn.dataset.id;
                
                destinatariosSeleccionados.usuarios.delete(id);
                // Actualizar tarjeta de usuario
                const card = document.querySelector(`[data-user-id="${id}"]`);
                if (card) {
                    card.className = 'card user-card border-secondary';
                    const checkbox = card.querySelector('.form-check-input');
                    if (checkbox) checkbox.checked = false;
                    const iconCheck = card.querySelector('.bi-check-circle-fill');
                    if (iconCheck) iconCheck.remove();
                }
                
                actualizarChipsDestinatarios();
            }
        }
    });
    
    // Manejar clicks en chips de oficinas para eliminarlas (usando delegación de eventos)
    document.addEventListener('click', function(e) {
        const chipsOficinas = document.getElementById('interna_chips_oficinas');
        if (chipsOficinas && chipsOficinas.contains(e.target)) {
            if (e.target.matches('.btn-close') || e.target.closest('.btn-close')) {
                const btn = e.target.closest('.btn-close') || e.target;
                const id = btn.dataset.id;
                
                destinatariosSeleccionados.oficinas.delete(id);
                // Actualizar tarjeta de oficina
                const card = document.querySelector(`[data-oficina-id="${id}"]`);
                if (card) {
                    card.className = 'card oficina-card border-secondary';
                    const checkbox = card.querySelector('.form-check-input');
                    if (checkbox) checkbox.checked = false;
                    const iconCheck = card.querySelector('.bi-check-circle-fill');
                    if (iconCheck) iconCheck.remove();
                }
                
                actualizarChipsOficinas();
            }
        }
    });
    
    // Botón limpiar usuarios (tipo USUARIO)
    document.addEventListener('click', function(e) {
        if (e.target && (e.target.id === 'interna_btn_limpiar_destinatarios_usuarios' || e.target.closest('#interna_btn_limpiar_destinatarios_usuarios'))) {
            destinatariosSeleccionados.usuarios.clear();
            
            // Actualizar todas las tarjetas de usuarios
            document.querySelectorAll('.user-card').forEach(card => {
                card.className = 'card user-card border-secondary';
                const checkbox = card.querySelector('.form-check-input');
                if (checkbox) checkbox.checked = false;
                const iconCheck = card.querySelector('.bi-check-circle-fill');
                if (iconCheck) iconCheck.remove();
            });
            
            actualizarChipsDestinatarios();
        }
    });
    
    // Botón limpiar oficinas (tipo OFICINA)
    document.addEventListener('click', function(e) {
        if (e.target && (e.target.id === 'interna_btn_limpiar_oficinas' || e.target.closest('#interna_btn_limpiar_oficinas'))) {
            destinatariosSeleccionados.oficinas.clear();
            
            // Actualizar todas las tarjetas de oficinas
            document.querySelectorAll('.oficina-card').forEach(card => {
                card.className = 'card oficina-card border-secondary';
                const checkbox = card.querySelector('.form-check-input');
                if (checkbox) checkbox.checked = false;
                const iconCheck = card.querySelector('.bi-check-circle-fill');
                if (iconCheck) iconCheck.remove();
            });
            
            actualizarChipsOficinas();
        }
    });
    
    // Filtro dinámico de usuarios por oficina destino (solo para tipo USUARIO) - OBSOLETO
    // Mantenido para compatibilidad, pero la nueva funcionalidad usa los selects múltiples

    // Manejar envío del formulario
    function enviarFormulario() {
        if (!form || !internaEndpoint) return;

        // Validación básica
        const asunto = document.getElementById('interna_asunto')?.value.trim();
        const cuerpo = document.getElementById('interna_cuerpo')?.value.trim();
        const tipo = tipoDistribucionSelect?.value;

        if (!asunto || !cuerpo) {
            const errorMsg = 'Asunto y contenido son obligatorios.';
            if (typeof window.showError === 'function') {
                window.showError(errorMsg);
            } else {
                alert(errorMsg);
            }
            return;
        }

        // Validaciones según tipo (para modo crear)
        if (modoActual === 'crear') {
            if (tipo === 'USUARIO') {
                // Validar que haya al menos un destinatario seleccionado (usuario)
                if (destinatariosSeleccionados.usuarios.size === 0) {
                    const errorMsg = 'Debe seleccionar al menos un usuario.';
                    if (typeof window.showError === 'function') {
                        window.showError(errorMsg);
                    } else {
                        alert(errorMsg);
                    }
                    return;
                }
            } else if (tipo === 'OFICINA') {
                // Validar que haya al menos una oficina seleccionada
                if (destinatariosSeleccionados.oficinas.size === 0) {
                    const errorMsg = 'Debe seleccionar al menos una oficina (subproceso).';
                    if (typeof window.showError === 'function') {
                        window.showError(errorMsg);
                    } else {
                        alert(errorMsg);
                    }
                    return;
                }
            } else if (tipo === 'PROCESO') {
                const procesoSelect = document.getElementById('interna_destinatario_proceso');
                const proceso = procesoSelect?.value?.trim();
                if (!proceso || proceso === '') {
                    const errorMsg = 'Debe seleccionar un proceso.';
                    if (typeof window.showError === 'function') {
                        window.showError(errorMsg);
                    } else {
                        alert(errorMsg);
                    }
                    if (procesoSelect) {
                        procesoSelect.focus();
                    }
                    return;
                }
            }
        }

        if (form.dataset.submitting === '1') {
            return;
        }

        form.dataset.submitting = '1';
        if (btnEnviar) btnEnviar.disabled = true;

        // Crear FormData manualmente para tener control total sobre los valores
        const formData = new FormData();
        
        // Agregar todos los campos básicos
        formData.append('ciudad', document.getElementById('interna_ciudad')?.value || 'Saravena');
        formData.append('fecha_documento', document.getElementById('interna_fecha_documento')?.value || '');
        formData.append('tipo_distribucion', tipo || 'USUARIO');
        formData.append('asunto', document.getElementById('interna_asunto')?.value || '');
        formData.append('cuerpo', document.getElementById('interna_cuerpo')?.value || '');
        
        const trdInput = document.getElementById('interna_trd');
        if (trdInput?.value) {
            formData.append('trd', trdInput.value);
        }
        
        // Determinar endpoint según modo
        let endpoint = internaEndpoint;
        if (modoActual === 'responder' && comunicacionIdResponder) {
            // Construir endpoint de respuesta
            const baseUrl = internaEndpoint.split('/crear-ajax')[0];
            endpoint = `${baseUrl}/${comunicacionIdResponder}/responder-ajax/`;
            formData.append('save_send', '1');
        } else {
            // Modo crear: siempre enviar a aprobación inmediatamente
            formData.append('enviar_inmediatamente', 'on');
            
            // Agregar campos según tipo de distribución
            if (tipo === 'USUARIO') {
                // Agregar usuarios seleccionados
                destinatariosSeleccionados.usuarios.forEach((usuario, id) => {
                    formData.append('destinatarios_usuarios', id);
                });
                
                // Agregar oficinas seleccionadas como destinatarios (para enviar a oficinas completas desde tipo USUARIO)
                destinatariosSeleccionados.oficinas.forEach((oficina, id) => {
                    formData.append('destinatarios_oficinas', id);
                });
            } else if (tipo === 'OFICINA') {
                // Para tipo OFICINA, enviar las oficinas seleccionadas
                // El backend espera al menos una oficina en destinatarios_oficinas
                if (destinatariosSeleccionados.oficinas.size > 0) {
                    destinatariosSeleccionados.oficinas.forEach((oficina, id) => {
                        formData.append('destinatarios_oficinas', id);
                    });
                    
                    // También enviar la primera oficina en el campo destinatario_oficina para compatibilidad
                    const primeraOficinaId = Array.from(destinatariosSeleccionados.oficinas.keys())[0];
                    formData.append('destinatario_oficina', primeraOficinaId);
                }
            } else if (tipo === 'PROCESO') {
                const oficinaCompletaSelect = document.getElementById('interna_destinatario_oficina_completa');
                const oficinaCompletaValue = oficinaCompletaSelect?.value?.trim();
                console.log('Tipo OFICINA - oficinaCompletaValue:', oficinaCompletaValue);
                if (oficinaCompletaValue) {
                    formData.append('destinatario_oficina', oficinaCompletaValue);
                }
            } else if (tipo === 'PROCESO') {
                const procesoSelect = document.getElementById('interna_destinatario_proceso');
                if (procesoSelect?.value) {
                    formData.append('destinatario_proceso', procesoSelect.value);
                }
            } else if (tipo === 'ENTIDAD') {
                formData.append('es_a_toda_entidad', 'on');
            }
        }
        
        // Agregar CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (csrfToken) {
            formData.append('csrfmiddlewaretoken', csrfToken);
        }
        
        // Debug final
        console.log('FormData final antes de enviar:', {
            tipo: tipo,
            modoActual: modoActual,
            destinatario_oficina: formData.get('destinatario_oficina'),
            destinatario_usuario: formData.get('destinatario_usuario'),
            destinatario_proceso: formData.get('destinatario_proceso'),
            tipo_distribucion: formData.get('tipo_distribucion')
        });
        
        // Para responder, siempre enviar a aprobación
        if (modoActual === 'responder') {
            formData.append('save_send', '1');
        }

        fetch(endpoint, {
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
                // Mostrar mensaje de éxito
                const successMsg = data.message || 'Operación exitosa.';
                if (typeof window.showSuccess === 'function') {
                    window.showSuccess(successMsg);
                } else if (typeof showSuccess === 'function') {
                    showSuccess(successMsg);
                } else {
                    alert(successMsg);
                }
                
                // Cerrar el modal inmediatamente
                if (modalElement) {
                    const modal = bootstrap.Modal.getInstance(modalElement);
                    if (modal) {
                        modal.hide();
                    }
                }
                
                // Redirigir después de un breve delay para que el toast sea visible
                setTimeout(() => {
                    if (data.redirect_url) {
                        window.location.href = data.redirect_url;
                    } else {
                        window.location.reload();
                    }
                }, 800);
            } else {
                const errorMsg = 'Error: ' + (data.error || 'Ocurrió un error desconocido.');
                if (typeof window.showError === 'function') {
                    window.showError(errorMsg);
                } else if (typeof showError === 'function') {
                    showError(errorMsg);
                } else {
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
                alert('Error de conexión al enviar el formulario.');
            }
        })
        .finally(() => {
            form.dataset.submitting = '0';
            if (btnEnviar) btnEnviar.disabled = false;
        });
    }

    // Event listeners
    if (form) {
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            enviarFormulario();
        });
    }

})();

