/**
 * Modern DataTables JavaScript
 * Sistema de Gestión de Correspondencia - Hospital del Sarare
 */

window.ModernDataTables = (function() {
    'use strict';

    // Private variables
    let isInitialized = false;
    let tables = new Map();

    // Configuration
    const defaultConfig = {
        responsive: true,
        language: {
            url: '/static/correspondencia/datatables/es-ES.json'
        },
        // Estilo tipo Gmail: sin zebra striping
        stripeClasses: [],
        pageLength: 25,
        lengthMenu: [[10, 25, 50, 100, -1], [10, 25, 50, 100, "Todos"]],
        order: [[0, "desc"]],
        searching: false, // Oculta la caja de búsqueda por defecto
        columnDefs: [
            {
                targets: -1, // Last column (actions)
                orderable: false,
                searchable: false
            }
        ],
        // Eliminar la caja de búsqueda (f) del DOM
        dom: '<"row"<"col-sm-12 col-md-6"l>>' +
             '<"row"<"col-sm-12"tr>>' +
             '<"row"<"col-sm-12 col-md-5"i><"col-sm-12 col-md-7"p>>',
        initComplete: function() {
            // Add custom classes and styling
            this.api().columns.adjust();
        },
        drawCallback: function() {
            // Add custom styling after each draw
            addCustomStyling(this.api());
        }
    };

    // Private methods
    function addCustomStyling(table) {
        const container = table.table().container();
        if (!container || !container.parentNode) return;
        const wrapper = container.parentNode;
        
        // Add modern styling classes
        wrapper.classList.add('modern-datatable');
        
        // Style the table
        const tableElement = table.table().node();
        tableElement.classList.add('table-modern');
        
        // Hover visual now entirely controlled via CSS (Gmail-like)
    }

    function setupResponsiveHandling(table) {
        const container = table.table().container();
        if (!container || !container.parentNode) return;
        const wrapper = container.parentNode;
        
        // Handle responsive breakpoints
        function handleResponsive() {
            const isMobile = window.innerWidth <= 768;
            
            if (isMobile) {
                wrapper.classList.add('mobile-view');
            } else {
                wrapper.classList.remove('mobile-view');
            }
        }
        
        // Initial call
        handleResponsive();
        
        // Listen for resize events
        window.addEventListener('resize', handleResponsive);
    }

    function setupSearchEnhancement(table) {
        const container = table.table().container();
        if (!container) return;
        const searchInput = container.querySelector('.dataTables_filter input');
        
        if (searchInput) {
            // Add placeholder
            searchInput.setAttribute('placeholder', 'Buscar en la tabla...');
            
            // Add search icon
            const searchWrapper = searchInput.parentNode;
            searchWrapper.style.position = 'relative';
            
            const icon = document.createElement('i');
            icon.className = 'bi bi-search';
            icon.style.cssText = `
                position: absolute;
                left: 12px;
                top: 50%;
                transform: translateY(-50%);
                color: var(--gray-400);
                pointer-events: none;
            `;
            
            searchInput.style.paddingLeft = '40px';
            searchWrapper.appendChild(icon);
        }
    }

    function setupPaginationEnhancement(table) {
        const container = table.table().container();
        if (!container) return;
        const pagination = container.querySelector('.dataTables_paginate');
        
        if (pagination) {
            // Add modern pagination styling
            pagination.classList.add('pagination-modern');
            
            // Add page info
            const pageInfo = document.createElement('div');
            pageInfo.className = 'page-info';
            pageInfo.style.cssText = `
                text-align: center;
                margin-top: 1rem;
                color: var(--gray-600);
                font-size: 0.875rem;
            `;
            
            pagination.appendChild(pageInfo);
            
            // Update page info on page change
            table.on('page.dt', function() {
                const info = table.page.info();
                pageInfo.textContent = `Página ${info.page + 1} de ${info.pages}`;
            });
        }
    }

    function setupLoadingStates(table) {
        const container = table.table().container();
        if (!container || !container.parentNode) return;
        const wrapper = container.parentNode;
        
        // Show loading state
        function showLoading() {
            wrapper.classList.add('loading');
        }
        
        // Hide loading state
        function hideLoading() {
            wrapper.classList.remove('loading');
        }
        
        // Listen for processing events
        table.on('processing.dt', function(e, settings, processing) {
            if (processing) {
                showLoading();
            } else {
                hideLoading();
            }
        });
    }

    function setupAccessibility(table) {
        const tableElement = table.table().node();
        
        // Add ARIA labels
        tableElement.setAttribute('role', 'table');
        tableElement.setAttribute('aria-label', 'Tabla de datos');
        
        // Add ARIA labels to headers
        const headers = tableElement.querySelectorAll('thead th');
        headers.forEach((header, index) => {
            header.setAttribute('aria-label', `Columna ${index + 1}: ${header.textContent.trim()}`);
        });
        
        // Add keyboard navigation
        const rows = tableElement.querySelectorAll('tbody tr');
        rows.forEach(row => {
            row.setAttribute('tabindex', '0');
            row.setAttribute('role', 'row');
            
            row.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    const link = this.querySelector('a');
                    if (link) {
                        link.click();
                    }
                }
            });
        });
    }

    function setupExportFeatures(table) {
        // Add export buttons if needed
        const wrapper = table.table().container().parentNode;
        const header = wrapper.querySelector('.table-card-header');
        
        if (header) {
            const exportContainer = document.createElement('div');
            exportContainer.className = 'export-actions';
            exportContainer.style.cssText = `
                display: flex;
                gap: 0.5rem;
                align-items: center;
            `;
            
            // Add export buttons
            const exportButtons = [
                { text: 'CSV', icon: 'bi-file-earmark-text', action: 'csv' },
                { text: 'Excel', icon: 'bi-file-earmark-excel', action: 'excel' },
                { text: 'PDF', icon: 'bi-file-earmark-pdf', action: 'pdf' }
            ];
            
            exportButtons.forEach(btn => {
                const button = document.createElement('button');
                button.className = 'btn btn-sm btn-outline-secondary';
                button.innerHTML = `<i class="${btn.icon}"></i> ${btn.text}`;
                button.addEventListener('click', function() {
                    // Handle export functionality
                    console.log(`Exporting as ${btn.action}`);
                });
                exportContainer.appendChild(button);
            });
            
            header.appendChild(exportContainer);
        }
    }

    function setupMassSelection(table) {
        // Setup Gmail-like mass selection
        const selectAllCheckbox = document.getElementById('selectAllCheckbox');
        const massActionsToolbar = document.getElementById('massActionsToolbar');
        const selectedCountSpan = document.getElementById('selectedCount');
        
        if (!selectAllCheckbox || !massActionsToolbar) return;

        let selectedItems = new Set();

        // Select All checkbox handler
        selectAllCheckbox.addEventListener('change', function() {
            const rowCheckboxes = document.querySelectorAll('.row-checkbox');
            
            if (this.checked) {
                // Select all visible rows
                rowCheckboxes.forEach(checkbox => {
                    checkbox.checked = true;
                    selectedItems.add(checkbox.value);
                    const row = checkbox.closest('tr');
                    if (row) row.classList.add('selected');
                });
            } else {
                // Deselect all
                rowCheckboxes.forEach(checkbox => {
                    checkbox.checked = false;
                    selectedItems.delete(checkbox.value);
                    const row = checkbox.closest('tr');
                    if (row) row.classList.remove('selected');
                });
            }
            
            updateMassActionsUI();
        });

        // Individual row checkbox handlers
        function setupRowCheckboxes() {
            const rowCheckboxes = document.querySelectorAll('.row-checkbox');
            
            rowCheckboxes.forEach(checkbox => {
                checkbox.addEventListener('change', function() {
                    const row = this.closest('tr');
                    
                    if (this.checked) {
                        selectedItems.add(this.value);
                        row.classList.add('selected');
                    } else {
                        selectedItems.delete(this.value);
                        row.classList.remove('selected');
                        // Uncheck select all if any individual is unchecked
                        selectAllCheckbox.indeterminate = false;
                        selectAllCheckbox.checked = false;
                    }
                    
                    updateMassActionsUI();
                    updateSelectAllState();
                });
            });
        }

        function updateSelectAllState() {
            const rowCheckboxes = document.querySelectorAll('.row-checkbox');
            const checkedCount = document.querySelectorAll('.row-checkbox:checked').length;
            const totalCount = rowCheckboxes.length;

            if (checkedCount === 0) {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = false;
            } else if (checkedCount === totalCount) {
                selectAllCheckbox.checked = true;
                selectAllCheckbox.indeterminate = false;
            } else {
                selectAllCheckbox.checked = false;
                selectAllCheckbox.indeterminate = true;
            }
        }

        function updateMassActionsUI() {
            const count = selectedItems.size;
            
            if (count > 0) {
                massActionsToolbar.style.display = 'block';
                selectedCountSpan.textContent = count;
            } else {
                massActionsToolbar.style.display = 'none';
            }
        }

        // Mass action handlers
        document.getElementById('markAsReadBtn')?.addEventListener('click', function() {
            handleMassAction('mark_read');
        });

        document.getElementById('markAsUnreadBtn')?.addEventListener('click', function() {
            handleMassAction('mark_unread');
        });

        document.getElementById('shareSelectedBtn')?.addEventListener('click', function() {
            handleMassAction('share');
        });

        document.getElementById('deleteSelectedBtn')?.addEventListener('click', function() {
            handleMassAction('delete');
        });

        function handleMassAction(action) {
            const selectedIds = Array.from(selectedItems);
            
            if (selectedIds.length === 0) {
                alert('Por favor selecciona al menos un elemento.');
                return;
            }

            // Confirm action
            const actionNames = {
                'mark_read': 'marcar como leído',
                'mark_unread': 'marcar como no leído',
                'share': 'compartir',
                'delete': 'eliminar'
            };

            if (!confirm(`¿Estás seguro de que quieres ${actionNames[action]} ${selectedIds.length} elemento(s)?`)) {
                return;
            }

            // TODO: Implement actual mass actions via AJAX
            console.log(`Mass action: ${action}`, selectedIds);
            
            // For now, just show a message
            alert(`Acción "${actionNames[action]}" aplicada a ${selectedIds.length} elemento(s).`);
            
            // Clear selection
            selectedItems.clear();
            document.querySelectorAll('.row-checkbox').forEach(cb => {
                cb.checked = false;
                const row = cb.closest('tr');
                if (row) row.classList.remove('selected');
            });
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
            updateMassActionsUI();
        }

        // Setup row checkboxes on table draw
        setupRowCheckboxes();
        
        // Re-setup on DataTable draw
        table.on('draw.dt', function() {
            setupRowCheckboxes();
            selectedItems.clear();
            // Clear all selected row styles
            document.querySelectorAll('.dataTable tbody tr').forEach(row => {
                row.classList.remove('selected');
            });
            updateMassActionsUI();
            updateSelectAllState();
        });
    }

    function initializeTable(tableElement, customConfig = {}) {
        // Merge configurations
        const config = { ...defaultConfig, ...customConfig };
        
        // Initialize DataTable (avoid re-initialization)
        let table;
        if ($.fn.DataTable.isDataTable(tableElement)) {
            table = $(tableElement).DataTable();
        } else {
            table = $(tableElement).DataTable(config);
        }
        
        // Store table reference
        tables.set(tableElement, table);
        
        // Setup enhancements
        setupResponsiveHandling(table);
        setupSearchEnhancement(table);
        setupPaginationEnhancement(table);
        setupLoadingStates(table);
        setupAccessibility(table);
        setupExportFeatures(table);
        setupMassSelection(table);
        
        // Add custom event listeners
        table.on('draw.dt', function() {
            // Re-apply custom styling after each draw
            addCustomStyling(table);
            setupAccessibility(table);
        });
        
        return table;
    }

    // Public API
    return {
        init: function(selector = '.datatable-correspondencia', customConfig = {}) {
            if (isInitialized) return;
            
            const tableElements = document.querySelectorAll(selector);
            
            if (tableElements.length === 0) {
                // Silently return if no tables found - this is normal for some pages
                return;
            }
            
            tableElements.forEach(tableElement => {
                try {
                    initializeTable(tableElement, customConfig);
                } catch (error) {
                    console.error('Error initializing DataTable:', error);
                }
            });
            
            isInitialized = true;
            console.log(`Modern DataTables initialized: ${tableElements.length} table(s)`);
        },

        // Initialize specific table
        initTable: function(tableElement, customConfig = {}) {
            if (!tableElement) {
                console.error('Table element is required');
                return null;
            }
            
            return initializeTable(tableElement, customConfig);
        },

        // Get table instance
        getTable: function(tableElement) {
            return tables.get(tableElement);
        },

        // Destroy table
        destroyTable: function(tableElement) {
            const table = tables.get(tableElement);
            if (table) {
                table.destroy();
                tables.delete(tableElement);
            }
        },

        // Refresh table
        refreshTable: function(tableElement) {
            const table = tables.get(tableElement);
            if (table) {
                table.ajax.reload();
            }
        },

        // Get configuration
        getDefaultConfig: function() {
            return { ...defaultConfig };
        },

        // Utility methods
        isInitialized: function() {
            return isInitialized;
        },

        getTableCount: function() {
            return tables.size;
        }
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.ModernDataTables) {
        window.ModernDataTables.init();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.ModernDataTables;
} 