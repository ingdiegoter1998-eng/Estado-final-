/**
 * Mensajes claros para envíos AJAX de salida/respuesta con adjuntos (multipart).
 */
(function (global) {
    'use strict';

    function mensajeLimiteAdjuntos(adjuntosMb) {
        return (
            `Los adjuntos superan el límite permitido (máx. ${adjuntosMb} MB en total). ` +
            'Si usa un archivo .zip u otros comprimidos, redúzcalo o comparta un enlace de Drive en el cuerpo del mensaje.'
        );
    }

    async function parseJsonResponse(response) {
        const contentType = response.headers.get('content-type') || '';
        if (!contentType.includes('application/json')) {
            const err = new Error('Respuesta no JSON del servidor');
            err.userMessage =
                'El servidor rechazó la carga del formulario. Si adjuntó un .zip u otros archivos pesados, ' +
                'verifique que el total no supere el límite indicado en el formulario.';
            throw err;
        }
        try {
            return await response.json();
        } catch (parseError) {
            const err = new Error('JSON inválido');
            err.userMessage =
                'No se pudo interpretar la respuesta del servidor. Si adjuntó archivos grandes (.zip), ' +
                'es probable que hayan superado el límite de carga.';
            err.cause = parseError;
            throw err;
        }
    }

    async function parseOutboundAjaxResponse(response, options) {
        const adjuntosMb = options && options.adjuntosMb != null ? options.adjuntosMb : 25;

        if (response.status === 413) {
            const err = new Error('Payload too large');
            err.userMessage = mensajeLimiteAdjuntos(adjuntosMb);
            throw err;
        }

        if (!response.ok) {
            let detail = '';
            const contentType = response.headers.get('content-type') || '';
            if (contentType.includes('application/json')) {
                try {
                    const data = await response.json();
                    detail = data.error || data.detail || '';
                } catch (_) {
                    /* respuesta JSON malformada */
                }
            }
            const err = new Error(detail || `HTTP ${response.status}`);
            err.userMessage = detail
                ? `Error: ${detail}`
                : `El servidor respondió con un error (${response.status}). Intente de nuevo.`;
            throw err;
        }

        return parseJsonResponse(response);
    }

    function mensajeErrorEnvioFormulario(error, options) {
        if (error && error.userMessage) {
            return error.userMessage;
        }
        const adjuntosMb = options && options.adjuntosMb != null ? options.adjuntosMb : 25;
        if (error && error.name === 'TypeError') {
            return (
                `No se pudo completar el envío. Verifique su conexión y que los adjuntos ` +
                `(incluidos .zip) no superen ${adjuntosMb} MB en total.`
            );
        }
        return (
            `No se pudo enviar el formulario. Si adjuntó un archivo .zip u otros archivos pesados, ` +
            `compruebe que el total no supere ${adjuntosMb} MB o use un enlace de Drive en el cuerpo del mensaje.`
        );
    }

    global.CorrespondenciaOutboundAjax = {
        parseOutboundAjaxResponse: parseOutboundAjaxResponse,
        mensajeErrorEnvioFormulario: mensajeErrorEnvioFormulario,
        mensajeLimiteAdjuntos: mensajeLimiteAdjuntos,
    };
})(typeof window !== 'undefined' ? window : globalThis);
