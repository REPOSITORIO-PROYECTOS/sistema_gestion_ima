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
from back.modelos import Articulo, Categoria, Marca, ConfiguracionEmpresa

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
    
    # Set para rastrear los códigos que SÍ existen en el sheet
    codigos_en_sheet = set()

    # 3. PROCESAR CADA FILA Y SINCRONIZAR
    for i, fila_sheet in enumerate(articulos_del_sheet):
        # Debug en la primera fila
        if i == 0:
            print(f"DEBUG: Campos mapeados disponibles: {[k for k in fila_sheet.keys() if k != '_fila_original']}")

        try:
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
            codigos_en_sheet.add(codigo_interno)

            # Obtener valores numéricos seguros
            precio_costo = fila_sheet.get('precio_costo', 0) or 0
            precio_venta = fila_sheet.get('precio_venta', 0) or 0
            venta_negocio = fila_sheet.get('venta_negocio', 0) or 0
            stock_actual = fila_sheet.get('stock_actual', 0) or 0
            tasa_iva = fila_sheet.get('tasa_iva', 0.21) or 0.21
            ubicacion = fila_sheet.get('ubicacion', 'Sin definir') or 'Sin definir'
            unidad_venta = fila_sheet.get('unidad_venta', 'Unidad') or 'Unidad'
            
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
                if categoria_obj:
                    articulo_existente.categoria = categoria_obj
                if marca_obj:
                    articulo_existente.marca = marca_obj
                
                db.add(articulo_existente)
                actualizados += 1
            else:
                # --- CREAR NUEVO ARTÍCULO ---
                print(f"  ✨ Creando nuevo: {codigo_interno} - {descripcion}")
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
                    id_categoria=categoria_obj.id if categoria_obj else None,
                    id_marca=marca_obj.id if marca_obj else None
                )
                db.add(nuevo_articulo)
                creados += 1
        
        except Exception as e:
            print(f"Error fatal procesando la fila {i+2} ({fila_sheet.get('codigo_interno')}): {e}")
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
    print(f"Verificando eliminaciones... Total en DB: {len(articulos_en_db)}. Total en Sheet (únicos): {len(codigos_en_sheet)}")
    print(f"Muestra de códigos en Sheet: {list(codigos_en_sheet)[:10]}")
    
    for articulo in articulos_en_db:
        # Normalizamos también el código de la DB para comparar manzanas con manzanas
        codigo_db_normalizado = str(articulo.codigo_interno).strip()
        
        if codigo_db_normalizado not in codigos_en_sheet:
            # Verificar si el artículo tiene movimientos
            tiene_ventas = len(articulo.items_venta) > 0
            tiene_compras = len(articulo.items_compra) > 0
            
            if tiene_ventas or tiene_compras:
                print(f"  ⚠️ No se puede eliminar '{codigo_db_normalizado}' - Tiene movimientos históricos (Ventas: {len(articulo.items_venta)}, Compras: {len(articulo.items_compra)})")
                no_eliminados_con_movimientos += 1
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
        "filas_con_error": filas_con_error
    }
