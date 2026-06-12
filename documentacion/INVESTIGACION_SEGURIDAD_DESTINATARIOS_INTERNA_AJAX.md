# Investigación: Seguridad de `destinatarios_interna_ajax`

## Contexto

La vista `correspondencia.views.destinatarios_interna_ajax(request, pk)` devuelve en JSON los destinatarios de una comunicación interna. Actualmente **no verifica** si el usuario tiene derecho a ver esa comunicación; cualquier usuario autenticado puede llamar `/interna/<pk>/destinatarios-ajax/` y obtener radicado, asunto y lista de destinatarios.

**Ruta:** `path('interna/<int:pk>/destinatarios-ajax/', views.destinatarios_interna_ajax, name='destinatarios_interna_ajax')`

---

## Dónde se usa este endpoint

- Modal de comunicaciones recibidas: para mostrar "Para quién" en el listado/detalle de una comunicación a la que el usuario **ya accedió** desde una vista que sí valida permisos (lista recibidas/enviadas o detalle). El riesgo es que el frontend pueda ser manipulado para pedir destinatarios de otro `pk`.

---

## Modelo de permisos ya existente

En `ComunicacionInternaDetailView.get_object()` (líneas ~9992-9946) está la lógica oficial de “quién puede ver esta comunicación”:

| tipo_distribucion | Quién tiene acceso |
|-------------------|--------------------|
| **USUARIO**       | Solo si `remitente_usuario == user` o `destinatario_usuario == user` |
| **OFICINA**       | Solo si la oficina del usuario es remitente o destinataria **y** existe `ComunicacionInternaDistribucion(comunicacion=obj, usuario=user)` |
| **PROCESO**       | Solo si existe `ComunicacionInternaDistribucion(comunicacion=obj, usuario=user)` |
| **ENTIDAD**       | Solo si existe `ComunicacionInternaDistribucion(comunicacion=obj, usuario=user)` |
| **None** (legacy)  | Remitente/destinatario usuario u oficina, o está en `ComunicacionInternaDistribucion` |

Modelos relevantes:

- `ComunicacionInterna`: `remitente_usuario`, `remitente_oficina`, `destinatario_usuario`, `destinatario_oficina`, `destinatario_proceso`, `tipo_distribucion`, `destinatarios_multiples` (ComunicacionInternaDestinatario).
- `ComunicacionInternaDistribucion`: indica que a un usuario se le “distribuyó” esa comunicación (puede verla).

---

## Opciones de corrección (cuando decidas implementar)

1. **Reutilizar la misma lógica que el detalle**  
   Extraer la comprobación de “¿el usuario tiene acceso a esta comunicación?” a una función o método (por ejemplo `usuario_puede_ver_comunicacion_interna(user, comunicacion)`) y usarla en:
   - `ComunicacionInternaDetailView.get_object()`
   - `destinatarios_interna_ajax` antes de construir y devolver el JSON.  
   Si no tiene acceso → `JsonResponse({'success': False, 'error': 'Sin permiso.'}, status=403)`.

2. **Obtener el objeto como en el detalle**  
   En la vista AJAX, obtener la comunicación con la misma lógica que `get_object()` (por ejemplo instanciar la misma clase de vista y llamar a `get_object()`, o usar la función anterior). Así se centraliza la regla de negocio y se evita IDOR.

3. **No cambiar nada**  
   Si este endpoint solo se llama desde pantallas donde el usuario ya pasó por lista/detalle (y no se expone el `pk` de otras comunicaciones), el riesgo es bajo pero sigue existiendo si alguien prueba IDs a mano.

---

## Recomendación

Aplicar la **opción 1**: extraer la lógica de acceso a una función y usarla en `destinatarios_interna_ajax` y en `ComunicacionInternaDetailView.get_object()` para mantener un solo criterio y cerrar el IDOR.

---

*Documento generado a partir de la evaluación de seguridad de views. Fecha: 2025.*
