# Dashboard Moderno - Correspondencia

## Descripción

Se ha implementado un nuevo diseño moderno para el dashboard de correspondencia basado en el prototipo visual proporcionado. El nuevo diseño incluye:

- **Sistema de colores moderno** con variables CSS
- **Modo oscuro/claro** automático basado en preferencias del sistema
- **Layout responsivo** con grid CSS moderno
- **Componentes visuales mejorados** (KPIs, gráficos, tablas)
- **Accesibilidad mejorada** con contraste adecuado

## Características Implementadas

### 1. Sistema de Variables CSS
- Paleta de colores consistente
- Modo oscuro automático
- Transiciones suaves
- Espaciado y bordes estandarizados

### 2. Componentes Modernos
- **KPIs**: Cards con números grandes y tags de estado
- **Donut Chart**: Gráfico circular para SLA con CSS puro
- **Tablas**: Headers sticky, hover effects, modo compacto
- **Botones**: Estilos modernos con micro-interacciones
- **Formularios**: Inputs con bordes redondeados y estados de focus

### 3. Layout Responsivo
- Grid adaptativo para diferentes breakpoints
- Sidebar colapsable en móvil
- Navegación optimizada para dispositivos móviles

### 4. Mejoras de UX
- Indicadores visuales de estado
- Micro-interacciones sutiles
- Contraste adecuado para WCAG
- Reducción de motion para usuarios sensibles

## Archivos Creados/Modificados

### Nuevos Archivos
- `correspondencia/static/correspondencia/css/dashboard-modern.css` - Estilos del dashboard moderno
- `correspondencia/templates/correspondencia/admin/dashboard_moderno.html` - Template alternativo

### Archivos Modificados
- `correspondencia/templates/correspondencia/admin/dashboard_ventanilla.html` - Dashboard principal actualizado

## Uso

### Dashboard Principal
El dashboard principal (`dashboard_ventanilla.html`) ahora incluye el nuevo diseño moderno. Para acceder:

1. Navega a la sección de ventanilla
2. El dashboard se mostrará automáticamente con el nuevo diseño

### Dashboard Alternativo
Si prefieres usar el template alternativo:

1. Modifica la vista correspondiente para usar `dashboard_moderno.html`
2. O crea una nueva URL que apunte al template alternativo

## Personalización

### Colores
Los colores se pueden personalizar modificando las variables CSS en `dashboard-modern.css`:

```css
.dashboard-modern {
  --accent: #2563eb;     /* Color principal */
  --ok: #16a34a;         /* Verde para éxito */
  --warn: #b45309;       /* Amarillo para advertencia */
  --danger: #b91c1c;     /* Rojo para peligro */
  /* ... más variables */
}
```

### Modo Oscuro
El modo oscuro se activa automáticamente basado en las preferencias del sistema. Para forzar un modo específico, puedes agregar clases CSS adicionales.

### Responsividad
Los breakpoints están configurados para:
- **Móvil**: < 768px
- **Tablet**: 768px - 980px
- **Desktop**: > 980px

## Compatibilidad

### Navegadores Soportados
- Chrome 88+
- Firefox 85+
- Safari 14+
- Edge 88+

### Características CSS Utilizadas
- CSS Grid
- CSS Variables (Custom Properties)
- `color-mix()` function
- `clamp()` function
- `conic-gradient`
- `backdrop-filter`

## Mantenimiento

### Actualización de Estilos
Para actualizar los estilos:

1. Modifica `dashboard-modern.css`
2. Ejecuta `python manage.py collectstatic` si es necesario
3. Limpia la caché del navegador

### Agregar Nuevos Componentes
Para agregar nuevos componentes:

1. Define las variables CSS necesarias
2. Crea los estilos en `dashboard-modern.css`
3. Usa las clases `.dashboard-modern` como prefijo

## Próximas Mejoras

- [ ] Toggle manual para modo oscuro/claro
- [ ] Más tipos de gráficos (barras, líneas)
- [ ] Animaciones más elaboradas
- [ ] Temas personalizables por usuario
- [ ] Exportación de datos en diferentes formatos

## Soporte

Para reportar problemas o solicitar mejoras:

1. Revisa la documentación existente
2. Verifica la compatibilidad del navegador
3. Consulta los logs de errores
4. Contacta al equipo de desarrollo

---

**Nota**: Este dashboard mantiene toda la funcionalidad existente mientras mejora significativamente la experiencia visual y de usuario.
