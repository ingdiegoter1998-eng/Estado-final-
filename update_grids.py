import re

with open("correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html", "r", encoding="utf-8") as f:
    text = f.read()

# Extract the chunks to be replaced
start_marker = "{% comment %} HISTORIAL {% endcomment %}"
end_marker = "            {% endif %}\n            </div>\n        </div>\n    </div>\n</div>"

if start_marker in text and end_marker in text:
    start_idx = text.find(start_marker)
    end_idx = text.find(end_marker)
    
    # We will replace this block with our "Seguimiento" card
    chunk = text[start_idx:end_idx]
    
    seguimiento_card = """{% comment %} BOTONES DE SEGUIMIENTO {% endcomment %}
            <div class="detail-side-card">
                <h6>Información de Seguimiento</h6>
                <div class="action-stack text-center mt-3">
                    <button type="button" class="btn btn-outline-primary mb-2 w-100 fw-medium d-flex align-items-center justify-content-center gap-2" data-bs-toggle="modal" data-bs-target="#modalHistorialEventos">
                        <i class="bx bx-history fs-5"></i> Historial de eventos
                    </button>
                    <button type="button" class="btn btn-outline-info w-100 fw-medium d-flex align-items-center justify-content-center gap-2" data-bs-toggle="modal" data-bs-target="#modalEstadoLectura">
                        <i class="bx bx-check-double fs-5"></i> Estado de lectura
                    </button>
                    {% if accesos_oficinas %}
                    <button type="button" class="btn btn-outline-secondary mt-2 w-100 fw-medium d-flex align-items-center justify-content-center gap-2" data-bs-toggle="modal" data-bs-target="#modalAccesosOficinas">
                        <i class="bx bx-buildings fs-5"></i> Oficinas con acceso
                    </button>
                    {% endif %}
                </div>
            </div>
"""
    
    # Append the extracted modals to the very bottom, inside the <!-- ===================== MODALES ===================== --> section
    modales_html = """
<!-- Modal Historial de Eventos -->
<div class="modal fade" id="modalHistorialEventos" tabindex="-1" aria-labelledby="modalHistorialEventosLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-lg modal-dialog-scrollable">
        <div class="modal-content" style="border: none; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25); overflow: hidden;">
            <div class="modal-header d-flex justify-content-between align-items-center" style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem;">
                <h5 class="modal-title d-flex align-items-center gap-2 m-0" id="modalHistorialEventosLabel" style="font-weight: 700; color: #0f172a; font-size: 1.15rem;">
                    <div class="bg-primary text-white d-flex align-items-center justify-content-center rounded-circle shadow-sm" style="width: 36px; height: 36px;">
                        <i class="bx bx-history fs-5"></i>
                    </div>
                    Historial de Eventos
                </h5>
                <button type="button" class="btn-close shadow-sm bg-white border" data-bs-dismiss="modal" aria-label="Close" style="border-radius: 50%; opacity: 1;"></button>
            </div>
            <div class="modal-body p-4 bg-light">
                <div class="timeline ps-3" style="border-left: 2px solid #cbd5e1;">
                    {% for evento in historial %}
                    <div class="timeline-item mb-4 position-relative">
                        <div class="timeline-marker bg-{% if evento.evento == 'RADICACION' %}primary{% elif evento.evento == 'DISTRIBUCION' %}info{% elif evento.evento == 'LECTURA' %}success{% elif evento.evento == 'RESPUESTA' %}warning{% else %}secondary{% endif %} rounded-circle position-absolute" style="width: 14px; height: 14px; left: -24px; top: 4px; box-shadow: 0 0 0 4px #f8fafc;"></div>
                        <div class="timeline-content card border-0 shadow-sm p-3" style="border-radius: 12px;">
                            <div class="timeline-header d-flex justify-content-between align-items-center mb-2">
                                <span class="badge bg-{% if evento.evento == 'RADICACION' %}primary{% elif evento.evento == 'DISTRIBUCION' %}info{% elif evento.evento == 'LECTURA' %}success{% elif evento.evento == 'RESPUESTA' %}warning{% else %}secondary{% endif %} bg-opacity-10 text-{% if evento.evento == 'RADICACION' %}primary{% elif evento.evento == 'DISTRIBUCION' %}info{% elif evento.evento == 'LECTURA' %}success{% elif evento.evento == 'RESPUESTA' %}warning{% else %}secondary{% endif %} fw-bold px-3 py-2 rounded-pill">
                                    {{ evento.get_evento_display }}
                                </span>
                                <small class="text-muted fw-medium d-flex align-items-center gap-1"><i class="bx bx-time"></i> {{ evento.fecha_hora|date:"Y-m-d H:i:s" }}</small>
                            </div>
                            <div class="timeline-body mt-2">
                                <p class="mb-1 fw-bold text-dark d-flex align-items-center gap-1"><i class="bx bx-user text-muted"></i> {{ evento.usuario.username|default:"Sistema" }}</p>
                                {% if evento.descripcion %}
                                <p class="mb-0 text-secondary small bg-light p-2 rounded">{{ evento.descripcion|linebreaksbr }}</p>
                                {% endif %}
                            </div>
                        </div>
                    </div>
                    {% empty %}
                    <div class="text-center py-4">
                        <i class="bx bx-folder-open text-muted fs-1 mb-2"></i>
                        <p class="text-muted mb-0">No hay eventos registrados.</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
            <div class="modal-footer bg-light border-top" style="padding: 1rem 1.5rem;">
                <button type="button" class="btn btn-light border px-4 rounded-pill fw-medium text-secondary hover-shadow-sm" data-bs-dismiss="modal">
                    <i class="bx bx-x me-1"></i> Cerrar
                </button>
            </div>
        </div>
    </div>
</div>

<!-- Modal Estado de Lectura -->
<div class="modal fade" id="modalEstadoLectura" tabindex="-1" aria-labelledby="modalEstadoLecturaLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content" style="border: none; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25); overflow: hidden;">
            <div class="modal-header d-flex justify-content-between align-items-center" style="background: linear-gradient(135deg, #f0fdfa 0%, #f1f5f9 100%); border-bottom: 1px solid #ccfbf1; padding: 1.25rem 1.5rem;">
                <h5 class="modal-title d-flex align-items-center gap-2 m-0" id="modalEstadoLecturaLabel" style="font-weight: 700; color: #0f766e; font-size: 1.15rem;">
                    <div class="bg-info text-white d-flex align-items-center justify-content-center rounded-circle shadow-sm" style="width: 36px; height: 36px;">
                        <i class="bx bx-check-double fs-5"></i>
                    </div>
                    Estado de Lectura
                </h5>
                <button type="button" class="btn-close shadow-sm bg-white border" data-bs-dismiss="modal" aria-label="Close" style="border-radius: 50%; opacity: 1;"></button>
            </div>
            <div class="modal-body p-4 bg-light">
                <div class="card border-0 shadow-sm mb-4" style="border-radius: 16px;">
                    <div class="card-header bg-white border-bottom py-3">
                        <h6 class="mb-0 fw-bold text-success d-flex align-items-center gap-2"><i class="bx bx-check-circle fs-5"></i> Leído por:</h6>
                    </div>
                    <ul class="list-group list-group-flush" style="border-radius: 0 0 16px 16px;">
                        {% if usuarios_que_leyeron %}
                            {% for usuario in usuarios_que_leyeron %}
                                <li class="list-group-item px-4 py-3 d-flex align-items-center gap-3">
                                    <div class="bg-success bg-opacity-10 text-success p-2 rounded-circle"><i class="bx bx-user"></i></div>
                                    <span class="fw-medium text-dark">{{ usuario.get_full_name|default:usuario.username }}</span>
                                </li>
                            {% endfor %}
                        {% else %}
                            <li class="list-group-item px-4 py-4 text-center text-muted">
                                <em>Aún no ha sido leído por ningún destinatario.</em>
                            </li>
                        {% endif %}
                    </ul>
                </div>
                
                {% with todos_destinatarios=correspondencia.distribuciones_internas.all %}
                {% if todos_destinatarios %}
                <div class="card border-0 shadow-sm" style="border-radius: 16px;">
                    <div class="card-header bg-white border-bottom py-3">
                        <h6 class="mb-0 fw-bold text-warning d-flex align-items-center gap-2"><i class="bx bx-hourglass fs-5"></i> Pendiente por leer:</h6>
                    </div>
                    <ul class="list-group list-group-flush" style="border-radius: 0 0 16px 16px;">
                        {% for distribucion in todos_destinatarios %}
                            {% if not distribucion.leido %}
                            <li class="list-group-item px-4 py-3 d-flex align-items-center gap-3">
                                <div class="bg-warning bg-opacity-10 text-warning p-2 rounded-circle"><i class="bx bx-user-x"></i></div>
                                <span class="fw-medium text-dark">{{ distribucion.usuario_asignado.get_full_name|default:distribucion.usuario_asignado.username }}</span>
                            </li>
                            {% endif %}
                        {% endfor %}
                    </ul>
                </div>
                {% endif %}
                {% endwith %}
            </div>
        </div>
    </div>
</div>

{% if accesos_oficinas %}
<!-- Modal Accesos de Oficinas -->
<div class="modal fade" id="modalAccesosOficinas" tabindex="-1" aria-labelledby="modalAccesosOficinasLabel" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered modal-dialog-scrollable">
        <div class="modal-content" style="border: none; border-radius: 24px; box-shadow: 0 25px 50px -12px rgba(15, 23, 42, 0.25); overflow: hidden;">
            <div class="modal-header d-flex justify-content-between align-items-center" style="background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%); border-bottom: 1px solid #e2e8f0; padding: 1.25rem 1.5rem;">
                <h5 class="modal-title d-flex align-items-center gap-2 m-0" id="modalAccesosOficinasLabel" style="font-weight: 700; color: #0f172a; font-size: 1.15rem;">
                    <div class="bg-secondary text-white d-flex align-items-center justify-content-center rounded-circle shadow-sm" style="width: 36px; height: 36px;">
                        <i class="bx bx-buildings fs-5"></i>
                    </div>
                    Oficinas con Acceso de Solo Lectura
                </h5>
                <button type="button" class="btn-close shadow-sm bg-white border" data-bs-dismiss="modal" aria-label="Close" style="border-radius: 50%; opacity: 1;"></button>
            </div>
            <div class="modal-body p-4 bg-light">
                <div class="card border-0 shadow-sm" style="border-radius: 16px;">
                    <ul class="list-group list-group-flush" style="border-radius: 16px;">
                        {% for acceso in accesos_oficinas %}
                        <li class="list-group-item px-4 py-3 d-flex justify-content-between align-items-center">
                            <span class="fw-medium text-dark d-flex align-items-center gap-3">
                                <div class="bg-primary bg-opacity-10 text-primary p-2 rounded-lg"><i class="bx bx-building fs-5"></i></div>
                                {{ acceso.oficina.nombre }}
                            </span>
                            {% if acceso.leido %}
                                <span class="badge bg-success bg-opacity-10 text-success px-3 py-2 rounded-pill border border-success border-opacity-25" style="font-size: 0.85rem;"><i class="bx bx-check me-1"></i>Visto</span>
                            {% else %}
                                <span class="badge bg-secondary bg-opacity-10 text-secondary px-3 py-2 rounded-pill border border-secondary border-opacity-25" style="font-size: 0.85rem;"><i class="bx bx-time me-1"></i>Pendiente</span>
                            {% endif %}
                        </li>
                        {% endfor %}
                    </ul>
                </div>
            </div>
        </div>
    </div>
</div>
{% endif %}
"""
    
    new_text = text[:start_idx] + seguimiento_card + text[end_idx:]
    
    # Now find where to put the modals
    modales_marker = "<!-- ===================== MODALES ===================== -->"
    if modales_marker in new_text:
        new_text = new_text.replace(modales_marker, modales_marker + "\n" + modales_html)
        print("Modales inyectados.")
    else:
        new_text += modales_html
        
    with open("correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html", "w", encoding="utf-8") as file:
        file.write(new_text)
    
    print("Reemplazo listo.")
else:
    print("No se encontró el marcador de inicio o fin.")
