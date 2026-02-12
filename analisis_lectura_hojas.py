#!/usr/bin/env python3
"""
ANÁLISIS COMPLETO de qué hojas lee el sistema y cómo las lee
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "back"))

from back.database import get_db
from back.modelos import ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler
from sqlmodel import select
import gspread

# Colores para terminal
VERDE = '\033[92m'
ROJO = '\033[91m'
AMARILLO = '\033[93m'
AZUL = '\033[94m'
RESET = '\033[0m'

def analizar_uso_hojas():
    """
    Analiza qué hojas usa el sistema y cómo las usa
    """
    print(f"\n{'='*80}")
    print(f"📋 ANÁLISIS DE USO DE HOJAS DE GOOGLE SHEETS")
    print(f"{'='*80}\n")
    
    print("🔍 HOJAS QUE USA EL SISTEMA ACTUALMENTE:\n")
    
    hojas_sistema = {
        "clientes": {
            "método": "cargar_clientes()",
            "archivo": "back/utils/tablas_handler.py (línea 72)",
            "usado_en": [
                "back/gestion/caja/cliente_publico.py",
                "back/gestion/actualizaciones/actualizaciones_masivas.py"
            ],
            "propósito": "Sincronizar datos de clientes desde Sheets a la DB",
            "nombre_fijo": True,
            "campo_clave": "id-cliente o codigo_interno"
        },
        "proveedores": {
            "método": "cargar_proveedores()",
            "archivo": "back/utils/tablas_handler.py (línea 90)",
            "usado_en": [
                "back/gestion/actualizaciones/actualizaciones_masivas.py"
            ],
            "propósito": "Sincronizar datos de proveedores desde Sheets a la DB",
            "nombre_fijo": True,
            "campo_clave": "id o codigo_interno"
        },
        "MOVIMIENTOS": {
            "método": "registrar_movimiento()",
            "archivo": "back/utils/tablas_handler.py (línea 111)",
            "usado_en": [
                "back/gestion/caja/registro_caja.py (3 veces)"
            ],
            "propósito": "Registrar cada venta/movimiento de caja en Sheets",
            "nombre_fijo": True,
            "campo_clave": "id_movimiento (generado automáticamente)"
        },
        "stock": {
            "método": "restar_stock() y cargar_articulos()",
            "archivo": "back/utils/tablas_handler.py (líneas 154, 394)",
            "usado_en": [
                "back/gestion/caja/registro_caja.py",
                "back/gestion/sincronizacion_manager.py",
                "back/gestion/actualizaciones/actualizaciones_masivas.py"
            ],
            "propósito": "Actualizar stock en ventas y sincronizar artículos",
            "nombre_fijo": False,
            "alternativas": ['stock', 'articulos', 'productos', 'inventory', 'inventario', 'items'],
            "campo_clave": "Código o codigo_interno"
        }
    }
    
    for nombre_hoja, info in hojas_sistema.items():
        print(f"📄 {AZUL}{nombre_hoja}{RESET}")
        print(f"   Método: {info['método']}")
        print(f"   Definido en: {info['archivo']}")
        print(f"   Propósito: {info['propósito']}")
        print(f"   Campo clave: {info['campo_clave']}")
        
        if info['nombre_fijo']:
            print(f"   {ROJO}⚠️  NOMBRE FIJO{RESET} - La hoja DEBE llamarse '{nombre_hoja}'")
        else:
            print(f"   {VERDE}✓ FLEXIBLE{RESET} - Puede tener estos nombres: {', '.join(info['alternativas'])}")
        
        print(f"   Usado en {len(info['usado_en'])} archivo(s):")
        for uso in info['usado_en']:
            print(f"      - {uso}")
        print()
    
    return hojas_sistema


def verificar_hojas_empresas(db):
    """
    Verifica qué hojas tienen las empresas configuradas
    """
    print(f"\n{'='*80}")
    print(f"🏢 VERIFICACIÓN DE HOJAS EN EMPRESAS CONFIGURADAS")
    print(f"{'='*80}\n")
    
    empresas = db.exec(
        select(ConfiguracionEmpresa)
        .where(ConfiguracionEmpresa.link_google_sheets.isnot(None))
        .where(ConfiguracionEmpresa.link_google_sheets != "")
    ).all()
    
    if not empresas:
        print(f"{ROJO}❌ No hay empresas con Google Sheets configurado{RESET}")
        return
    
    print(f"Analizando {len(empresas)} empresa(s)...\n")
    
    hojas_requeridas = ["clientes", "proveedores", "MOVIMIENTOS", "stock"]
    resultados = {}
    
    for config in empresas:
        nombre = config.nombre_negocio or f"Empresa {config.id_empresa}"
        print(f"{'─'*80}")
        print(f"🏢 {nombre} (ID: {config.id_empresa})")
        print(f"   Sheet ID: {config.link_google_sheets[:40]}...")
        
        try:
            handler = TablasHandler(id_empresa=config.id_empresa, db=db)
            if not handler.client:
                print(f"   {ROJO}❌ No se pudo conectar{RESET}")
                continue
            
            sheet = handler.client.open_by_key(config.link_google_sheets)
            worksheets = sheet.worksheets()
            nombres_hojas = [ws.title for ws in worksheets]
            
            print(f"   Total de hojas: {len(nombres_hojas)}")
            
            # Verificar hojas requeridas
            hojas_encontradas = {}
            for requerida in hojas_requeridas:
                if requerida in nombres_hojas:
                    hojas_encontradas[requerida] = True
                    print(f"   {VERDE}✓{RESET} '{requerida}' encontrada")
                elif requerida == "stock":
                    # Buscar alternativas
                    alternativas = ['articulos', 'productos', 'inventory', 'inventario', 'items']
                    encontrada_alt = None
                    for alt in alternativas:
                        if alt in nombres_hojas:
                            encontrada_alt = alt
                            break
                    
                    if encontrada_alt:
                        hojas_encontradas[requerida] = True
                        print(f"   {VERDE}✓{RESET} 'stock' encontrada como '{encontrada_alt}'")
                    else:
                        hojas_encontradas[requerida] = False
                        print(f"   {ROJO}✗{RESET} '{requerida}' NO encontrada (ni alternativas)")
                else:
                    hojas_encontradas[requerida] = False
                    print(f"   {ROJO}✗{RESET} '{requerida}' NO encontrada")
            
            resultados[config.id_empresa] = {
                'nombre': nombre,
                'total_hojas': len(nombres_hojas),
                'hojas_encontradas': hojas_encontradas,
                'todas_ok': all(hojas_encontradas.values())
            }
            
        except gspread.exceptions.SpreadsheetNotFound:
            print(f"   {ROJO}❌ Documento no encontrado{RESET}")
            resultados[config.id_empresa] = {
                'nombre': nombre,
                'error': 'Documento no encontrado'
            }
        except Exception as e:
            print(f"   {ROJO}❌ Error: {e}{RESET}")
            resultados[config.id_empresa] = {
                'nombre': nombre,
                'error': str(e)
            }
    
    return resultados


def generar_resumen(resultados):
    """
    Genera resumen final del análisis
    """
    print(f"\n\n{'='*80}")
    print(f"📊 RESUMEN DE ANÁLISIS")
    print(f"{'='*80}\n")
    
    total = len(resultados)
    con_error = sum(1 for r in resultados.values() if 'error' in r)
    totalmente_ok = sum(1 for r in resultados.values() if r.get('todas_ok', False))
    con_problemas = total - con_error - totalmente_ok
    
    print(f"Total de empresas analizadas: {total}")
    print(f"{VERDE}✓ Configuradas correctamente: {totalmente_ok}{RESET}")
    print(f"{AMARILLO}⚠ Con hojas faltantes: {con_problemas}{RESET}")
    print(f"{ROJO}✗ Con errores de conexión: {con_error}{RESET}")
    
    if con_problemas > 0 or con_error > 0:
        print(f"\n{AMARILLO}⚠️  EMPRESAS QUE REQUIEREN ATENCIÓN:{RESET}\n")
        
        for id_emp, data in resultados.items():
            if 'error' in data:
                print(f"{ROJO}✗ {data['nombre']} (ID: {id_emp}){RESET}")
                print(f"  Error: {data['error']}\n")
            elif not data.get('todas_ok', False):
                print(f"{AMARILLO}⚠ {data['nombre']} (ID: {id_emp}){RESET}")
                print(f"  Hojas faltantes:")
                for hoja, encontrada in data['hojas_encontradas'].items():
                    if not encontrada:
                        print(f"    - {hoja}")
                print()
    
    # Recomendaciones
    print(f"\n{'='*80}")
    print(f"💡 RECOMENDACIONES")
    print(f"{'='*80}\n")
    
    print("1. HOJAS CON NOMBRE FIJO (deben llamarse exactamente así):")
    print(f"   - 'clientes' {ROJO}← OBLIGATORIO{RESET}")
    print(f"   - 'proveedores' {ROJO}← OBLIGATORIO{RESET}")
    print(f"   - 'MOVIMIENTOS' {ROJO}← OBLIGATORIO (en MAYÚSCULAS){RESET}")
    
    print("\n2. HOJA DE STOCK (acepta variantes):")
    print(f"   - 'stock' {VERDE}← RECOMENDADO{RESET}")
    print(f"   - Alternativas: 'articulos', 'productos', 'inventory', etc.")
    
    print("\n3. COLUMNAS REQUERIDAS:")
    print("   En 'clientes':")
    print("     - id-cliente o codigo_interno")
    print("     - nombre-usuario")
    print("     - CUIT-CUIL, whatsapp, mail, direccion, etc.")
    
    print("\n   En 'proveedores':")
    print("     - id o codigo_interno")
    print("     - nombre")
    print("     - cuit, telefono, etc.")
    
    print("\n   En 'MOVIMIENTOS':")
    print("     - Se generan automáticamente al registrar ventas")
    print("     - No requiere columnas previas")
    
    print("\n   En 'stock':")
    print("     - Código/codigo_interno/code (ID del producto)")
    print("     - cantidad/stock/stock_actual (cantidad en stock)")
    print("     - nombre/descripcion (descripción del producto)")
    print("     - precio (precio de venta)")


def main():
    print(f"\n{'#'*80}")
    print(f"# ANÁLISIS DE LECTURA DE HOJAS DE GOOGLE SHEETS")
    print(f"# Sistema de Gestión IMA")
    print(f"{'#'*80}")
    
    # Parte 1: Análisis de código
    hojas_sistema = analizar_uso_hojas()
    
    # Parte 2: Verificación en empresas
    db = next(get_db())
    try:
        resultados = verificar_hojas_empresas(db)
        
        if resultados:
            generar_resumen(resultados)
    finally:
        db.close()


if __name__ == "__main__":
    main()
