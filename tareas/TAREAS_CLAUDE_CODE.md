# 🤖 TAREAS PARA CLAUDE CODE (ALTO NIVEL)

## 📌 CONTEXTO
Objetivo: migrar el calendario de informes y firma de planillas a un frontend moderno, responsive y optimizado para tablets y moviles.

Guia principal:
- documentacion/mapa_topologico_archivos.md

Usa las 3 skills como prefieras:
- frontend-design
- theme-factory
- web-artifacts-builder

---

## 🎯 PRIORIDAD GLOBAL
La experiencia debe ser excelente en tablets y dispositivos moviles. Todo lo demas es secundario.

---

## ✅ CHECKLIST MINIMO (ALTO NIVEL)

### 1) Comprension del flujo actual
- [ ] Identificar pantallas clave desde el mapa topologico
- [ ] Revisar templates relevantes del calendario y detalle
- [ ] Entender endpoints necesarios desde el backend Django

### 2) Definir stack y arquitectura
- [ ] Elegir stack frontend (criterio propio)
- [ ] Definir estructura basica de carpetas
- [ ] Definir estrategia de autenticacion (cookies o tokens)

### 3) Implementar el calendario
- [ ] Vista mensual con estados visuales por dia
- [ ] Navegacion entre meses
- [ ] Click en dia abre detalle
- [ ] Responsive real para tablet y movil

### 4) Implementar detalle del dia
- [ ] Lista o tabla de correspondencias
- [ ] Estadisticas visibles (total, firmadas, pendientes)
- [ ] Acciones principales visibles y accesibles

### 5) Firma digital y archivos
- [ ] Firma en canvas con soporte tactil
- [ ] Subida de archivos firmados
- [ ] Validaciones basicas y feedback claro

### 6) Calidad y mobile-first
- [ ] Legibilidad, contraste y tamanos tactiles
- [ ] Navegacion simple con pocos pasos
- [ ] Estados de carga y error claros
- [ ] Pruebas en 360px y 768px como minimo

---

## ✅ CRITERIOS DE ACEPTACION
- [ ] Funciona bien en tablet y movil
- [ ] Calendario y detalle reproducen el flujo actual
- [ ] Firma digital usable con touch
- [ ] Subida de archivos estable
- [ ] Sin errores visibles en UI
