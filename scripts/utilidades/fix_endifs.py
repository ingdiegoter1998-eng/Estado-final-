import re

with open("correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html", "r", encoding="utf-8") as f:
    text = f.read()

# I notice on line 1173:
#             </div>
#         </div>
#     </div>
# </div>
# {% endif %}

# In my sed output:
# 1171                </div>
# 1172            </div>
# 1173            {% endif %}  <--- THIS IS WRONG, it was orphaned because my regex didn't clean it up properly. Let's fix this area.

bad_block = """                    {% if accesos_oficinas %}
                    <button type="button" class="btn btn-outline-secondary mt-2 w-100 fw-medium d-flex align-items-center justify-content-center gap-2" data-bs-toggle="modal" data-bs-target="#modalAccesosOficinas">
                        <i class="bx bx-buildings fs-5"></i> Oficinas con acceso
                    </button>
                    {% endif %}
                </div>
            </div>
            {% endif %}
            </div>
        </div>
    </div>
</div>
{% endif %}"""

good_block = """                    {% if accesos_oficinas %}
                    <button type="button" class="btn btn-outline-secondary mb-2 w-100 fw-medium d-flex align-items-center justify-content-center gap-2" data-bs-toggle="modal" data-bs-target="#modalAccesosOficinas">
                        <i class="bx bx-buildings fs-5"></i> Oficinas con acceso
                    </button>
                    {% endif %}
                </div>
            </div>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""

text = text.replace(bad_block, good_block)

# Also check for {% endblock %} at the end. Actually wait, let's look at the original tail.

