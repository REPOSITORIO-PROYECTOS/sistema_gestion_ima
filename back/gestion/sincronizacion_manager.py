# /back/gestion/sincronizacion_manager.py

"""
Módulo de lógica de negocio para operaciones de sincronización.
Su principal responsabilidad es tomar datos de fuentes externas (como Google Sheets)
y poblarlos de manera inteligente en nuestra base de datos SQL, que es la
fuente única de verdad de la aplicación.
"""

from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import List, Dict, Any, Type, Optional

# Importamos los modelos de nuestra base de datos con los que vamos a trabajar
from back.modelos import Articulo, ArticuloCodigo, Categoria, ConfiguracionEmpresa, Marca
from back.utils.articulo_helpers import (
    conflicto_barcode_en_empresa,
    es_articulo_precio_manual,
    obtener_codigo_barras_articulo,
)

# Importamos nuestro "operario" para leer Google Sheets
from back.utils.tablas_handler import TablasHandler

# --- Función Auxiliar para manejar Categorías y Marcas ---
def _obtener_o_crear_relacion(db: Session, id_empresa: int, modelo: Type[Any], nombre: str) -> Any:
    """
    Busca una instancia de un modelo (Categoria o Marca) por su nombre.
    Si no existe, la crea. Esto evita duplicados.
    """
    if not nombre: # Si el nombre viene vacío desde el sheet
        return None

    # Busca si ya existe una con ese nombre para esa empresa
    instancia = db.exec(
        select(modelo).where(modelo.nombre == nombre, modelo.id_empresa == id_empresa)
    ).first()

    if instancia:
        return instancia
    else:
        # Si no existe, la crea y la añade a la sesión
        print(f"Creando nueva {modelo.__name__}: '{nombre}'")
        nueva_instancia = modelo(nombre=nombre, id_empresa=id_empresa)
        db.add(nueva_instancia)
        # No hacemos commit aquí, esperamos al final de la transacción principal.
        return nueva_instancia


def _procesar_codigos_barra(codigo_barra_string: str) -> List[str]:
    """
    Procesa códigos de barra que pueden venir con separadores ';' o ','
    Retorna una lista de códigos de barra
    
    Ejemplos:
    - '7798316700808;;' → ['7798316700808;;']
    - '7798316700808; 7790895643743' → ['7798316700808', '7790895643743']
    """
    if not codigo_barra_string or not str(codigo_barra_string).strip():
        return []
    
    # Convertir a string y limpiar espacios iniciales/finales
    codigo_str = str(codigo_barra_string).strip()
    
    # Si está vacío o solo tiene separadores, retornar lista vacía
    if not codigo_str or codigo_str.replace(';', '').replace(',', '').replace('|', '').replace(' ', '').strip() == '':
        return []
    
    # El código tal como viene es válido
    # Solo dividir si hay separadores de múltiples códigos
    if codigo_str.count(';') > 1 or (';' in codigo_str and len(codigo_str.split(';')) > 2):
        # Hay múltiples códigos separados
        codigos = codigo_str.split(';')
        codigos_limpios = []
        for codigo in codigos:
            codigo = codigo.strip()
            if codigo:
                codigos_limpios.append(codigo)
        return codigos_limpios if codigos_limpios else [codigo_str]
    
    # Si viene un solo código (incluso con ;; al final), mantenerlo tal como es
    return [codigo_str]


def sincronizar_articulos_desde_sheet(db: Session, id_empresa_actual: int, nombre_hoja: Optional[str] = None) -> Dict[str, Any]:
    """
    Orquesta el proceso completo de sincronización de artículos.
    Ahora con mapeo automático flexible de columnas.
    
    Args:
        db: Sesión de base de datos
        id_empresa_actual: ID de la empresa
        nombre_hoja: Nombre específico de la hoja (opcional, buscará automáticamente)
    """
    print(f"--- Iniciando Sincronización de Artículos para Empresa ID: {id_empresa_actual} ---")
    
    # 1. OBTENER CONFIGURACIÓN DE LA EMPRESA
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Operación fallida: La empresa no tiene un Google Sheet configurado."
        )

    # 2. LEER DATOS DEL GOOGLE SHEET (ya mapeados a formato estándar)
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    articulos_del_sheet = handler.cargar_articulos(nombre_hoja=nombre_hoja)

    if not articulos_del_sheet:
        return {
            "mensaje": "No se encontraron artículos en el Google Sheet.",
            "leidos_de_sheet": 0,
            "creados_en_db": 0,
            "actualizados_en_db": 0,
            "eliminados_en_db": 0,
            "filas_con_error": 0
        }

    print(f"Se encontraron {len(articulos_del_sheet)} filas en Google Sheets. Procesando...")
    
    # Contadores para el reporte final
    creados = 0
    actualizados = 0
    eliminados = 0
    filas_con_error = 0
    conflictos_codigos = 0
    codigos_duplicados_en_sheet = 0
    
    # Set para rastrear los códigos que SÍ existen en el sheet
    codigos_en_sheet = set()


    # 3. PROCESAR CADA FILA Y SINCRONIZAR
    for i, fila_sheet in enumerate(articulos_del_sheet):
        # Debug en la primera fila
        if i == 0:
            print(f"DEBUG: Campos mapeados disponibles: {[k for k in fila_sheet.keys() if k != '_fila_original']}")

        try:
            # Savepoint por fila: evita perder todo lo procesado por errores puntuales.
            with db.begin_nested():
                # Ya tiene formato estándar gracias al mapeo
                codigo_interno = fila_sheet.get('codigo_interno')
                descripcion = fila_sheet.get('descripcion')

                # Normalización del código
                if codigo_interno:
                    codigo_interno = str(codigo_interno).strip()

                # Validación básica
                if not codigo_interno or not descripcion:
                    print(f"⚠️ Fila {i+2}: Código o descripción vacíos. Saltando.")
                    filas_con_error += 1
                    continue

                # Agregamos el código al set de códigos válidos (normalizado)
                if codigo_interno in codigos_en_sheet:
                    codigos_duplicados_en_sheet += 1
                codigos_en_sheet.add(codigo_interno)

                # Obtener valores numéricos seguros
                precio_costo = fila_sheet.get('precio_costo', 0) or 0
                precio_venta = fila_sheet.get('precio_venta', 0) or 0
                venta_negocio = fila_sheet.get('venta_negocio', 0) or 0
                stock_actual = fila_sheet.get('stock_actual', 0) or 0
                tasa_iva = fila_sheet.get('tasa_iva', 0.21) or 0.21
                ubicacion = fila_sheet.get('ubicacion', 'Sin definir') or 'Sin definir'
                unidad_venta = fila_sheet.get('unidad_venta', 'Unidad') or 'Unidad'
                activo_raw = str(fila_sheet.get('Activo', 'TRUE')).strip().lower()
                activo_en_sheet = activo_raw in {'true', '1', 'si', 'sí', 'yes', 'y', 'on'}

                try:
                    precio_costo = float(precio_costo)
                    precio_venta = float(precio_venta)
                    venta_negocio = float(venta_negocio)
                    stock_actual = float(stock_actual)
                    tasa_iva = float(tasa_iva)
                except (ValueError, TypeError):
                    print(f"⚠️ Fila {i+2}: Error en conversión de números. Usando valores por defecto.")
                    precio_costo = 0.0
                    precio_venta = 0.0
                    venta_negocio = 0.0
                    stock_actual = 0.0
                    tasa_iva = 0.21

                # --- Lógica de UPSERT (Update or Insert) ---
                articulo_existente = db.exec(
                    select(Articulo).where(Articulo.codigo_interno == codigo_interno, Articulo.id_empresa == id_empresa_actual)
                ).first()

                # Manejo de relaciones (Categoría y Marca)
                nombre_categoria = fila_sheet.get('categoria')
                nombre_marca = fila_sheet.get('marca')

                categoria_obj = _obtener_o_crear_relacion(db, id_empresa_actual, Categoria, nombre_categoria)
                marca_obj = _obtener_o_crear_relacion(db, id_empresa_actual, Marca, nombre_marca)

                if articulo_existente:
                    # --- ACTUALIZAR ARTÍCULO EXISTENTE ---
                    print(f"  ✏️ Actualizando: {codigo_interno} - {descripcion}")
                    articulo_existente.descripcion = descripcion
                    articulo_existente.precio_costo = precio_costo
                    articulo_existente.precio_venta = precio_venta
                    articulo_existente.venta_negocio = venta_negocio
                    articulo_existente.stock_actual = stock_actual
                    articulo_existente.tasa_iva = tasa_iva
                    articulo_existente.ubicacion = ubicacion
                    articulo_existente.unidad_venta = unidad_venta
                    articulo_existente.activo = activo_en_sheet
                    if es_articulo_precio_manual(descripcion, codigo_interno):
                        articulo_existente.precio_manual = True
                        articulo_existente.auto_actualizar_precio = False
                    if categoria_obj:
                        articulo_existente.categoria = categoria_obj
                    if marca_obj:
                        articulo_existente.marca = marca_obj

                    db.add(articulo_existente)
                    articulo_actual = articulo_existente
                    actualizados += 1
                else:
                    # --- CREAR NUEVO ARTÍCULO ---
                    print(f"  ✨ Creando nuevo: {codigo_interno} - {descripcion}")
                    es_precio_manual = es_articulo_precio_manual(descripcion, codigo_interno)
                    nuevo_articulo = Articulo(
                        id_empresa=id_empresa_actual,
                        codigo_interno=codigo_interno,
                        descripcion=descripcion,
                        precio_costo=precio_costo,
                        precio_venta=precio_venta,
                        venta_negocio=venta_negocio,
                        stock_actual=stock_actual,
                        tasa_iva=tasa_iva,
                        ubicacion=ubicacion,
                        unidad_venta=unidad_venta,
                        activo=activo_en_sheet,
                        precio_manual=es_precio_manual,
                        auto_actualizar_precio=not es_precio_manual,
                        id_categoria=categoria_obj.id if categoria_obj else None,
                        id_marca=marca_obj.id if marca_obj else None
                    )
                    db.add(nuevo_articulo)
                    db.flush()  # obtener ID
                    articulo_actual = nuevo_articulo
                    creados += 1

                # --- PROCESAR CÓDIGOS DE BARRA (sin romper la fila por duplicados) ---
                codigos_barra = _procesar_codigos_barra(fila_sheet.get('Codigo de barras', ''))
                if codigos_barra:
                    # Eliminar códigos actuales del artículo y reconstruirlos desde hoja
                    codigos_antiguos = db.exec(
                        select(ArticuloCodigo).where(ArticuloCodigo.id_articulo == articulo_actual.id)
                    ).all()
                    for cod_antiguo in codigos_antiguos:
                        db.delete(cod_antiguo)
                    db.flush()

                    # Evitar repetir códigos dentro de la misma fila
                    codigos_unicos_fila = []
                    vistos_fila = set()
                    for c in codigos_barra:
                        c_norm = str(c).strip()
                        if c_norm and c_norm not in vistos_fila:
                            codigos_unicos_fila.append(c_norm)
                            vistos_fila.add(c_norm)

                    for codigo_barra in codigos_unicos_fila:
                        if obtener_codigo_barras_articulo(db, codigo_barra, articulo_actual.id):
                            continue

                        if conflicto_barcode_en_empresa(
                            db, codigo_barra, articulo_actual.id, id_empresa_actual
                        ):
                            print(
                                f"  ⚠️ Conflicto código '{codigo_barra}' para '{codigo_interno}' "
                                f"(ya asignado a otro artículo de la empresa)."
                            )
                            conflictos_codigos += 1
                            continue

                        db.add(ArticuloCodigo(codigo=codigo_barra, id_articulo=articulo_actual.id))
        
        except Exception as e:
            print(f"Error procesando la fila {i+2} ({fila_sheet.get('codigo_interno')}): {e}")
            filas_con_error += 1    
    
    # --- COMMIT 1: Guardar artículos nuevos/actualizados PRIMERO ---
    try:
        db.commit()
        print(f"✅ {creados + actualizados} artículos procesados y guardados correctamente.")
    except Exception as e:
        print(f"⚠️ Error durante commit de artículos: {e}")
        db.rollback()
        return {
            "mensaje": f"Error durante sincronización: {str(e)}",
            "leidos_de_sheet": len(articulos_del_sheet),
            "creados_en_db": creados,
            "actualizados_en_db": actualizados,
            "eliminados_en_db": 0,
            "filas_con_error": filas_con_error
        }
    
    # --- Lógica de Eliminación (Delete) ---
    # Eliminar artículos que están en la DB pero NO en el Sheet
    # IMPORTANTE: Solo eliminamos artículos SIN movimientos (ventas/compras)
    # Los artículos con historial se mantienen para preservar integridad
    
    # 1. Obtenemos todos los artículos de esta empresa
    articulos_en_db = db.exec(
        select(Articulo).where(Articulo.id_empresa == id_empresa_actual)
    ).all()
    
    eliminados = 0
    no_eliminados_con_movimientos = 0
    inactivados_con_movimientos = 0
    eliminacion_omitida_por_seguridad = False
    print(f"Verificando eliminaciones... Total en DB: {len(articulos_en_db)}. Total en Sheet (únicos): {len(codigos_en_sheet)}")
    print(f"Muestra de códigos en Sheet: {list(codigos_en_sheet)[:10]}")

    # Guardrail: si la lectura de sheet luce incompleta, no borrar/inactivar masivamente.
    if len(codigos_en_sheet) == 0:
        eliminacion_omitida_por_seguridad = True
        print("⚠️ Eliminación omitida por seguridad: el Sheet devolvió 0 códigos válidos.")

    if not eliminacion_omitida_por_seguridad and len(articulos_en_db) > 20:
        cobertura = len(codigos_en_sheet) / max(1, len(articulos_en_db))
        if cobertura < 0.2:
            eliminacion_omitida_por_seguridad = True
            print(
                f"⚠️ Eliminación omitida por seguridad: cobertura de Sheet muy baja ({cobertura:.2%})."
            )
    
    for articulo in articulos_en_db:
        if eliminacion_omitida_por_seguridad:
            break

        # Normalizamos también el código de la DB para comparar manzanas con manzanas
        codigo_db_normalizado = str(articulo.codigo_interno).strip()
        
        if codigo_db_normalizado not in codigos_en_sheet:
            # Verificar si el artículo tiene movimientos
            tiene_ventas = len(articulo.items_venta) > 0
            tiene_compras = len(articulo.items_compra) > 0
            
            if tiene_ventas or tiene_compras:
                print(f"  ⚠️ No se puede eliminar '{codigo_db_normalizado}' - Tiene movimientos históricos (Ventas: {len(articulo.items_venta)}, Compras: {len(articulo.items_compra)})")
                no_eliminados_con_movimientos += 1
                if getattr(articulo, "activo", True):
                    articulo.activo = False
                    articulo.stock_actual = 0
                    db.add(articulo)
                    inactivados_con_movimientos += 1
                    print(f"  📌 Artículo histórico inactivado: '{codigo_db_normalizado}' - {articulo.descripcion}")
            else:
                print(f"  🗑️ Eliminando artículo sin movimientos: '{codigo_db_normalizado}' - {articulo.descripcion}")
                db.delete(articulo)
                eliminados += 1
    
    # Actualizar versión de catálogo
    if config_empresa:
        try:
            config_empresa.catalogo_version = (config_empresa.catalogo_version or 0) + 1
            db.add(config_empresa)
        except Exception:
            pass
    
    # --- COMMIT 2: Guardar eliminaciones ---
    try:
        db.commit()
        print("✅ Sincronización completada exitosamente.")
        if no_eliminados_con_movimientos > 0:
            print(f"ℹ️ {no_eliminados_con_movimientos} artículo(s) no se eliminaron porque tienen movimientos históricos.")
        if inactivados_con_movimientos > 0:
            print(f"ℹ️ {inactivados_con_movimientos} artículo(s) históricos fueron inactivados para no mostrarse en catálogo activo.")
    except Exception as e:
        print(f"⚠️ Error no crítico durante commit de eliminaciones (ignorado): {type(e).__name__}")
        # No hacer rollback para preservar los cambios de artículos que ya fueron guardados
        try:
            db.rollback()
        except:
            pass
    
    print("--- Sincronización Finalizada ---")
    
    # 5. DEVOLVER UN REPORTE DEL RESULTADO
    return {
        "mensaje": "Sincronización completada.",
        "leidos_de_sheet": len(articulos_del_sheet),
        "creados_en_db": creados,
        "actualizados_en_db": actualizados,
        "eliminados_en_db": eliminados,
        "no_eliminados_con_movimientos": no_eliminados_con_movimientos,
        "inactivados_con_movimientos": inactivados_con_movimientos,
        "filas_con_error": filas_con_error,
        "conflictos_codigos": conflictos_codigos,
        "codigos_duplicados_en_sheet": codigos_duplicados_en_sheet,
        "eliminacion_omitida_por_seguridad": eliminacion_omitida_por_seguridad,
    }
