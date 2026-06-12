---
name: correspondencia-ui-line
description: 'Rediseña interfaces de la unidad de correspondencia siguiendo la línea visual actual del proyecto. Úsala para modernizar templates Django de bandejas, dashboards, modales, sidebars, tablas, paginación y vistas administrativas sin romper IDs, endpoints, hooks JS ni flujos existentes. Activar con palabras como rediseñar, retoque visual, modernizar UI, modal, bandeja, dashboard, correspondencia, unidad de correspondencia, homologar estilo, mejorar layout.'
argument-hint: 'Indica la pantalla o archivo a rediseñar y si quieres rediseño completo o retoque ligero'
user-invocable: true
disable-model-invocation: false
---

# Correspondencia UI Line

## Qué Produce

Esta skill aplica la línea de diseño que se viene consolidando en la unidad de correspondencia del proyecto:

- interfaces más amplias, limpias y jerarquizadas
- cards y superficies con radios altos y sombras suaves
- cabeceras con mejor presencia visual
- badges tipo pill para estados, accesos y semáforos
- tablas más legibles y paginación más cuidada
- modales modernos, con secciones claras y scroll usable
- consistencia entre bandejas personales, de oficina, interoficina y dashboards

El objetivo no es hacer “arte por arte”. El objetivo es subir calidad visual sin romper la operación diaria.

## Cuándo Usarla

Usa esta skill cuando el usuario pida alguna de estas cosas:

- rediseñar una pantalla de correspondencia
- dar un retoque visual a un dashboard
- modernizar una bandeja o una tabla
- mejorar un modal de la unidad de correspondencia
- homologar una vista a la línea visual ya aplicada
- hacer que una plantilla se vea como bandeja_personal, bandeja_oficina o dashboard_usuario

Casos típicos:

- templates Django en `correspondencia/templates/correspondencia/...`
- modales en `correspondencia/templates/correspondencia/partials/modals/...`
- vistas de usuario y ventanilla
- sidebars, paginación y shells de layout

## Principios de Diseño

### 1. Coherencia antes que novedad

Si ya existe una dirección visual aprobada en la app, reutilízala y extiéndela. No rediseñes cada pantalla con un idioma distinto.

### 2. Mejorar la capa visual, no mover la lógica sin necesidad

Por defecto, conserva:

- IDs de elementos
- nombres de campos
- endpoints
- atributos `data-*`
- hooks de Bootstrap
- selectores usados por JavaScript
- bloques Django y contexto esperado por la vista

Si el trabajo es visual, el backend no se toca salvo necesidad real.

### 3. La interfaz debe sentirse institucional, no genérica

Evita UI plana de admin básico o estética de demo. El tono correcto para este proyecto es:

- sobrio pero actual
- claro pero con personalidad
- profesional, no frío
- elegante sin perder rapidez operativa

### 4. La legibilidad manda

En correspondencia se leen asuntos, radicados, remitentes, plazos y estados. La estética nunca debe entorpecer eso.

## Señales Visuales de Esta Línea

Al aplicar esta skill, busca estos patrones:

- contenedores principales con mayor ancho útil
- shells y heroes principales ocupando normalmente el 95% del ancho útil del contenedor, salvo una restricción funcional o visual justificada
- `border-radius` generosos, normalmente entre 16px y 28px
- sombras suaves y profundas, no duras
- gradientes sutiles en hero, headers o paneles clave
- colores de estado muy claros: éxito, advertencia, urgencia, pendiente
- pills o badges redondeados para estados y contadores
- bloques de filtros colapsables si hay mucha densidad de controles
- tablas con más aire, columnas mejor jerarquizadas y estados visuales claros
- footer y header sticky dentro de modales grandes cuando haga falta
- scroll interno visible en modales largos

## Flujo de Trabajo

### Paso 1. Inspeccionar el contexto real

Antes de editar:

1. Lee la plantilla objetivo.
2. Busca si esa pantalla depende de JS externo o de eventos Bootstrap.
3. Revisa archivos de referencia visual ya consolidados en el repo.

Referencias frecuentes en este proyecto:

- `bandeja_personal.html`
- `bandeja_oficina.html`
- `bandeja_interoficina.html`
- `dashboard_usuario.html`
- `dashboard_ventanilla.html`
- modales ya modernizados en `partials/modals`

### Paso 2. Definir el nivel de intervención

Decide si es:

- `retoque ligero`: mejorar espaciado, cards, encabezados, contraste, botones y jerarquía sin rehacer la estructura
- `rediseño completo`: reorganizar layout, paneles, tablas, modales y navegación manteniendo funcionalidad

Regla:

- si el usuario dice “solo un retoque”, no rehagas la arquitectura visual completa
- si pide “como la otra bandeja” o “rediseñemos”, sí puedes reconstruir la composición

### Paso 3. Proteger compatibilidad funcional

Antes de tocar estructura, identifica y preserva:

- formularios y sus `id`
- elementos usados por `document.getElementById`, jQuery o listeners globales
- `data-bs-target`, `data-bs-toggle`, `aria-*`
- zonas donde se inyecta HTML o donde el JS actualiza chips, contadores o inputs ocultos

En modales, esto es obligatorio. Cambia la piel, no rompas el cableado.

### Paso 4. Aplicar la composición correcta

Usa estas decisiones según el tipo de pantalla:

#### Bandejas

- shell ancho, preferiblemente al 95% del ancho útil del contenedor principal
- hero o cabecera con contexto
- filtros como bloque separado
- tabla dentro de card principal
- badges para lectura, plazo, acceso, visibilidad o urgencia
- paginación integrada visualmente al conjunto

#### Dashboards

- hero claro con acción principal visible y ancho útil cercano al 95% del contenedor principal
- métricas en tarjetas con peso visual uniforme
- secciones separadas con encabezados bien definidos
- accesos rápidos con intención gráfica, sin parecer grilla genérica

#### Modales

- hero superior breve
- contenido dividido por paneles o columnas
- campos agrupados por función
- `modal-dialog-scrollable` cuando haya mucho contenido
- `modal-content` con altura máxima visible
- `modal-body` con `overflow-y: auto` si el modal es largo
- header y footer sticky cuando mejore usabilidad

### Paso 5. Encapsular estilos

Siempre que puedas:

- usa una clase raíz propia por pantalla o modal
- define variables CSS locales
- evita contaminar otros templates
- evita reescribir estilos globales salvo que el cambio sea realmente transversal

Patrón recomendado:

1. wrapper raíz del template o modal
2. variables CSS locales
3. bloques visuales nombrados por función, no por apariencia vaga

Si la pantalla usa shell principal o hero exterior, prioriza un ancho útil del 95% antes de introducir límites más estrechos. Si necesitas reducirlo, debe haber una razón clara de legibilidad, densidad o compatibilidad.

## Reglas Específicas del Proyecto

### Modales de correspondencia

Cuando rediseñes modales de creación, respuesta o edición:

- conserva IDs y nombres de campos
- conserva contenedores que JS llena dinámicamente
- permite scroll interno si el contenido supera la altura de pantalla
- no escondas acciones críticas en mobile
- mantén visible el submit y cancelar aunque el cuerpo sea largo

### Bandejas y KPIs

Si la pantalla tiene KPIs o links que filtran bandejas:

- verifica que el filtro enlazado sí exista en la vista destino
- no inventes parámetros visuales que no soporta el backend
- si hay KPIs, deben respetar la misma lógica de consulta que la bandeja a la que apuntan

### Estados y semáforos

Estados como leída, no leída, vencida, próxima a vencer, compartida o solo lectura deben distinguirse de un vistazo.

No dependas solo del texto. Usa también:

- color
- badge
- icono cuando aporte claridad
- jerarquía tipográfica

## Criterios de Calidad

La tarea se considera bien terminada si:

1. la plantilla se ve más clara, moderna y coherente con el resto del sistema
2. no se rompieron IDs, formularios, modales, AJAX ni scripts existentes
3. mobile y desktop siguen siendo utilizables
4. el contenido largo puede recorrerse sin fricción
5. las acciones principales siguen visibles y obvias
6. Django check o validación equivalente no arroja problemas por el cambio

## Checklist de Cierre

Antes de terminar:

1. revisar errores del archivo editado
2. validar que el layout no pierda funcionalidad
3. si aplica, correr `manage.py check`
4. confirmar que botones, modales y submits siguen conectados
5. verificar que el resultado mantenga la línea visual de correspondencia ya existente

## Qué Evitar

- reescribir backend cuando el pedido es visual
- cambiar nombres de campos o IDs usados por JS
- meter CSS global innecesario
- diseñar un modal bonito pero imposible de recorrer
- tablas visualmente “modernas” pero menos legibles
- usar estilos llamativos que rompan el carácter institucional de la app

## Prompt de Ejemplo

- `/correspondencia-ui-line rediseña este modal para que siga la línea actual del sistema y no rompa los hooks JS`
- `/correspondencia-ui-line dale un retoque ligero a este dashboard sin cambiar su estructura funcional`
- `/correspondencia-ui-line moderniza esta bandeja usando como referencia bandeja_personal y dashboard_usuario`

## Nota de Aplicación

Si existe ambigüedad entre un rediseño completo y un retoque ligero, prioriza primero una mejora conservadora y explícita la suposición.