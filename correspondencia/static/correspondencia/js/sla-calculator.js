/**
 * Calculadora de SLA para formularios de correspondencia
 * 
 * Calcula automáticamente plazos de respuesta basado en el tipo de trámite
 * seleccionado (TipoTramite.dias_respuesta).
 * 
 * Flujo:
 * 1. Usuario selecciona tipo de trámite
 * 2. JS consulta endpoint → obtiene dias_respuesta
 * 3. Si tiene plazo: activa "requiere respuesta", muestra panel SLA, oculta selector manual
 * 4. Si no tiene plazo: el usuario decide manualmente
 */

(function($) {
    'use strict';

    const SLA_CONFIG = {
        endpoint: '/registros/correspondencia/api/sla/calcular-plazo/',
        timeout: 10000,
        retryAttempts: 3
    };

    class SLACalculator {
        constructor(options = {}) {
            this.options = $.extend({}, SLA_CONFIG, options);
            this.currentRequest = null;
            this.currentContext = $(document);
            this.retryCount = 0;
            this.init();
        }

        init() {
            this.bindEvents();
        }

        resolveContext($ctx) {
            return $ctx && $ctx.length ? $ctx : $(document);
        }

        resolveEndpoint($trigger, $ctx) {
            const $context = this.resolveContext($ctx);
            const candidates = [
                $trigger,
                $context,
                $context.closest('.modal-content'),
                $context.closest('.modal').find('.modal-content').first(),
                $context.find('[data-sla-endpoint]').first(),
                $('.modal.show .modal-content[data-sla-endpoint]').first()
            ];

            for (let i = 0; i < candidates.length; i++) {
                const $candidate = candidates[i];
                if ($candidate && $candidate.length) {
                    const endpoint = $candidate.attr('data-sla-endpoint');
                    if (endpoint) {
                        return endpoint;
                    }
                }
            }

            return this.options.endpoint;
        }

        getCSRFToken($ctx) {
            const $context = this.resolveContext($ctx);
            const formToken = $context.find('input[name="csrfmiddlewaretoken"]').first().val();
            if (formToken) {
                return formToken;
            }

            const cookieMatch = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
            if (cookieMatch) {
                return decodeURIComponent(cookieMatch[1]);
            }

            return $('input[name="csrfmiddlewaretoken"]').first().val() || '';
        }

        bindEvents() {
            // Al cambiar tipo de trámite → consultar plazo y actualizar UI
            $(document).on('change', 'select[name*="tipo_tramite"]', (e) => {
                const $field = $(e.target);
                const $form = $field.closest('form');
                const codigo = $field.val();

                this.options.endpoint = this.resolveEndpoint($field, $form);

                if (codigo) {
                    this.checkTipoTramite(codigo, $form, $field);
                } else {
                    // Limpio la selección: ocultar panel, habilitar selector manual
                    this.hideSLAInfo($form);
                    this.hidePlazoBadge($form);
                    this.showTiempoRespuesta($form);
                }
            });

            // Toggle requiere respuesta
            $(document).on('change', 'input[type="checkbox"][name*="requiere_respuesta"]', (e) => {
                const $form = $(e.target).closest('form');
                this.toggleTiempoRespuesta($(e.target));
                const codigo = $form.find('select[name*="tipo_tramite"]').val();
                if ($(e.target).is(':checked') && codigo) {
                    this.calculateSLA(codigo, $form);
                } else if (!$(e.target).is(':checked')) {
                    this.hideSLAInfo($form);
                }
            });

        }

        // ─── Consulta de tipo de trámite ──────────────────────────────
        checkTipoTramite(codigo, $form, $trigger) {
            const $ctx = $form && $form.length ? $form : $(document);
            if (!codigo) {
                this.hidePlazoBadge($ctx);
                this.showTiempoRespuesta($ctx);
                return;
            }
            const self = this;
            const csrfToken = this.getCSRFToken($ctx);
            $.ajax({
                url: this.resolveEndpoint($trigger, $ctx),
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                data: {
                    tipo_tramite_codigo: codigo,
                    check_tipo_tramite: 'true',
                    csrfmiddlewaretoken: csrfToken
                },
                timeout: this.options.timeout,
                success(data) {
                    if (data && data.tiene_plazo && data.plazo_dias) {
                        // Tipo de trámite con plazo configurado
                        self.showPlazoBadge(data.plazo_dias, $ctx);
                        self.hideTiempoRespuesta($ctx);

                        // Activar checkbox automáticamente
                        const $cb = $ctx.find('input[name*="requiere_respuesta"]');
                        if ($cb.length && !$cb.is(':checked')) {
                            $cb.prop('checked', true).trigger('change');
                        } else {
                            // Si ya estaba checked, calcular de una vez
                            self.calculateSLA(codigo, $ctx);
                        }
                    } else {
                        // Sin plazo: usuario decide manual
                        self.hidePlazoBadge($ctx);
                        self.showTiempoRespuesta($ctx);
                        self.hideSLAInfo($ctx);
                    }
                },
                error(xhr, status, error) {
                    self.hidePlazoBadge($ctx);
                    self.showTiempoRespuesta($ctx);
                    self.hideSLAInfo($ctx);
                    console.error('SLA checkTipoTramite error:', status, error, xhr && xhr.status, xhr && xhr.responseText);
                }
            });
        }

        // ─── Cálculo SLA completo ─────────────────────────────────────
        calculateSLA(codigo, $form) {
            const $ctx = this.resolveContext($form);
            if (!codigo) { this.hideSLAInfo($ctx); return; }
            if (this.currentRequest) { this.currentRequest.abort(); }
            this.currentContext = $ctx;
            this.showLoading($ctx);
            this.retryCount = 0;
            this._doRequest(codigo, $ctx);
        }

        _doRequest(codigo, $ctx) {
            const self = this;
            const $form = this.resolveContext($ctx);
            const csrfToken = this.getCSRFToken($form);
            this.currentRequest = $.ajax({
                url: this.resolveEndpoint($form.find('select[name*="tipo_tramite"]').first(), $form),
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken
                },
                data: {
                    tipo_tramite_codigo: codigo,
                    requiere_respuesta: $form.find('input[name*="requiere_respuesta"]').is(':checked') ? 'true' : 'false',
                    csrfmiddlewaretoken: csrfToken
                },
                timeout: this.options.timeout,
                success(data) { self._onSuccess(data, $form); },
                error(xhr, status, err) { self._onError(xhr, status, err, codigo, $form); }
            });
        }

        _onSuccess(data, $ctx) {
            this.hideLoading($ctx);
            if (data && !data.error) {
                this.updateSLAInfo(data, $ctx);
                this.showSLAInfo($ctx);
            } else {
                this.showError(data && data.error ? data.error : 'Error desconocido', $ctx);
            }
        }

        _onError(xhr, status, error, codigo, $ctx) {
            if (status === 'abort') return;
            if (this.retryCount < this.options.retryAttempts) {
                this.retryCount++;
                setTimeout(() => this._doRequest(codigo, $ctx), 1000 * this.retryCount);
            } else {
                this.hideLoading($ctx);
                if (xhr && xhr.status === 403) {
                    this.showError('La sesión o el token CSRF expiró. Recargue la página e intente nuevamente.', $ctx);
                } else {
                    this.showError('Error de conexión al calcular plazo. Intente nuevamente.', $ctx);
                }
                console.error('SLA calculate error:', status, error, xhr && xhr.status, xhr && xhr.responseText);
            }
        }

        // ─── DOM: actualización del panel SLA ─────────────────────────
        updateSLAInfo(data, $ctx) {
            const $root = this.resolveContext($ctx);
            const set = (selector, val) => {
                const $el = $root.find(selector).first();
                if ($el.length) $el.text(val || '-');
            };
            set('#plazo-dias', data.plazo_dias);
            set('#fecha-limite', data.fecha_limite);
            set('#plazo-origen', data.plazo_origen);
            set('#corte-horario', data.corte_horario);

            // Colorear badge de días según urgencia
            const $badge = $root.find('#plazo-dias').first();
            $badge.removeClass('bg-primary bg-danger bg-warning bg-success');
            if (data.plazo_dias) {
                if (data.plazo_dias <= 3) $badge.addClass('bg-danger');
                else if (data.plazo_dias <= 5) $badge.addClass('bg-warning text-dark');
                else $badge.addClass('bg-primary');
            } else {
                $badge.addClass('bg-primary');
            }
        }

        showSLAInfo($ctx)  {
            const $root = this.resolveContext($ctx);
            $root.find('#sla-info').first().slideDown(200);
            $root.find('#sla-status').first().hide();
        }
        hideSLAInfo($ctx)  {
            const $root = this.resolveContext($ctx);
            $root.find('#sla-info').first().slideUp(200);
            $root.find('#sla-status').first().hide();
        }
        showLoading($ctx)  {
            const $root = this.resolveContext($ctx);
            $root.find('#sla-loading').first().show();
            $root.find('#sla-status').first().show();
            $root.find('#sla-message').first().text('Calculando plazo...');
        }
        hideLoading($ctx)  {
            this.resolveContext($ctx).find('#sla-loading').first().hide();
        }
        showError(msg, $ctx) {
            const $root = this.resolveContext($ctx);
            $root.find('#sla-loading').first().hide();
            $root.find('#sla-message').first().text(msg);
            $root.find('#sla-status').first().show();
            $root.find('#sla-info').first().hide();
        }
        showMessage(m, $ctx) {
            const $root = this.resolveContext($ctx);
            $root.find('#sla-message').first().text(m);
            $root.find('#sla-status').first().show();
        }

        // ─── Badge "Plazo automático" ─────────────────────────────────
        showPlazoBadge(dias, $ctx) {
            const $badge = this.resolveContext($ctx).find('#tipo-tramite-plazo-badge').first();
            if ($badge.length) {
                $badge.html('<i class="bi bi-clock-fill me-1"></i>Plazo: ' + dias + ' días hábiles').show();
            }
        }
        hidePlazoBadge($ctx) {
            this.resolveContext($ctx).find('#tipo-tramite-plazo-badge').first().hide();
        }

        // ─── Selector manual de tiempo_respuesta ──────────────────────
        hideTiempoRespuesta($form) {
            const $ctx = $form && $form.length ? $form : $(document);
            $ctx.find('select[name*="tiempo_respuesta"]').prop('disabled', true);
            $ctx.find('#div_id_radicar-tiempo_respuesta, #div_tiempo_respuesta').slideUp(200);
        }
        showTiempoRespuesta($form) {
            const $ctx = $form && $form.length ? $form : $(document);
            $ctx.find('select[name*="tiempo_respuesta"]').prop('disabled', false);
            $ctx.find('#div_id_radicar-tiempo_respuesta, #div_tiempo_respuesta').slideDown(200);
        }
        disableTiempoRespuesta() { $('select[name*="tiempo_respuesta"]').prop('disabled', true); }
        enableTiempoRespuesta()  { $('select[name*="tiempo_respuesta"]').prop('disabled', false); }

        toggleTiempoRespuesta($checkbox) {
            const $div = $checkbox.closest('form').find('[id*="tiempo_respuesta"]').closest('.mb-3');
            $checkbox.is(':checked') ? $div.slideDown(200) : $div.slideUp(200);
        }

        // ─── Validación de formulario ─────────────────────────────────
        validateForm($form) {
            const required = ['remitente', 'asunto', 'oficina_destino'];
            let valid = true;
            required.forEach(name => {
                const $f = $form.find(`[name*="${name}"]`);
                if (!$f.val()) { this.showFieldError($f, 'Este campo es obligatorio.'); valid = false; }
                else { this.clearFieldError($f); }
            });
            return valid;
        }

        showFieldError($f, msg) {
            this.clearFieldError($f);
            $f.after($('<div class="invalid-feedback d-block">').text(msg)).addClass('is-invalid');
        }
        clearFieldError($f) {
            $f.removeClass('is-invalid').siblings('.invalid-feedback').remove();
        }
    }

    $(document).ready(function() {
        window.slaCalculator = new SLACalculator();
    });

    window.SLACalculator = SLACalculator;

})(jQuery);
