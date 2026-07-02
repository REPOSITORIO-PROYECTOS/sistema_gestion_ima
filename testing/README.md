# Tests - Sistema de Gestión IMA

## Ubicación de Tests

Los tests están organizados en dos carpetas:
- **testing/** → Tests principales y de sincronización
- **back/testing/** → Tests de integración backend

---

## Tests Principales (testing/)

### 📊 `test_sincronizacion_stock.py`
**Propósito:** Verificar sincronización de stock desde Google Sheets a Base de Datos
- Valida carga de artículos desde Sheet
- Verifica mapeo flexible de columnas
- Revisa actualización de stock y precios
- **Ejecutar:** `python testing/test_sincronizacion_stock.py`

### 💰 `diag_movimientos_columnas.py` / `test_movimientos_columnas.py`
**Propósito:** Diagnóstico y tests de alineación de columnas en pestaña `MOVIMIENTOS` (corrimiento Swing)
- Simula fila por encabezados de fila 1 sin escribir en Sheets
- Detecta encabezados desconocidos y columna A vacía
- **Diagnóstico en vivo (empresa 1 = Swing):** `python testing/diag_movimientos_columnas.py --id-empresa 1 --guardar-fixture`
- **Diagnóstico offline:** `python testing/diag_movimientos_columnas.py --solo-fixture`
- **Tests unitarios:** `python testing/test_movimientos_columnas.py`

### 🔄 `test_sincronizacion_manual.py`
**Propósito:** Test rápido de sincronización manual
- Verifica funcionamiento básico de sync
- Comprueba que artículos se cargan correctamente
- **Ejecutar:** `python testing/test_sincronizacion_manual.py`

### 🍽️ `test_mesas.py`
**Propósito:** Tests del módulo de mesas y pedidos
- Validación de operaciones con mesas
- **Ejecutar:** `python testing/test_mesas.py`

### 🔌 `test_api.py`
**Propósito:** Tests básicos de endpoints de API
- Verifica conectividad y respuestas básicas
- **Ejecutar:** `python testing/test_api.py`

### 🌊 `test_general_flujos.py`
**Propósito:** Tests de flujos generales del sistema
- Validación end-to-end de procesos
- **Ejecutar:** `python testing/test_general_flujos.py`

---

## Tests Backend (back/testing/)

### 🔗 `test_integracion_sistema.py`
**Propósito:** Tests de integración del sistema completo
- Valida interacción entre módulos

### 📄 `test_render_factura.py`
**Propósito:** Tests de renderizado de facturas
- Verifica generación de comprobantes

### 🧪 `prototipo_generico.py`
**Propósito:** Prototipo genérico para testing

### 🎯 `viabilidad_generador_comprobantes.py`
**Propósito:** Análisis de viabilidad del generador de comprobantes

---

## Cómo Ejecutar Tests

### Ejecutar un test específico:
```bash
cd /home/sgi_user/proyectos/sistema_gestion_ima
python testing/test_sincronizacion_stock.py
```

### Ejecutar todos los tests:
```bash
cd /home/sgi_user/proyectos/sistema_gestion_ima
python -m pytest testing/ -v
```

### Ejecutar tests con salida detallada:
```bash
python testing/test_sincronizacion_stock.py -v
```

---

## Notas Importantes

✅ **Sincronización automática:** La sincronización de artículos ocurre cada 5 minutos via cron job  
✅ **Tests de desarrollo:** Estos son principalmente para validar cambios locales  
✅ **BD de prueba:** Los tests usan la BD real del empresa ID 32 (admin_ropa)

---
