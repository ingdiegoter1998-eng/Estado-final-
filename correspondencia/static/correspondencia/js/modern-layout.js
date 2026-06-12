/**
 * Modern Layout JavaScript
 * Sistema de Gestión de Correspondencia - Hospital del Sarare
 */

window.ModernLayout = (function() {
    'use strict';

    // Private variables
    let isInitialized = false;

    // Configuration
    const config = {
        transitionDuration: 300
    };

    function setupEventListeners() {
        setupActiveLinks();
    }

    function setupActiveLinks() {
        const currentPath = window.location.pathname;
        const welcomeUrl = '/registros/welcome/';

        document.querySelectorAll('.sidebar .nav-link').forEach(link => {
            const linkPath = link.getAttribute('href');
            
            if (linkPath && linkPath !== '#' && currentPath.startsWith(linkPath)) {
                let blockActivation = false;
                
                // Special handling for welcome page
                if (linkPath === welcomeUrl && currentPath !== welcomeUrl) {
                    document.querySelectorAll('.sidebar .nav-link').forEach(otherLink => {
                        const otherPath = otherLink.getAttribute('href');
                        if (otherPath && otherPath !== welcomeUrl && otherPath !== '#' && currentPath.startsWith(otherPath)) {
                            blockActivation = true;
                        }
                    });
                }
                
                if (!blockActivation) {
                    document.querySelectorAll('.sidebar .nav-link').forEach(l => l.classList.remove('active'));
                    link.classList.add('active');
                } else {
                    link.classList.remove('active');
                }
            } else if (linkPath && linkPath !== '#') {
                link.classList.remove('active');
            }
        });

        // Fallback for welcome page
        if (document.querySelectorAll('.sidebar .nav-link.active').length === 0 && currentPath === welcomeUrl) {
            const welcomeLink = document.querySelector(`.sidebar .nav-link[href="${welcomeUrl}"]`);
            if (welcomeLink) {
                welcomeLink.classList.add('active');
            }
        }
    }

    function initializeTooltips() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.forEach(tooltipTriggerEl => {
            new bootstrap.Tooltip(tooltipTriggerEl, {
                placement: 'top',
                trigger: 'hover',
                animation: true
            });
        });
    }

    function setupAccessibility() {
        // Add aria-labels to buttons without text
        document.querySelectorAll('.btn').forEach(btn => {
            if (!btn.getAttribute('aria-label')) {
                const text = btn.textContent.trim();
                if (text) {
                    btn.setAttribute('aria-label', text);
                }
            }
        });

        // Add focus management
        document.querySelectorAll('a, button, input, select, textarea').forEach(element => {
            element.addEventListener('focus', function() {
                this.style.outline = '2px solid var(--primary-color)';
                this.style.outlineOffset = '2px';
            });

            element.addEventListener('blur', function() {
                this.style.outline = '';
                this.style.outlineOffset = '';
            });
        });
    }

    function addLoadingEffects() {
        document.querySelectorAll('.table-container').forEach(container => {
            container.classList.add('loading');
            setTimeout(() => {
                container.classList.remove('loading');
            }, 500);
        });
    }

    // Public API
    return {
        init: function() {
            if (isInitialized) return;

            setupEventListeners();
            
            // Initialize tooltips
            initializeTooltips();
            
            // Setup accessibility
            setupAccessibility();
            
            // Add loading effects
            addLoadingEffects();
            
            isInitialized = true;
            
            console.log('Modern Layout initialized successfully');
        },

        getConfig: function() {
            return { ...config };
        }
    };
})();

// Auto-initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    if (window.ModernLayout) {
        window.ModernLayout.init();
    }
});

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = window.ModernLayout;
} 