import re

with open("correspondencia/templates/correspondencia/usuario/detalle_correspondencia.html", "r", encoding="utf-8") as f:
    text = f.read()

# Using regex to find the block
pattern = r"\{%\s*comment\s*%\} HISTORIAL \{%\s*endcomment\s*%\}.*?\{%\s*endif\s*%\}\n\s*</div>\n\s*</div>\n\s*</div>\n</div>"
match = re.search(pattern, text, flags=re.DOTALL)

if match:
    start_idx = match.start()
    end_idx = match.end() - len("\n        </div>\n    </div>\n</div>") 
    # Wait, let's just make sure we capture up to the end of the last detail-side-card
    # Actually, a better marker is from `{% comment %} HISTORIAL {% endcomment %}` and replace until `<!-- ===================== MODALES ===================== -->` minus the closing tags of the main grid.
