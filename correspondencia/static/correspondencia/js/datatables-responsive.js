/**
 * Mejoras responsive para DataTables
 * Optimiza la experiencia en dispositivos móviles y tablets
 */

(function($) {
    'use strict';

    // Configuración global para DataTables responsive
    const DataTablesResponsiveConfig = {
        // Configuración responsive mejorada
        responsive: {
            details: {
                display: $.fn.dataTable.Responsive.display.modal({
                    header: function(row) {
                        const data = row.data();
                        return `<div class="dtr-modal-header">
                                    <h5 class="mb-0">Detalles de Correspondencia</h5>
                                    <button type="button" class="dtr-modal-close" data-bs-dismiss="modal" aria-label="Cerrar">
                                        <i class="bi bi-x-lg"></i>
                                    </button>
                                </div>`;
                    }
                }),
                renderer: $.fn.dataTable.Responsive.renderer.tableAll({
                    tableClass: 'table table-sm table-bordered'
                })
            },
            // Configuración para evitar columnas extra
            breakpoints: [
                { name: 'desktop', width: Infinity },
                { name: 'tablet', width: 1024 },
                { name: 'mobile', width: 768 }
            ]
        },
        
        // Configuración de scroll
        scrollY: 'calc(100vh - 350px)',
        scrollCollapse: true,
        scrollX: true,
        autoWidth: false,
        fixedHeader: true,
        fixedColumns: {
            left: 1, // Fijar la primera columna (fecha)
            right: 1  // Fijar la última columna (acciones)
        },
        
        // Configuración de paginación
        paging: true,
        pageLength: 15,
        lengthMenu: [[10, 15, 25, 50, -1], [10, 15, 25, 50, "Todos"]],
        
        // Configuración de búsqueda y ordenamiento
        searching: true,
        ordering: true,
        info: true,
        lengthChange: true,
        
        // Configuración de idioma
        language: {
            "search": "Buscar:",
            "lengthMenu": "Mostrar _MENU_ registros",
            "info": "Mostrando _START_ a _END_ de _TOTAL_ registros",
            "infoEmpty": "Mostrando 0 a 0 de 0 registros",
            "infoFiltered": "(filtrado de _MAX_ registros totales)",
            "paginate": {
                "first": "<<",
                "last": ">>",
                "next": ">",
                "previous": "<"
            },
            "zeroRecords": "No se encontraron resultados",
            "emptyTable": "No hay datos disponibles en esta tabla",
            "loadingRecords": "Cargando...",
            "processing": "Procesando...",
            "aria": {
                "sortAscending": ": activar para ordenar ascendentemente",
                "sortDescending": ": activar para ordenar descendentemente"
            },
            "responsive": {
                "details": {
                    "display": "Mostrar detalles",
                    "type": "column"
                }
            }
        },
        
        // Configuración de columnas responsive
        columnDefs: [
            {
                responsivePriority: 1,
                targets: [1, 3], // Número Radicado y Asunto siempre visibles
                className: 'text-nowrap'
            },
            {
                responsivePriority: 2,
                targets: 0, // Fecha
                className: 'text-nowrap'
            },
            {
                responsivePriority: 3,
                targets: 2, // Remitente
                className: 'text-truncate'
            },
            {
                responsivePriority: 4,
                targets: 4, // Estado Lectura
                className: 'text-center'
            },
            {
                responsivePriority: 5,
                targets: 5, // Estado Plazo
                className: 'text-center'
            },
            {
                responsivePriority: 6,
                targets: 6, // Días Restantes
                className: 'text-center'
            },
            {
                responsivePriority: 7,
                targets: 7, // Asignado Inicial (solo en bandeja oficina)
                className: 'text-truncate',
                visible: function() {
                    return $(this).find('thead th').length === 9;
                }
            },
            {
                responsivePriority: 8,
                targets: function() {
                    const columnCount = $(this).find('thead th').length;
                    return columnCount === 8 ? 7 : 8; // Acciones
                },
                className: 'text-center'
            }
        ],
        
        // Configuración del DOM
        dom: '<"row"<"col-sm-12 col-md-6"l><"col-sm-12 col-md-6"f>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        
        // Callback de inicialización
        initComplete: function(settings, json) {
            const table = this;
            const wrapper = $(table).closest('.dataTables_wrapper');
            
            // Verificar y corregir discrepancias de columnas
            const headerColumns = $(table).find('thead th').length;
            const bodyColumns = $(table).find('tbody tr:first-child td').length;
            
            if (headerColumns !== bodyColumns) {
                console.warn(`DataTables: Discrepancia de columnas detectada. Header: ${headerColumns}, Body: ${bodyColumns}`);
                
                // Ajustar automáticamente si es posible
                if (bodyColumns > headerColumns) {
                    // Agregar columnas faltantes al header
                    for (let i = headerColumns; i < bodyColumns; i++) {
                        $(table).find('thead tr').append('<th></th>');
                    }
                }
            }
            
            // Agregar clases CSS para mejor apariencia
            wrapper.addClass('datatable-wrapper');
            
            // Añadir tooltips a los botones de acción
            $(table).find('.btn[title]').each(function() {
                if (!$(this).data('bs-toggle')) {
                    $(this).attr('data-bs-toggle', 'tooltip');
                }
            });
            
            // Limpiar elementos desbordados que puedan causar badges flotantes
            $(table).find('.badge, .btn').each(function() {
                const $element = $(this);
                const $parent = $element.closest('td, th');
                
                // Si el elemento está fuera de su contenedor, ocultarlo
                if ($parent.length && ($element.offset().left > $parent.offset().left + $parent.width())) {
                    $element.hide();
                }
                
                // Forzar que los badges no excedan el ancho de su contenedor
                if ($parent.length) {
                    const parentWidth = $parent.width();
                    const elementWidth = $element.outerWidth();
                    
                    if (elementWidth > parentWidth) {
                        $element.css({
                            'max-width': (parentWidth - 4) + 'px',
                            'overflow': 'hidden',
                            'text-overflow': 'ellipsis',
                            'white-space': 'nowrap'
                        });
                    }
                }
            });
            
            // Limpiar cualquier elemento que esté fuera del área de la tabla
            const tableRect = $(table)[0].getBoundingClientRect();
            $(table).find('.badge, .btn').each(function() {
                const elementRect = this.getBoundingClientRect();
                
                if (elementRect.right > tableRect.right + 10) {
                    $(this).hide();
                }
            });
            
            // Ajustar altura del scroll según el viewport
            const adjustScrollHeight = () => {
                const viewportHeight = window.innerHeight;
                const headerHeight = $('.main-header').outerHeight() || 80;
                const controlsHeight = wrapper.find('.dataTables_length, .dataTables_filter, .dataTables_info, .dataTables_paginate').outerHeight() || 120;
                const padding = 50;
                const newHeight = Math.max(200, viewportHeight - headerHeight - controlsHeight - padding);
                
                if (table.scroller) {
                    table.scroller.y(newHeight);
                }
            };
            
            // Ajustar altura inicial y en resize
            adjustScrollHeight();
            $(window).on('resize', adjustScrollHeight);
            
            // Mejorar responsive en móviles
            if (window.innerWidth <= 768) {
                if (table.responsive) {
                    table.responsive.recalc();
                }
            }
            
            // Agregar efectos de carga
            wrapper.closest('.table-container').removeClass('loading');
        }
    };

    // Función para inicializar DataTables con configuración responsive
    function initResponsiveDataTable(selector, customConfig = {}) {
        const config = $.extend(true, {}, DataTablesResponsiveConfig, customConfig);
        
        // Agregar clase de carga
        $(selector).closest('.table-container').addClass('loading');
        
        // Inicializar DataTable
        const table = $(selector).DataTable(config);
        
        // Configurar eventos adicionales
        $(selector).on('draw.dt', function() {
            // Recalcular responsive después de cada redibujado
            if (table.responsive) {
                table.responsive.recalc();
            }
            
            // Actualizar tooltips
            $(this).find('.btn[title]').each(function() {
                if (!$(this).data('bs-toggle')) {
                    $(this).attr('data-bs-toggle', 'tooltip');
                }
            });
            
            // Limpiar elementos desbordados después de cada redibujado
            setTimeout(() => {
                $(this).find('.badge, .btn').each(function() {
                    const $element = $(this);
                    const $parent = $element.closest('td, th');
                    
                    if ($parent.length && ($element.offset().left > $parent.offset().left + $parent.width())) {
                        $element.hide();
                    }
                    
                    // Forzar contención de elementos
                    if ($parent.length) {
                        const parentWidth = $parent.width();
                        const elementWidth = $element.outerWidth();
                        
                        if (elementWidth > parentWidth) {
                            $element.css({
                                'max-width': (parentWidth - 4) + 'px',
                                'overflow': 'hidden',
                                'text-overflow': 'ellipsis',
                                'white-space': 'nowrap'
                            });
                        }
                    }
                });
                
                // Limpiar elementos fuera del área de la tabla
                const tableRect = $(this)[0].getBoundingClientRect();
                $(this).find('.badge, .btn').each(function() {
                    const elementRect = this.getBoundingClientRect();
                    
                    if (elementRect.right > tableRect.right + 10) {
                        $(this).hide();
                    }
                });
            }, 100);
        });
        
        return table;
    }

    // Función para ajustar el layout en diferentes breakpoints
    function adjustLayoutForBreakpoint() {
        const width = window.innerWidth;
        const tables = $('.datatable-correspondencia').DataTable();
        
        tables.each(function() {
            const table = this;
            
            if (width <= 576) {
                // Móviles pequeños: mostrar menos columnas
                if (table.responsive) {
                    table.responsive.recalc();
                }
            } else if (width <= 768) {
                // Móviles: ajustar columnas
                if (table.responsive) {
                    table.responsive.recalc();
                }
            } else if (width <= 1024) {
                // Tablets: mostrar más columnas
                if (table.responsive) {
                    table.responsive.recalc();
                }
            } else {
                // Desktop: mostrar todas las columnas
                if (table.responsive) {
                    table.responsive.recalc();
                }
            }
        });
    }

    // Inicializar cuando el DOM esté listo
    $(document).ready(function() {
        // Inicializar todas las tablas con clase datatable-correspondencia
        $('.datatable-correspondencia').each(function() {
            initResponsiveDataTable(this);
        });
        
        // Limpiar elementos desbordados después de un breve delay
        setTimeout(() => {
            $('.datatable-correspondencia').each(function() {
                const $table = $(this);
                const tableRect = $table[0].getBoundingClientRect();
                
                $table.find('.badge, .btn').each(function() {
                    const $element = $(this);
                    const $parent = $element.closest('td, th');
                    const elementRect = this.getBoundingClientRect();
                    
                    // Ocultar elementos fuera del área de la tabla
                    if (elementRect.right > tableRect.right + 10) {
                        $element.hide();
                    }
                    
                    // Forzar contención en celdas
                    if ($parent.length) {
                        const parentWidth = $parent.width();
                        const elementWidth = $element.outerWidth();
                        
                        if (elementWidth > parentWidth) {
                            $element.css({
                                'max-width': (parentWidth - 4) + 'px',
                                'overflow': 'hidden',
                                'text-overflow': 'ellipsis',
                                'white-space': 'nowrap'
                            });
                        }
                    }
                });
            });
        }, 500);
        
        // Ajustar layout en resize
        let resizeTimer;
        $(window).on('resize', function() {
            clearTimeout(resizeTimer);
            resizeTimer = setTimeout(function() {
                adjustLayoutForBreakpoint();
            }, 250);
        });
        
        // Ajustar layout inicial
        adjustLayoutForBreakpoint();
        
        // Mejorar la experiencia móvil
        if (window.innerWidth <= 768) {
            // Agregar swipe gestures para navegación
            $('.dataTables_scrollBody').on('touchstart', function(e) {
                const touch = e.originalEvent.touches[0];
                $(this).data('touchStartX', touch.clientX);
            });
            
            $('.dataTables_scrollBody').on('touchend', function(e) {
                const touch = e.originalEvent.changedTouches[0];
                const startX = $(this).data('touchStartX');
                const endX = touch.clientX;
                const diffX = startX - endX;
                
                if (Math.abs(diffX) > 50) {
                    // Swipe detectado
                    const table = $(this).closest('.datatable-correspondencia').DataTable();
                    if (diffX > 0) {
                        // Swipe izquierda: siguiente página
                        if (table.page.info().page < table.page.info().pages - 1) {
                            table.page('next').draw('page');
                        }
                    } else {
                        // Swipe derecha: página anterior
                        if (table.page.info().page > 0) {
                            table.page('previous').draw('page');
                        }
                    }
                }
            });
        }
    });

    // Exponer funciones globalmente
    window.DataTablesResponsive = {
        init: initResponsiveDataTable,
        adjustLayout: adjustLayoutForBreakpoint
    };

})(jQuery); 