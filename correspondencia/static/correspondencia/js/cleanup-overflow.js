/**
 * Script para limpiar elementos desbordados en DataTables
 * Resuelve el problema de badges que aparecen fuera de la tabla
 */

(function($) {
    'use strict';

    function cleanupOverflowElements() {
        $('.datatable-correspondencia').each(function() {
            const $table = $(this);
            const tableRect = $table[0].getBoundingClientRect();
            
            // Limpiar badges y botones desbordados
            $table.find('.badge, .btn').each(function() {
                const $element = $(this);
                const $parent = $element.closest('td, th');
                const elementRect = this.getBoundingClientRect();
                
                // Ocultar elementos que están fuera del área de la tabla
                if (elementRect.right > tableRect.right + 5) {
                    $element.hide();
                    console.log('Elemento desbordado ocultado:', $element.text());
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
    }

    // Ejecutar limpieza cuando el DOM esté listo
    $(document).ready(function() {
        // Limpieza inicial
        setTimeout(cleanupOverflowElements, 1000);
        
        // Limpieza después de cada redibujado de DataTables
        $(document).on('draw.dt', function() {
            setTimeout(cleanupOverflowElements, 100);
        });
        
        // Limpieza en resize de ventana
        $(window).on('resize', function() {
            setTimeout(cleanupOverflowElements, 200);
        });
        
        // Limpieza periódica cada 5 segundos
        setInterval(cleanupOverflowElements, 5000);
    });

    // Exponer función globalmente
    window.cleanupOverflowElements = cleanupOverflowElements;

})(jQuery); 