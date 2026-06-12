(function () {
    const roots = document.querySelectorAll('[data-chatbot-root]');
    if (!roots.length) {
        return;
    }

    function getCsrfToken() {
        const cookie = document.cookie.split('; ').find((item) => item.startsWith('csrftoken='));
        return cookie ? decodeURIComponent(cookie.split('=')[1]) : '';
    }

    function escapeHtml(value) {
        return (value || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }

    function normalizeAssistantText(value) {
        return (value || '')
            .replace(/\*\*(.*?)\*\*/g, '$1')
            .replace(/^\s*\*\s+/gm, '- ')
            .replace(/^\s*[-•]\s+/gm, '- ')
            .replace(/\n{3,}/g, '\n\n')
            .trim();
    }

    function timeAgo(iso) {
        var diff = (Date.now() - new Date(iso).getTime()) / 1000;
        if (diff < 60) return 'ahora';
        if (diff < 3600) return Math.floor(diff / 60) + ' min';
        if (diff < 86400) return Math.floor(diff / 3600) + ' h';
        return Math.floor(diff / 86400) + ' d';
    }

    function renderBubble(message) {
        const wrapper = document.createElement('article');
        wrapper.className = `chatbot-bubble ${message.role === 'user' ? 'is-user' : 'is-assistant'}`;

        const createdAt = new Date(message.created_at).toLocaleString('es-CO');
        const displayContent = message.role === 'assistant'
            ? normalizeAssistantText(message.content)
            : (message.content || '');

        wrapper.innerHTML = `
            <div class="chatbot-bubble-head">
                <strong>${message.role === 'user' ? 'Tú' : 'Asistente'}</strong>
                <span>${createdAt}</span>
            </div>
            <div class="chatbot-bubble-body">${escapeHtml(displayContent)}</div>
        `;
        return wrapper;
    }

    function renderThinkingBubble() {
        const wrapper = document.createElement('article');
        wrapper.className = 'chatbot-bubble is-assistant is-thinking';
        wrapper.setAttribute('data-thinking-bubble', 'true');
        wrapper.setAttribute('aria-live', 'polite');
        wrapper.innerHTML = `
            <div class="chatbot-bubble-head">
                <strong>Asistente</strong>
                <span>Ahora</span>
            </div>
            <div class="chatbot-bubble-body chatbot-thinking-body">
                <span class="chatbot-thinking-dots" aria-hidden="true">
                    <span></span>
                    <span></span>
                    <span></span>
                </span>
                <span class="chatbot-thinking-label">Pensando…</span>
            </div>
        `;
        return wrapper;
    }

    function renderSupportBubble(msg) {
        const wrapper = document.createElement('article');
        wrapper.className = 'chatbot-bubble chatbot-support-bubble ' + (msg.es_admin ? 'is-admin' : 'is-user');

        const timeStr = new Date(msg.creado).toLocaleTimeString('es-CO', { hour: '2-digit', minute: '2-digit' });
        let adjuntosHtml = '';
        if (msg.adjuntos && msg.adjuntos.length > 0) {
            adjuntosHtml = '<div class="chatbot-support-attachments">' +
                msg.adjuntos.map(function (a) {
                    return '<img src="' + escapeHtml(a.url) + '" alt="' + escapeHtml(a.nombre) + '" class="chatbot-support-thumb" data-lightbox-src="' + escapeHtml(a.url) + '">';
                }).join('') + '</div>';
        }

        wrapper.innerHTML =
            '<div class="chatbot-bubble-head">' +
                '<strong>' + escapeHtml(msg.autor || 'Sistema') + '</strong>' +
                '<span>' + timeStr + '</span>' +
            '</div>' +
            '<div class="chatbot-bubble-body">' + escapeHtml(msg.texto) + '</div>' +
            adjuntosHtml;

        return wrapper;
    }

    async function fetchJson(url, options) {
        const response = await fetch(url, options);
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'No fue posible completar la operación.');
        }
        return data;
    }

    async function apiFetchSupport(url, opts) {
        opts = opts || {};
        var isFormData = opts.body instanceof FormData;
        var headers = Object.assign({
            'Accept': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest',
        }, !isFormData ? { 'Content-Type': 'application/json' } : {}, opts.headers || {});
        var response = await fetch(url, Object.assign({}, opts, { headers: headers, credentials: 'same-origin' }));
        var data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Error en la operación');
        }
        return data;
    }

    function buildConversationUrl(template, conversationId) {
        return template.replace('/0/', `/${conversationId}/`);
    }

    roots.forEach(function initializeChatbot(root) {
        if (root.dataset.chatbotInitialized === 'true') {
            return;
        }
        root.dataset.chatbotInitialized = 'true';

        // ═══════════════════════════════════════════════════════
        // AI CHATBOT (existing)
        // ═══════════════════════════════════════════════════════
        const conversationList = root.querySelector('[data-conversation-list]');
        const messageList = root.querySelector('[data-message-list]');
        const form = root.querySelector('[data-chat-form]');
        const input = root.querySelector('[data-question-input]');
        const status = root.querySelector('[data-chat-status]');
        const submitButton = root.querySelector('[data-submit-button]');
        const chatTitle = root.querySelector('[data-chat-title]');
        const newConversationButton = root.querySelector('[data-action="new-conversation"]');
        const expandButton = root.querySelector('[data-chatbot-expand-toggle]');
        const sidebarButton = root.querySelector('[data-chatbot-sidebar-toggle]');
        const modalElement = root.closest('.chatbot-modal');

        if (!conversationList || !messageList || !form || !input || !status || !submitButton || !chatTitle || !newConversationButton) {
            return;
        }

        const endpoints = {
            conversations: root.dataset.conversationsUrl,
            create: root.dataset.createUrl,
            messagesTemplate: root.dataset.messagesUrlTemplate,
            askTemplate: root.dataset.askUrlTemplate,
        };

        let currentConversationId = null;
        let activeThinkingBubble = null;

        function setStatus(text) {
            status.textContent = text;
        }

        function scrollMessagesToBottom() {
            messageList.scrollTop = messageList.scrollHeight;
        }

        function clearThinkingBubble() {
            if (activeThinkingBubble && activeThinkingBubble.isConnected) {
                activeThinkingBubble.remove();
            }
            activeThinkingBubble = null;
        }

        function showThinkingBubble() {
            clearThinkingBubble();
            activeThinkingBubble = renderThinkingBubble();
            messageList.appendChild(activeThinkingBubble);
            scrollMessagesToBottom();
        }

        function renderConversationItem(conversation) {
            const button = document.createElement('button');
            button.type = 'button';
            button.className = 'chatbot-conversation-item';
            button.dataset.conversationId = conversation.id;
            button.innerHTML = `
                <strong>${conversation.title}</strong>
                <small>${new Date(conversation.updated_at).toLocaleString('es-CO')}</small>
            `;
            button.addEventListener('click', function () {
                loadConversation(conversation.id);
            });
            return button;
        }

        function syncExpandButton() {
            if (!expandButton || !modalElement) {
                return;
            }
            const icon = expandButton.querySelector('i');
            const label = expandButton.querySelector('span');
            const expanded = modalElement.classList.contains('is-expanded');
            expandButton.setAttribute('aria-pressed', expanded ? 'true' : 'false');
            if (label) {
                label.textContent = expanded ? 'Contraer' : 'Expandir';
            }
            if (icon) {
                icon.className = expanded ? 'bi bi-fullscreen-exit' : 'bi bi-arrows-angle-expand';
            }
        }

        function getActiveTabContent() {
            return root.querySelector('.chatbot-tab-content.is-active');
        }

        function syncSidebarButton() {
            if (!sidebarButton) {
                return;
            }
            const icon = sidebarButton.querySelector('i');
            const label = sidebarButton.querySelector('span');
            const activeContent = getActiveTabContent();
            const collapsed = activeContent ? activeContent.classList.contains('is-sidebar-collapsed') : false;
            sidebarButton.setAttribute('aria-pressed', collapsed ? 'true' : 'false');
            if (label) {
                label.textContent = collapsed ? 'Mostrar sesiones' : 'Sesiones';
            }
            if (icon) {
                icon.className = collapsed ? 'bi bi-layout-sidebar' : 'bi bi-layout-sidebar-inset';
            }
        }

        async function refreshConversationList(selectedId) {
            const data = await fetchJson(endpoints.conversations, { headers: { 'X-Requested-With': 'XMLHttpRequest' } });
            conversationList.innerHTML = '';

            if (!data.results.length) {
                conversationList.innerHTML = '<div class="chatbot-empty-sidebar"><i class="bi bi-chat-left-text"></i><p>Aún no hay conversaciones guardadas.</p></div>';
                return;
            }

            data.results.forEach((conversation) => {
                const item = renderConversationItem(conversation);
                if (conversation.id === selectedId) {
                    item.classList.add('is-active');
                }
                conversationList.appendChild(item);
            });
        }

        async function createConversation() {
            setStatus('Creando conversación...');
            const data = await fetchJson(endpoints.create, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest',
                },
            });
            currentConversationId = data.conversation.id;
            await refreshConversationList(currentConversationId);
            await loadConversation(currentConversationId);
            setStatus('Conversación lista.');
        }

        async function loadConversation(conversationId) {
            currentConversationId = conversationId;
            setStatus('Cargando conversación...');
            const data = await fetchJson(buildConversationUrl(endpoints.messagesTemplate, conversationId), {
                headers: { 'X-Requested-With': 'XMLHttpRequest' },
            });

            chatTitle.textContent = data.conversation.title;
            messageList.innerHTML = '';
            if (!data.messages.length) {
                messageList.innerHTML = '<div class="chatbot-empty-state"><i class="bi bi-stars"></i><h5>Conversación vacía</h5><p>Haz una pregunta para comenzar.</p></div>';
            } else {
                data.messages.forEach((message) => {
                    messageList.appendChild(renderBubble(message));
                });
            }

            await refreshConversationList(currentConversationId);
            clearThinkingBubble();
            scrollMessagesToBottom();
            setStatus('Listo para consultar.');
        }

        async function askQuestion(event) {
            event.preventDefault();
            const question = input.value.trim();
            if (!question) {
                setStatus('Escribe una pregunta antes de enviar.');
                return;
            }

            if (!currentConversationId) {
                await createConversation();
            }

            submitButton.disabled = true;
            input.disabled = true;
            setStatus('El asistente está pensando...');

            try {
                if (messageList.querySelector('.chatbot-empty-state')) {
                    messageList.innerHTML = '';
                }

                messageList.appendChild(renderBubble({
                    role: 'user',
                    content: question,
                    created_at: new Date().toISOString(),
                    citations: [],
                }));
                showThinkingBubble();

                var minDelay = new Promise(function (r) { setTimeout(r, 1200); });
                var fetchPromise = fetchJson(buildConversationUrl(endpoints.askTemplate, currentConversationId), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken(),
                        'X-Requested-With': 'XMLHttpRequest',
                    },
                    body: JSON.stringify({ question }),
                });

                var results = await Promise.all([fetchPromise, minDelay]);
                var data = results[0];

                chatTitle.textContent = data.conversation.title;
                clearThinkingBubble();
                messageList.appendChild(renderBubble(data.assistant_message));
                input.value = '';
                scrollMessagesToBottom();
                await refreshConversationList(currentConversationId);
                setStatus('Respuesta generada.');
            } catch (error) {
                clearThinkingBubble();
                setStatus(error.message);
            } finally {
                submitButton.disabled = false;
                input.disabled = false;
                input.focus();
            }
        }

        newConversationButton.addEventListener('click', createConversation);
        form.addEventListener('submit', askQuestion);

        input.addEventListener('input', function () {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });

        input.addEventListener('keydown', function (e) {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                form.dispatchEvent(new Event('submit', { cancelable: true }));
            }
        });

        root.querySelectorAll('[data-suggestion]').forEach(function (btn) {
            btn.addEventListener('click', function () {
                input.value = btn.textContent.trim();
                input.style.height = 'auto';
                input.style.height = Math.min(input.scrollHeight, 120) + 'px';
                input.focus();
                form.dispatchEvent(new Event('submit', { cancelable: true }));
            });
        });

        if (expandButton && modalElement) {
            expandButton.addEventListener('click', function () {
                modalElement.classList.toggle('is-expanded');
                syncExpandButton();
            });

            modalElement.addEventListener('hidden.bs.modal', function () {
                modalElement.classList.remove('is-expanded');
                syncExpandButton();
            });

            syncExpandButton();
        }

        if (sidebarButton) {
            sidebarButton.addEventListener('click', function () {
                var activeContent = getActiveTabContent();
                if (activeContent) {
                    activeContent.classList.toggle('is-sidebar-collapsed');
                }
                syncSidebarButton();
            });
            syncSidebarButton();
        }

        // ═══════════════════════════════════════════════════════
        // TAB SWITCHING
        // ═══════════════════════════════════════════════════════
        const tabBar = root.querySelector('[data-chatbot-tab-bar]');
        const tabButtons = root.querySelectorAll('[data-chatbot-tab]');
        const tabContents = root.querySelectorAll('[data-chatbot-tab-content]');
        let activeTab = 'ai';

        function switchTab(tabName) {
            if (tabName === activeTab) return;
            activeTab = tabName;

            tabButtons.forEach(function (btn) {
                btn.classList.toggle('is-active', btn.dataset.chatbotTab === tabName);
            });
            tabContents.forEach(function (content) {
                content.classList.toggle('is-active', content.dataset.chatbotTabContent === tabName);
            });

            // Sync sidebar button state for the newly active tab
            syncSidebarButton();

            if (tabName === 'support') {
                supportLoadConversations();
                supportStartPolling();
            } else {
                supportStopPolling();
            }
        }

        if (tabBar) {
            tabButtons.forEach(function (btn) {
                btn.addEventListener('click', function () {
                    switchTab(btn.dataset.chatbotTab);
                });
            });
        }

        // ═══════════════════════════════════════════════════════
        // SUPPORT CHAT
        // ═══════════════════════════════════════════════════════
        const supportEndpoints = {
            conversations: root.dataset.supportConversationsUrl,
            create: root.dataset.supportCreateUrl,
            messagesTemplate: root.dataset.supportMessagesUrlTemplate,
            sendTemplate: root.dataset.supportSendUrlTemplate,
        };

        const supportConvList = root.querySelector('[data-support-conversation-list]');
        const supportMessageList = root.querySelector('[data-support-message-list]');
        const supportInputArea = root.querySelector('[data-support-input-area]');
        const supportClosedBar = root.querySelector('[data-support-closed-bar]');
        const supportTextInput = root.querySelector('[data-support-text-input]');
        const supportSendBtn = root.querySelector('[data-support-send-btn]');
        const supportAttachBtn = root.querySelector('[data-support-attach-btn]');
        const supportFileInput = root.querySelector('[data-support-file-input]');
        const supportPreviewsContainer = root.querySelector('[data-support-previews]');
        const supportNewOverlay = root.querySelector('[data-support-new-overlay]');
        const supportNewForm = root.querySelector('[data-support-new-form]');
        const supportNewCancel = root.querySelector('[data-support-new-cancel]');
        const supportNewBtn = root.querySelector('[data-action="new-support-conversation"]');
        const supportUnreadBadge = root.querySelector('[data-support-unread-badge]');

        let supportCurrentConvId = null;
        let supportCurrentConvEstado = null;
        let supportPollingInterval = null;
        let supportConvPollingInterval = null;
        let supportImageFiles = [];

        function supportScrollToBottom() {
            if (supportMessageList) supportMessageList.scrollTop = supportMessageList.scrollHeight;
        }

        function renderSupportConvItem(conv) {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'chatbot-conversation-item chatbot-support-conv-item';
            if (conv.id === supportCurrentConvId) btn.classList.add('is-active');
            btn.dataset.supportConvId = conv.id;

            let metaHtml = '<div class="chatbot-support-conv-meta">';
            if (conv.prioridad === 'urgente') {
                metaHtml += '<span class="chatbot-badge chatbot-badge--urgente">Urgente</span>';
            }
            if (conv.estado === 'cerrada') {
                metaHtml += '<span class="chatbot-badge chatbot-badge--cerrada">Cerrada</span>';
            }
            metaHtml += '<span class="chatbot-support-time">' + timeAgo(conv.actualizado) + '</span>';
            if (conv.no_leidos > 0) {
                metaHtml += '<span class="chatbot-badge chatbot-badge--count">' + conv.no_leidos + '</span>';
            }
            metaHtml += '</div>';

            btn.innerHTML =
                '<strong>' + escapeHtml(conv.asunto) + '</strong>' +
                '<small>' + escapeHtml((conv.ultimo_texto || '').substring(0, 80)) + '</small>' +
                metaHtml;

            btn.addEventListener('click', function () {
                supportLoadMessages(conv.id);
            });
            return btn;
        }

        async function supportLoadConversations() {
            if (!supportEndpoints.conversations) return;
            try {
                const data = await apiFetchSupport(supportEndpoints.conversations);
                supportConvList.innerHTML = '';

                let totalUnread = 0;
                if (Array.isArray(data) && data.length > 0) {
                    data.forEach(function (conv) {
                        totalUnread += (conv.no_leidos || 0);
                        supportConvList.appendChild(renderSupportConvItem(conv));
                    });
                } else {
                    supportConvList.innerHTML = '<div class="chatbot-empty-sidebar"><i class="bi bi-headset"></i><p>Sin reportes aún</p></div>';
                }

                // Update unread badge on tab
                if (supportUnreadBadge) {
                    if (totalUnread > 0) {
                        supportUnreadBadge.textContent = totalUnread;
                        supportUnreadBadge.style.display = '';
                    } else {
                        supportUnreadBadge.style.display = 'none';
                    }
                }
            } catch (e) {
                // silent
            }
        }

        async function supportLoadMessages(convId) {
            supportCurrentConvId = convId;
            try {
                const url = buildConversationUrl(supportEndpoints.messagesTemplate, convId);
                const data = await apiFetchSupport(url);

                const conv = data.conversacion;
                const msgs = data.mensajes;
                supportCurrentConvEstado = conv.estado;

                // Update chat title
                chatTitle.textContent = conv.asunto;

                // Render messages
                supportMessageList.innerHTML = '';
                if (msgs.length === 0) {
                    supportMessageList.innerHTML = '<div class="chatbot-empty-state"><i class="bi bi-chat-left-text"></i><p>Sin mensajes aún</p></div>';
                } else {
                    msgs.forEach(function (m) {
                        supportMessageList.appendChild(renderSupportBubble(m));
                    });
                }
                supportScrollToBottom();

                // Show/hide input based on estado
                if (conv.estado === 'abierta') {
                    if (supportInputArea) supportInputArea.style.display = '';
                    if (supportClosedBar) supportClosedBar.style.display = 'none';
                } else {
                    if (supportInputArea) supportInputArea.style.display = 'none';
                    if (supportClosedBar) supportClosedBar.style.display = '';
                }

                // Highlight active conversation
                supportConvList.querySelectorAll('.chatbot-support-conv-item').forEach(function (item) {
                    item.classList.toggle('is-active', parseInt(item.dataset.supportConvId, 10) === convId);
                });

            } catch (e) {
                supportMessageList.innerHTML = '<div class="chatbot-empty-state"><i class="bi bi-exclamation-triangle"></i><p>Error al cargar mensajes</p></div>';
            }
        }

        async function supportSendMessage() {
            if (!supportCurrentConvId) return;
            const texto = (supportTextInput ? supportTextInput.value.trim() : '');
            if (!texto && supportImageFiles.length === 0) return;

            if (supportSendBtn) supportSendBtn.disabled = true;

            try {
                const url = buildConversationUrl(supportEndpoints.sendTemplate, supportCurrentConvId);

                if (supportImageFiles.length > 0) {
                    const fd = new FormData();
                    fd.append('texto', texto);
                    supportImageFiles.forEach(function (f) { fd.append('imagenes', f); });
                    await apiFetchSupport(url, { method: 'POST', body: fd });
                } else {
                    await apiFetchSupport(url, {
                        method: 'POST',
                        body: JSON.stringify({ texto: texto }),
                    });
                }

                if (supportTextInput) supportTextInput.value = '';
                supportClearImages();
                await supportLoadMessages(supportCurrentConvId);
                await supportLoadConversations();
            } catch (e) {
                // silent
            } finally {
                if (supportSendBtn) supportSendBtn.disabled = false;
                if (supportTextInput) supportTextInput.focus();
            }
        }

        function supportClearImages() {
            supportImageFiles = [];
            if (supportPreviewsContainer) supportPreviewsContainer.innerHTML = '';
            if (supportFileInput) supportFileInput.value = '';
        }

        function supportUpdatePreviews() {
            if (!supportPreviewsContainer) return;
            supportPreviewsContainer.innerHTML = '';
            supportImageFiles.forEach(function (file, idx) {
                const wrap = document.createElement('div');
                wrap.className = 'chatbot-support-preview-item';
                const img = document.createElement('img');
                img.src = URL.createObjectURL(file);
                img.alt = file.name;
                const removeBtn = document.createElement('button');
                removeBtn.type = 'button';
                removeBtn.className = 'chatbot-support-preview-remove';
                removeBtn.textContent = '\u00d7';
                removeBtn.addEventListener('click', function () {
                    supportImageFiles.splice(idx, 1);
                    supportUpdatePreviews();
                });
                wrap.appendChild(img);
                wrap.appendChild(removeBtn);
                supportPreviewsContainer.appendChild(wrap);
            });
        }

        function supportHandleFiles(files) {
            if (!files) return;
            var nuevas = Array.from(files).filter(function (f) {
                return f.type.startsWith('image/') && f.size <= 5 * 1024 * 1024;
            }).slice(0, 5 - supportImageFiles.length);
            supportImageFiles = supportImageFiles.concat(nuevas);
            supportUpdatePreviews();
        }

        // Support input events
        if (supportSendBtn) {
            supportSendBtn.addEventListener('click', supportSendMessage);
        }
        if (supportTextInput) {
            supportTextInput.addEventListener('keydown', function (e) {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    supportSendMessage();
                }
            });
            supportTextInput.addEventListener('paste', function (ev) {
                var items = ev.clipboardData && ev.clipboardData.items;
                if (!items) return;
                var imgs = [];
                for (var i = 0; i < items.length; i++) {
                    if (items[i].type.startsWith('image/')) {
                        var f = items[i].getAsFile();
                        if (f) imgs.push(f);
                    }
                }
                if (imgs.length > 0) {
                    ev.preventDefault();
                    supportImageFiles = supportImageFiles.concat(imgs).slice(0, 5);
                    supportUpdatePreviews();
                }
            });
        }
        if (supportAttachBtn && supportFileInput) {
            supportAttachBtn.addEventListener('click', function () {
                supportFileInput.click();
            });
            supportFileInput.addEventListener('change', function () {
                supportHandleFiles(this.files);
            });
        }

        // New report modal
        function openNewReportOverlay() {
            if (supportNewOverlay) {
                supportNewOverlay.style.display = '';
                var asuntoInput = root.querySelector('[data-support-new-asunto]');
                if (asuntoInput) asuntoInput.focus();
            }
        }

        if (supportNewBtn) {
            supportNewBtn.addEventListener('click', openNewReportOverlay);
        }
        var supportNewInlineBtn = root.querySelector('[data-action="new-support-conversation-inline"]');
        if (supportNewInlineBtn) {
            supportNewInlineBtn.addEventListener('click', openNewReportOverlay);
        }
        if (supportNewCancel && supportNewOverlay) {
            supportNewCancel.addEventListener('click', function () {
                supportNewOverlay.style.display = 'none';
            });
        }
        if (supportNewOverlay) {
            supportNewOverlay.addEventListener('click', function (e) {
                if (e.target === supportNewOverlay) {
                    supportNewOverlay.style.display = 'none';
                }
            });
        }
        if (supportNewForm) {
            supportNewForm.addEventListener('submit', async function (e) {
                e.preventDefault();
                var asuntoEl = root.querySelector('[data-support-new-asunto]');
                var mensajeEl = root.querySelector('[data-support-new-mensaje]');
                var prioridadEl = root.querySelector('[data-support-new-prioridad]');
                var submitBtn = root.querySelector('[data-support-new-submit]');

                var asunto = asuntoEl ? asuntoEl.value.trim() : '';
                var mensaje = mensajeEl ? mensajeEl.value.trim() : '';
                var prioridad = prioridadEl ? prioridadEl.value : 'normal';

                if (!asunto || !mensaje) return;
                if (submitBtn) submitBtn.disabled = true;

                try {
                    var data = await apiFetchSupport(supportEndpoints.create, {
                        method: 'POST',
                        body: JSON.stringify({ asunto: asunto, mensaje: mensaje, prioridad: prioridad }),
                    });
                    if (supportNewOverlay) supportNewOverlay.style.display = 'none';
                    if (asuntoEl) asuntoEl.value = '';
                    if (mensajeEl) mensajeEl.value = '';
                    if (prioridadEl) prioridadEl.value = 'normal';
                    await supportLoadConversations();
                    if (data.id) await supportLoadMessages(data.id);
                } catch (err) {
                    // silent
                } finally {
                    if (submitBtn) submitBtn.disabled = false;
                }
            });
        }

        // Lightbox for support images
        if (supportMessageList) {
            supportMessageList.addEventListener('click', function (e) {
                var thumb = e.target.closest('[data-lightbox-src]');
                if (!thumb) return;
                var src = thumb.dataset.lightboxSrc;
                var overlay = document.createElement('div');
                overlay.className = 'chatbot-lightbox-overlay';
                overlay.innerHTML =
                    '<img src="' + escapeHtml(src) + '" alt="Vista ampliada" class="chatbot-lightbox-img">' +
                    '<button type="button" class="chatbot-lightbox-close">&times;</button>';
                overlay.addEventListener('click', function (ev) {
                    if (ev.target === overlay || ev.target.classList.contains('chatbot-lightbox-close')) {
                        overlay.remove();
                    }
                });
                document.body.appendChild(overlay);
            });
        }

        // Polling management
        function supportStartPolling() {
            supportStopPolling();
            supportConvPollingInterval = setInterval(function () {
                supportLoadConversations();
            }, 5000);
            supportPollingInterval = setInterval(function () {
                if (supportCurrentConvId) {
                    supportLoadMessages(supportCurrentConvId);
                }
            }, 3000);
        }

        function supportStopPolling() {
            if (supportPollingInterval) { clearInterval(supportPollingInterval); supportPollingInterval = null; }
            if (supportConvPollingInterval) { clearInterval(supportConvPollingInterval); supportConvPollingInterval = null; }
        }

        // ═══════════════════════════════════════════════════════
        // MODAL LIFECYCLE
        // ═══════════════════════════════════════════════════════
        if (modalElement) {
            modalElement.addEventListener('shown.bs.modal', function () {
                if (activeTab === 'ai') {
                    refreshConversationList(currentConversationId);
                    input.focus();
                    scrollMessagesToBottom();
                } else {
                    supportLoadConversations();
                    supportStartPolling();
                    if (supportTextInput) supportTextInput.focus();
                }
            });

            modalElement.addEventListener('hidden.bs.modal', function () {
                modalElement.classList.remove('is-expanded');
                syncExpandButton();
                supportStopPolling();
            });

            if (modalElement.dataset.chatbotAutoOpen === 'true') {
                window.requestAnimationFrame(function () {
                    const modal = bootstrap.Modal.getOrCreateInstance(modalElement);
                    modal.show();
                });
            }
        }

        const firstConversation = conversationList.querySelector('[data-conversation-id]');
        if (firstConversation) {
            loadConversation(parseInt(firstConversation.dataset.conversationId, 10));
        }
    });
})();