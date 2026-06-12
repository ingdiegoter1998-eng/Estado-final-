/**
 * Blocklist de buzones institucionales de correspondencia (destinatarios prohibidos).
 */
(function(global) {
    'use strict';

    const EMAIL_IN_ANGLE = /<([^>]+)>/;

    function normalizeEmail(raw) {
        if (!raw) return '';
        let value = String(raw).trim();
        const match = value.match(EMAIL_IN_ANGLE);
        if (match) {
            value = match[1];
        }
        return value.trim().toLowerCase();
    }

    function parseBlockedEmails(raw) {
        if (!raw) return new Set();
        if (Array.isArray(raw)) {
            return new Set(raw.map(normalizeEmail).filter(Boolean));
        }
        return new Set(
            String(raw)
                .split(',')
                .map(normalizeEmail)
                .filter(Boolean)
        );
    }

    function readConfig(formEl) {
        const emailsRaw = (formEl && formEl.dataset.blockedRecipientEmails) || '';
        const message = (formEl && formEl.dataset.blockedRecipientMessage) || '';
        return {
            blocked: parseBlockedEmails(emailsRaw),
            message: message,
        };
    }

    function isBlockedEmail(email, blockedSet) {
        const normalized = normalizeEmail(email);
        return Boolean(normalized && blockedSet && blockedSet.has(normalized));
    }

    function blockedUserMessage(email, config) {
        const normalized = normalizeEmail(email);
        const base = (config && config.message) || (
            'No puede agregar {email} como destinatario: es la cuenta del sistema de ' +
            'correspondencia del hospital. Enviar copia ahí no llega al destinatario real ' +
            'y solo genera ruido en la bandeja institucional — como echarle agua al mar.'
        );
        if (base.includes('{email}')) {
            return base.replace('{email}', normalized || 'esta dirección');
        }
        return base;
    }

    function notifyBlocked(email, config) {
        const msg = blockedUserMessage(email, config);
        if (typeof global.showWarning === 'function') {
            global.showWarning(msg);
        } else if (typeof global.showError === 'function') {
            global.showError(msg);
        } else {
            alert(msg);
        }
    }

    function canAddRecipient(email, formEl) {
        const config = readConfig(formEl);
        if (!isBlockedEmail(email, config.blocked)) {
            return true;
        }
        notifyBlocked(email, config);
        return false;
    }

    function canAddContact(contact, formEl) {
        if (!contact) return false;
        return canAddRecipient(contact.email || contact.correo_electronico || '', formEl);
    }

    function findBlockedInSelection(contactosMap, emailsSet, formEl) {
        const config = readConfig(formEl);
        const blocked = [];
        if (contactosMap && typeof contactosMap.forEach === 'function') {
            contactosMap.forEach(function(contacto) {
                const email = (contacto && (contacto.email || contacto.correo_electronico)) || '';
                if (isBlockedEmail(email, config.blocked)) {
                    blocked.push(normalizeEmail(email));
                }
            });
        }
        if (emailsSet && typeof emailsSet.forEach === 'function') {
            emailsSet.forEach(function(email) {
                if (isBlockedEmail(email, config.blocked)) {
                    blocked.push(normalizeEmail(email));
                }
            });
        }
        return blocked;
    }

    global.CorrespondenciaBlockedRecipients = {
        normalizeEmail: normalizeEmail,
        parseBlockedEmails: parseBlockedEmails,
        readConfig: readConfig,
        isBlockedEmail: isBlockedEmail,
        blockedUserMessage: blockedUserMessage,
        notifyBlocked: notifyBlocked,
        canAddRecipient: canAddRecipient,
        canAddContact: canAddContact,
        findBlockedInSelection: findBlockedInSelection,
    };
})(window);
