# /home/sgi_user/proyectos/sistema_gestion_ima/back/gestion/actualizaciones_masivas.py

import datetime
from fastapi import HTTPException
from requests import session
from sqlmodel import Session, select
from typing import Dict, List, Any
import re
from sqlalchemy.orm import selectinload
from back.modelos import ArticuloCodigo, ConfiguracionEmpresa, Tercero, Articulo
from back.utils.tablas_handler import TablasHandler

def limpiar_precio(valor_texto: str) -> float:
    if isinstance(valor_texto, (int, float)):
        return float(valor_texto)
    try:
        # Elimina el símbolo '$', espacios, y usa el punto como separador de miles
        valor_limpio = re.sub(r'[$\s.]', '', str(valor_texto)).replace(',', '.')
        return float(valor_limpio)
    except (ValueError, TypeError):
        return 0.0



# Función auxiliar para limpiar los precios
def sincronizar_clientes_desde_sheets(db: Session, id_empresa_actual: int) -> Dict[str, int]:
    """
    Sincroniza clientes desde Google Sheets.
    Si un cliente con el mismo (codigo_interno, id_empresa) existe, lo actualiza.
    Si no existe, lo crea.
    """
    # 1. VERIFICAR CONFIGURACIÓN
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración de Google Sheets para la empresa ID {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 2. CARGAR DATOS DE GOOGLE SHEETS
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    print("Obteniendo datos de clientes desde Google Sheets...")
    clientes_sheets = handler.cargar_clientes()
    if not clientes_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 3. CARGAR CLIENTES EXISTENTES DE LA EMPRESA ACTUAL EN UN DICCIONARIO
    print("Obteniendo clientes existentes de la base de datos (solo empresa actual)...")
    clientes_db_objetos = db.exec(
        select(Tercero).where(Tercero.id_empresa == id_empresa_actual)
    ).all()

    # La clave del diccionario será el 'codigo_interno', que corresponde al 'id-cliente' de la hoja.
    clientes_db_dict = {
        tercero.codigo_interno: tercero 
        for tercero in clientes_db_objetos if tercero.codigo_interno
    }
    
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    # 4. ITERAR Y SINCRONIZAR
    for cliente_sheet in clientes_sheets:
        try:
            # El 'id-cliente' de la hoja es nuestra clave de negocio 'codigo_interno'
            codigo_interno_sheet = str(cliente_sheet.get("id-cliente", "")).strip()
            if not codigo_interno_sheet:
                resumen["errores"] += 1
                continue

            # Buscamos el cliente en el diccionario que ya está filtrado por empresa
            cliente_existente = clientes_db_dict.get(codigo_interno_sheet)
            cuit_sheet = str(cliente_sheet.get("CUIT-CUIL", "")).strip() or None

            # Preparamos el conjunto de datos limpios que vienen del Excel
            datos_limpios = {
                "codigo_interno": codigo_interno_sheet,
                "nombre_razon_social": str(cliente_sheet.get("nombre-usuario", f"Cliente #{codigo_interno_sheet}")).strip(),
                "telefono": str(cliente_sheet.get("whatsapp", "")).strip(),
                "email": str(cliente_sheet.get("mail", "")).strip() or None,
                "direccion": str(cliente_sheet.get("direccion", "")).strip(),
                "notas": str(cliente_sheet.get("observaciones", "")).strip(),
                "cuit": cuit_sheet,
                "condicion_iva": str(cliente_sheet.get("condicion-iva", "")).strip() or "CONSUMIDOR_FINAL",
                "id_empresa": id_empresa_actual,
                "es_cliente": True,
            }

            if cliente_existente:
                # --- ACTUALIZAR CLIENTE EXISTENTE ---
                cambios_detectados = False
                for campo, valor_nuevo in datos_limpios.items():
                    valor_viejo = getattr(cliente_existente, campo)
                    if str(valor_viejo or '') != str(valor_nuevo or ''):
                        setattr(cliente_existente, campo, valor_nuevo)
                        cambios_detectados = True
                
                if cambios_detectados:
                    print(f"Actualizando cliente con código interno: {codigo_interno_sheet}")
                    db.add(cliente_existente)
                    resumen["actualizados"] += 1
                else:
                    resumen["sin_cambios"] += 1
            else:
                # --- CREAR NUEVO CLIENTE ---
                print(f"Creando nuevo cliente con código interno: {codigo_interno_sheet}")
                
                # Añadimos los valores por defecto que el modelo necesita al crear
                datos_limpios['activo'] = True
                datos_limpios['es_proveedor'] = False
                # Asumimos que el modelo Tercero maneja 'fecha_alta' con un default_factory
                
                nuevo_cliente = Tercero(**datos_limpios)
                db.add(nuevo_cliente)
                resumen["creados"] += 1

        except Exception as e:
            codigo_info = cliente_sheet.get('id-cliente', 'SIN ID')
            print(f"ERROR al procesar fila del sheet con id-cliente '{codigo_info}'. Detalle: {e}")
            resumen["errores"] += 1
            continue
            
    # 5. COMMIT FINAL
    try:
        db.commit()
        print("Sincronización de clientes completada.")
    except Exception as e:
        print(f"ERROR FATAL DURANTE EL COMMIT: Se revirtió la transacción. Detalle: {e}")
        db.rollback()
        
    return resumen
# ----- LÓGICA PARA ARTÍCULOS -----


def sincronizar_articulos_desde_sheets(db: Session, id_empresa_actual: int) -> Dict[str, int]:
    """
    Sincroniza los artículos y sus códigos de barras desde Google Sheets a la base de datos,
    implementando manejo de duplicados, validaciones multi-empresa y conversión de tipos segura.
    """
    # 1. VERIFICAR CONFIGURACIÓN DE LA EMPRESA (Sin cambios)
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración o link de Google Sheets para la empresa ID: {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}
    
    # 2. CARGAR DATOS CRUDOS DESDE GOOGLE SHEETS (Sin cambios)
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    print("Obteniendo datos de Google Sheets...")
    articulos_sheets_crudos = handler.cargar_articulos()
    
    if not articulos_sheets_crudos:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 3. PRE-PROCESAR DATOS DE SHEETS PARA ELIMINAR DUPLICADOS (Sin cambios)
    print(f"Se encontraron {len(articulos_sheets_crudos)} filas en Google Sheets. Procesando duplicados...")
    articulos_sheets_unicos = {}
    duplicados_omitidos = 0
    for articulo_sheet in articulos_sheets_crudos:
        codigo_interno_crudo = articulo_sheet.get("Código", "")
        codigo_interno = str(codigo_interno_crudo).strip()
        if not codigo_interno:
            continue

        if codigo_interno in articulos_sheets_unicos:
            duplicados_omitidos += 1
        articulos_sheets_unicos[codigo_interno] = articulo_sheet
        
    articulos_sheets = list(articulos_sheets_unicos.values())
    print(f"Procesando {len(articulos_sheets)} artículos únicos. Se omitieron {duplicados_omitidos} filas duplicadas.")

    # 4. CARGAR DATOS EXISTENTES DE LA BASE DE DATOS PARA COMPARAR (Sin cambios)
    print("Obteniendo datos de la base de datos...")
    # Usamos selectinload para cargar previamente los códigos de barras de cada artículo
    articulos_db_objetos = db.exec(
        select(Articulo)
        .where(Articulo.id_empresa == id_empresa_actual)
        .options(selectinload(Articulo.codigos))
    ).all()
    articulos_db_dict = {str(articulo.codigo_interno): articulo for articulo in articulos_db_objetos if articulo.codigo_interno}
    
    print("Obteniendo TODOS los códigos de barras de la base de datos...")
    query_codigos = select(ArticuloCodigo).options(selectinload(ArticuloCodigo.articulo))
    codigos_barras_db_objetos = db.exec(query_codigos).all()
    codigos_barras_db_dict = {cb.codigo: cb for cb in codigos_barras_db_objetos}
    
    resumen = {
        "leidos": len(articulos_sheets), 
        "creados": 0, 
        "actualizados": 0, 
        "sin_cambios": 0, 
        "errores": 0,
        "eliminados": 0,
        "no_eliminados_con_movimientos": 0
    }

    # 5. BUCLE PRINCIPAL DE SINCRONIZACIÓN (Lógica de artículo sin cambios)
    for articulo_sheet in articulos_sheets:
        try:
            codigo_interno = str(articulo_sheet.get("Código", "")).strip()
            articulo_existente = articulos_db_dict.get(codigo_interno)
            
            datos_limpios = {
                "descripcion": str(articulo_sheet.get("descripcion", "Sin Descripción")).strip(),
                "precio_venta": limpiar_precio(articulo_sheet.get("precio_venta", 0)),
                "venta_negocio": limpiar_precio(articulo_sheet.get("venta_negocio", 0)),
                "stock_actual": limpiar_precio(articulo_sheet.get("stock_actual", 0)),
                "activo": str(articulo_sheet.get("Activo", "TRUE")).strip().upper() == "TRUE",
                "id_empresa": id_empresa_actual,
                "ubicacion": str(articulo_sheet.get("ubicacion", "Sin informacion")).strip(),
                "unidad_venta": str(articulo_sheet.get("unidad", "Sin informacion")).strip(),
            }

            articulo_actual_db = None

            if articulo_existente:
                cambios_detectados = False
                for campo, valor_nuevo in datos_limpios.items():
                    if str(getattr(articulo_existente, campo)) != str(valor_nuevo):
                        setattr(articulo_existente, campo, valor_nuevo)
                        cambios_detectados = True
                
                if cambios_detectados:
                    print(f"-> Actualizando artículo '{codigo_interno}' para empresa {id_empresa_actual}")
                    db.add(articulo_existente)
                    resumen["actualizados"] += 1
                else:
                    resumen["sin_cambios"] += 1
                
                articulo_actual_db = articulo_existente
            else:
                print(f"Creando nuevo artículo '{codigo_interno}' para empresa {id_empresa_actual}")
                nuevo_articulo = Articulo(codigo_interno=codigo_interno, **datos_limpios)
                db.add(nuevo_articulo)
                # Necesitamos hacer flush para obtener el ID del nuevo artículo y poder asociar el código
                db.flush()
                resumen["creados"] += 1
                articulo_actual_db = nuevo_articulo

            # =================================================================================
            # === INICIO: BLOQUE DE CÓDIGO DE BARRAS REESTRUCTURADO (REEMPLAZAR EL ANTIGUO) ===
            # =================================================================================
            # Paso 1: Obtener el código deseado desde la hoja de cálculo (el estado final).
            codigo_barras_crudo = articulo_sheet.get("Codigo de barras", "")
            codigo_barras_sheet = str(codigo_barras_crudo).strip()

            # Paso 2: Obtener el código de barras que ESTE artículo tiene actualmente en la BD.
            codigo_actual_db_obj = next(iter(articulo_actual_db.codigos), None)
            codigo_actual_db_str = codigo_actual_db_obj.codigo if codigo_actual_db_obj else ""

            # Paso 3: Comparar y actuar. Solo hacemos algo si el código nuevo es diferente al viejo.
            if codigo_actual_db_str != codigo_barras_sheet:
                print(f"--> Sincronizando código de barras para '{codigo_interno}': "
                      f"Viejo='{codigo_actual_db_str}', Nuevo='{codigo_barras_sheet}'")

                # Paso 3a: Si había un código antiguo, debemos eliminarlo.
                if codigo_actual_db_obj:
                    print(f"    - Eliminando código obsoleto: '{codigo_actual_db_str}'")
                    if codigo_actual_db_str in codigos_barras_db_dict:
                        del codigos_barras_db_dict[codigo_actual_db_str]
                    db.delete(codigo_actual_db_obj)

                # Paso 3b: Si el nuevo código de la hoja no está vacío, procedemos a añadirlo/validarlo.
                if codigo_barras_sheet:
                    codigo_existente_en_sistema = codigos_barras_db_dict.get(codigo_barras_sheet)

                    if not codigo_existente_en_sistema:
                        print(f"    + Creando y asociando nuevo código: '{codigo_barras_sheet}'")
                        nuevo_codigo_barras = ArticuloCodigo(codigo=codigo_barras_sheet, articulo=articulo_actual_db)
                        db.add(nuevo_codigo_barras)
                        codigos_barras_db_dict[codigo_barras_sheet] = nuevo_codigo_barras
                    else:
                        articulo_asociado = codigo_existente_en_sistema.articulo
                        if not articulo_asociado:
                            print(f"    * Re-asociando código huérfano '{codigo_barras_sheet}'.")
                            codigo_existente_en_sistema.articulo = articulo_actual_db
                            db.add(codigo_existente_en_sistema)
                        elif articulo_asociado.id_empresa == id_empresa_actual:
                            if articulo_asociado.id != articulo_actual_db.id:
                                print(f"    * Re-asociando código '{codigo_barras_sheet}' (antes en '{articulo_asociado.codigo_interno}').")
                                codigo_existente_en_sistema.articulo = articulo_actual_db
                                db.add(codigo_existente_en_sistema)
                        else:
                            print(f"## ERROR DE CONFLICTO ##: El código '{codigo_barras_sheet}' ya está asignado "
                                  f"al artículo '{articulo_asociado.codigo_interno}' (empresa ID {articulo_asociado.id_empresa}). "
                                  f"No se puede asignar al artículo '{codigo_interno}' (empresa ID {id_empresa_actual}).")
                            resumen["errores"] += 1
            # ===============================================================================
            # === FIN: BLOQUE DE CÓDIGO DE BARRAS REESTRUCTURADO ==============================
            # ===============================================================================

        except Exception as e:
            codigo_info = articulo_sheet.get('Código', 'SIN CÓDIGO')
            print(f"Error fatal procesando la fila del sheet con código '{codigo_info}'. Detalle: {e}")
            print(f"Datos de la fila problemática: {articulo_sheet}")
            resumen["errores"] += 1
            continue
            
    # --- BLOQUE DE ELIMINACIÓN (Nuevo) ---
    print("--- Verificando eliminaciones de artículos obsoletos ---")
    eliminados = 0
    no_eliminados_con_movimientos = 0
    # Obtenemos los códigos que SÍ están en el sheet (ya procesados en articulos_sheets_unicos)
    codigos_validos_sheet = set(articulos_sheets_unicos.keys())
    
    # Importar modelos de venta y compra para verificar movimientos
    from back.modelos import VentaDetalle, CompraDetalle
    from sqlalchemy import func
    
    # Recorremos todos los artículos que teníamos en la DB al inicio
    # Nota: articulos_db_dict tiene {codigo: objeto}
    for codigo_db, articulo_db in articulos_db_dict.items():
        # Normalizamos por seguridad, aunque ya deberían estar normalizados en el dict
        if codigo_db not in codigos_validos_sheet:
            # PROTECCIÓN: Verificar si el artículo tiene movimientos (ventas o compras)
            tiene_ventas = db.exec(
                select(func.count()).select_from(VentaDetalle).where(VentaDetalle.id_articulo == articulo_db.id)
            ).first()
            
            tiene_compras = db.exec(
                select(func.count()).select_from(CompraDetalle).where(CompraDetalle.id_articulo == articulo_db.id)
            ).first()
            
            # Si tiene movimientos, no eliminamos
            if (tiene_ventas and tiene_ventas > 0) or (tiene_compras and tiene_compras > 0):
                print(f"🔒 PROTEGIDO: No eliminando artículo '{codigo_db}' (tiene {tiene_ventas or 0} ventas, {tiene_compras or 0} compras)")
                no_eliminados_con_movimientos += 1
            else:
                print(f"Eliminando artículo obsoleto (no encontrado en Sheet): '{codigo_db}' - {articulo_db.descripcion}")
                db.delete(articulo_db)
                eliminados += 1
            
    resumen["eliminados"] = eliminados
    resumen["no_eliminados_con_movimientos"] = no_eliminados_con_movimientos
    # -------------------------------------

    # 6. COMMIT FINAL DE LA TRANSACCIÓN (Sin cambios)
    try:
        db.commit()
        print("Sincronización de artículos y códigos de barras completada.")
    except Exception as e:
        print(f"ERROR FATAL DURANTE EL COMMIT: Se revirtió la transacción. Detalle: {e}")
        db.rollback()
        
    return resumen



def sincronizar_proveedores_desde_sheets(db: Session, id_empresa_actual: int) -> Dict[str, int]:
    """
    Sincroniza proveedores
    """
    # 1. VERIFICAR CONFIGURACIÓN
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración de Google Sheets para la empresa ID {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 2. CARGAR DATOS DE GOOGLE SHEETS
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    print("Obteniendo datos de clientes desde Google Sheets...")
    proveedores_sheets = handler.cargar_proveedores()
    if not proveedores_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 3. CARGAR CLIENTES EXISTENTES DE LA EMPRESA ACTUAL EN UN DICCIONARIO
    print("Obteniendo clientes existentes de la base de datos (solo empresa actual)...")
    clientes_db_objetos = db.exec(
        select(Tercero).where(Tercero.id_empresa == id_empresa_actual)
    ).all()

    # La clave del diccionario será el 'codigo_interno', que corresponde al 'id-cliente' de la hoja.
    clientes_db_dict = {
        tercero.codigo_interno: tercero 
        for tercero in clientes_db_objetos if tercero.codigo_interno
    }
    
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    # 4. ITERAR Y SINCRONIZAR
    for proveedor_sheet in proveedores_sheets:
        try:
            # El 'id-cliente' de la hoja es nuestra clave de negocio 'codigo_interno'
            codigo_interno_sheet = str(proveedor_sheet.get("id", "")).strip()
            if not codigo_interno_sheet:
                resumen["errores"] += 1
                continue

            # Buscamos el cliente en el diccionario que ya está filtrado por empresa
            proveedor_existente = clientes_db_dict.get(codigo_interno_sheet)
            cuit_sheet = str(proveedor_sheet.get("cuit", "")).strip() or None

            # Preparamos el conjunto de datos limpios que vienen del Excel
            datos_limpios = {
                "codigo_interno": codigo_interno_sheet,
                "nombre_razon_social": str(proveedor_sheet.get("nombre social", f"Proveedor #{codigo_interno_sheet}")).strip(),
                "telefono": str(proveedor_sheet.get("telefono", "")).strip(),
                "nombre_fantasia": str(proveedor_sheet.get("nombre fantasia", "")).strip() or None,
                "direccion": str(proveedor_sheet.get("direccion", "")).strip(),
                "identificacion_fiscal": str(proveedor_sheet.get("id fiscal", "")).strip(),
                "limite_credito": str(proveedor_sheet.get("limite credito", "")).strip(),
                "provincia": str(proveedor_sheet.get("provincia", "")).strip(),
                "cuit": cuit_sheet,
                "condicion_iva": str(proveedor_sheet.get("condicion iva", "")).strip() or "Consumidor Final",
                "id_empresa": id_empresa_actual,
                "es_proveedor": True,
                "es_cliente": False,
            }

            if proveedor_existente:
                # --- ACTUALIZAR CLIENTE EXISTENTE ---
                cambios_detectados = False
                for campo, valor_nuevo in datos_limpios.items():
                    valor_viejo = getattr(proveedor_existente, campo)
                    if str(valor_viejo or '') != str(valor_nuevo or ''):
                        setattr(proveedor_existente, campo, valor_nuevo)
                        cambios_detectados = True
                
                if cambios_detectados:
                    print(f"Actualizando cliente con código interno: {codigo_interno_sheet}")
                    db.add(proveedor_existente)
                    resumen["actualizados"] += 1
                else:
                    resumen["sin_cambios"] += 1
            else:
                # --- CREAR NUEVO CLIENTE ---
                print(f"Creando nuevo cliente con código interno: {codigo_interno_sheet}")
                
                # Añadimos los valores por defecto que el modelo necesita al crear
                datos_limpios['activo'] = True
                datos_limpios['es_cliente'] = False
                datos_limpios['es_proveedor'] = True
                # Asumimos que el modelo Tercero maneja 'fecha_alta' con un default_factory
                
                nuevo_cliente = Tercero(**datos_limpios)
                db.add(nuevo_cliente)
                resumen["creados"] += 1

        except Exception as e:
            codigo_info = proveedor_sheet.get('id', 'SIN ID')
            print(f"ERROR al procesar fila del sheet con id-cliente '{codigo_info}'. Detalle: {e}")
            resumen["errores"] += 1
            continue
            
    # 5. COMMIT FINAL
    try:
        db.commit()
        print("Sincronización de clientes completada.")
    except Exception as e:
        print(f"ERROR FATAL DURANTE EL COMMIT: Se revirtió la transacción. Detalle: {e}")
        db.rollback()
        
    return resumen
# ----- LÓGICA PARA ARTÍCULOS -----