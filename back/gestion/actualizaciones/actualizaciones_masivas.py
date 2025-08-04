# /home/sgi_user/proyectos/sistema_gestion_ima/back/gestion/actualizaciones_masivas.py

from fastapi import HTTPException
from requests import session
from sqlmodel import Session, select
from typing import Dict, List, Any
import re
from sqlalchemy.orm import selectinload
from back.modelos import ArticuloCodigo, ConfiguracionEmpresa, Tercero, Articulo
from back.utils.tablas_handler import TablasHandler

# Función auxiliar para limpiar los precios
def sincronizar_clientes_desde_sheets(db: Session, id_empresa_actual: int) -> Dict[str, int]:
    """
    Sincroniza clientes desde Google Sheets de forma robusta, emparejando registros
    existentes sin 'codigo_interno' a través de su CUIT para actualizarlos.
    """
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración de Google Sheets para la empresa ID {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    
    print("Obteniendo datos de clientes desde Google Sheets...")
    clientes_sheets = handler.cargar_clientes()
    if not clientes_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # --- CAMBIO CLAVE 1: Cargar TODOS los 'Tercero' de la empresa ---
    # Necesitamos cargar tanto clientes como proveedores para tener una visión completa
    # y poder usar el CUIT como un puente fiable.
    print("Obteniendo todos los Terceros de la base de datos (solo empresa actual)...")
    terceros_db_objetos = db.exec(
        select(Tercero).where(Tercero.id_empresa == id_empresa_actual)
    ).all()

    # --- CAMBIO CLAVE 2: Crear MÚLTIPLES diccionarios para búsqueda flexible ---
    terceros_por_codigo_interno = {
        tercero.codigo_interno: tercero 
        for tercero in terceros_db_objetos if tercero.codigo_interno
    }
    terceros_por_cuit = {
        tercero.cuit: tercero 
        for tercero in terceros_db_objetos if tercero.cuit
    }
    
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    for cliente_sheet in clientes_sheets:
        try:
            codigo_interno_sheet = str(cliente_sheet.get("id-cliente", "")).strip()
            if not codigo_interno_sheet:
                resumen["errores"] += 1
                continue

            cuit_sheet = str(cliente_sheet.get("CUIT-CUIL", "")).strip() or None

            # --- CAMBIO CLAVE 3: Lógica de emparejamiento inteligente ---
            tercero_existente = None
            
            # Prioridad 1: Buscar por 'codigo_interno'. Es la forma más directa.
            if codigo_interno_sheet in terceros_por_codigo_interno:
                tercero_existente = terceros_por_codigo_interno[codigo_interno_sheet]
            
            # Prioridad 2: Si no se encontró y hay CUIT, buscar por CUIT.
            elif cuit_sheet and cuit_sheet in terceros_por_cuit:
                candidato_por_cuit = terceros_por_cuit[cuit_sheet]
                # ¡Crucial! Solo lo consideramos un 'match' si su codigo_interno está vacío.
                if not candidato_por_cuit.codigo_interno:
                    print(f"Match encontrado por CUIT ({cuit_sheet}) para cliente de hoja '{codigo_interno_sheet}'. Vinculando...")
                    tercero_existente = candidato_por_cuit
                else:
                    # Conflicto: El CUIT ya está vinculado a OTRO código interno.
                    print(f"Advertencia de conflicto: CUIT {cuit_sheet} ya está asignado al código interno {candidato_por_cuit.codigo_interno}.")
            
            datos_limpios = {
                "codigo_interno": codigo_interno_sheet,
                "nombre_razon_social": str(cliente_sheet.get("nombre-usuario", f"Cliente #{codigo_interno_sheet}")).strip(),
                "telefono": str(cliente_sheet.get("whatsapp", "")).strip(),
                "email": str(cliente_sheet.get("mail", "")).strip() or None,
                "direccion": str(cliente_sheet.get("direccion", "")).strip(),
                "notas": str(cliente_sheet.get("observaciones", "")).strip(),
                "cuit": cuit_sheet,
                "condicion_iva": str(cliente_sheet.get("Tipo de Cliente", "")).strip() or "Consumidor Final",
                "id_empresa": id_empresa_actual,
                "es_cliente": True,
            }

            if tercero_existente:
                # --- ACTUALIZAR ---
                cambios_detectados = False
                for campo, valor_nuevo in datos_limpios.items():
                    valor_viejo = getattr(tercero_existente, campo)
                    # La condición `valor_nuevo is not None` puede ser problemática si quieres vaciar un campo.
                    # Es mejor comparar directamente los strings.
                    if str(valor_viejo or '') != str(valor_nuevo or ''):
                        setattr(tercero_existente, campo, valor_nuevo)
                        cambios_detectados = True
                
                if cambios_detectados:
                    print(f"Actualizando tercero con código interno: {codigo_interno_sheet}")
                    db.add(tercero_existente)
                    resumen["actualizados"] += 1
                else:
                    resumen["sin_cambios"] += 1
            else:
                # --- CREAR ---
                print(f"Creando nuevo cliente con código interno: {codigo_interno_sheet}")
                datos_limpios['activo'] = True # Solo al crear se establece como activo por defecto
                
                nuevo_cliente = Tercero(**datos_limpios)
                db.add(nuevo_cliente)
                resumen["creados"] += 1

        except Exception as e:
            codigo_info = cliente_sheet.get('id-cliente', 'SIN ID')
            print(f"Error fatal procesando la fila del sheet con id-cliente '{codigo_info}'. Detalle: {e}")
            resumen["errores"] += 1
            continue
            
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
    # 1. VERIFICAR CONFIGURACIÓN DE LA EMPRESA
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración o link de Google Sheets para la empresa ID: {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}
    
    # 2. CARGAR DATOS CRUDOS DESDE GOOGLE SHEETS
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    print("Obteniendo datos de Google Sheets...")
    articulos_sheets_crudos = handler.cargar_articulos()
    
    if not articulos_sheets_crudos:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    # 3. PRE-PROCESAR DATOS DE SHEETS PARA ELIMINAR DUPLICADOS
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

    # 4. CARGAR DATOS EXISTENTES DE LA BASE DE DATOS PARA COMPARAR
    print("Obteniendo datos de la base de datos...")
    articulos_db_objetos = db.exec(select(Articulo).where(Articulo.id_empresa == id_empresa_actual)).all()
    articulos_db_dict = {str(articulo.codigo_interno): articulo for articulo in articulos_db_objetos if articulo.codigo_interno}
    
    print("Obteniendo TODOS los códigos de barras de la base de datos...")
    query_codigos = select(ArticuloCodigo).options(selectinload(ArticuloCodigo.articulo))
    codigos_barras_db_objetos = db.exec(query_codigos).all()
    codigos_barras_db_dict = {cb.codigo: cb for cb in codigos_barras_db_objetos}
    
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    # 5. BUCLE PRINCIPAL DE SINCRONIZACIÓN
    for articulo_sheet in articulos_sheets:
        try:
            # Re-obtenemos el código interno ya limpio
            codigo_interno = str(articulo_sheet.get("Código", "")).strip()

            articulo_existente = articulos_db_dict.get(codigo_interno)
            
            # --- LIMPIEZA DE DATOS SEGURA (ANTI-ERRORES DE TIPO) ---
            # Se convierte cada valor a string ANTES de usar métodos de string.
            nombre_crudo = articulo_sheet.get("nombre", "Sin Descripción")
            nombre_texto = str(nombre_crudo).strip()

            activo_crudo = articulo_sheet.get("Activo", "TRUE")
            activo_texto = str(activo_crudo).strip().upper()
            
            datos_limpios = {
                "descripcion": nombre_texto,
                "precio_venta": limpiar_precio(articulo_sheet.get("precio", 0)),
                "venta_negocio": limpiar_precio(articulo_sheet.get("precio negocio", 0)),
                "stock_actual": limpiar_precio(articulo_sheet.get("cantidad", 0)),
                "activo": activo_texto == "TRUE",
                "id_empresa": id_empresa_actual,
            }

            articulo_actual_db = None

            if articulo_existente:
                # --- ACTUALIZAR ARTÍCULO ---
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
                # --- CREAR ARTÍCULO ---
                print(f"Creando nuevo artículo '{codigo_interno}' para empresa {id_empresa_actual}")
                nuevo_articulo = Articulo(codigo_interno=codigo_interno, **datos_limpios)
                db.add(nuevo_articulo)
                resumen["creados"] += 1
                articulo_actual_db = nuevo_articulo

            # --- SINCRONIZAR CÓDIGO DE BARRAS (con validación y limpieza) ---
            codigo_barras_crudo = articulo_sheet.get("Codigo de barras", "")
            codigo_barras_sheet = str(codigo_barras_crudo).strip()

            if codigo_barras_sheet:
                codigo_barras_existente_db = codigos_barras_db_dict.get(codigo_barras_sheet)

                if not codigo_barras_existente_db:
                    print(f"--> Creando y asociando nuevo código de barras '{codigo_barras_sheet}' al artículo '{codigo_interno}'.")
                    nuevo_codigo_barras = ArticuloCodigo(codigo=codigo_barras_sheet, articulo=articulo_actual_db)
                    db.add(nuevo_codigo_barras)
                    codigos_barras_db_dict[codigo_barras_sheet] = nuevo_codigo_barras
                else:
                    articulo_asociado = codigo_barras_existente_db.articulo
                    if not articulo_asociado:
                        print(f"--> Re-asociando código de barras huérfano '{codigo_barras_sheet}' al artículo '{codigo_interno}'.")
                        codigo_barras_existente_db.articulo = articulo_actual_db
                        db.add(codigo_barras_existente_db)
                    elif articulo_asociado.id_empresa == id_empresa_actual:
                        if articulo_asociado.id != articulo_actual_db.id:
                            print(f"--> Re-asociando código de barras '{codigo_barras_sheet}' al artículo '{codigo_interno}' (misma empresa).")
                            codigo_barras_existente_db.articulo = articulo_actual_db
                            db.add(codigo_barras_existente_db)
                    else:
                        print(f"## ERROR DE CONFLICTO ##: El código de barras '{codigo_barras_sheet}' ya está asignado "
                              f"al artículo '{articulo_asociado.codigo_interno}' de la empresa ID {articulo_asociado.id_empresa}. "
                              f"No se puede asignar al artículo '{codigo_interno}' de la empresa {id_empresa_actual}.")
                        resumen["errores"] += 1

        except Exception as e:
            codigo_info = articulo_sheet.get('Código', 'SIN CÓDIGO')
            print(f"Error fatal procesando la fila del sheet con código '{codigo_info}'. Detalle: {e}")
            print(f"Datos de la fila problemática: {articulo_sheet}")
            resumen["errores"] += 1
            # Importante: No hacer rollback aquí para no perder toda la transacción por una fila.
            # Simplemente continuamos con la siguiente. El rollback final se encargará si hay
            # un error de base de datos. Si el error es de Python, perdemos una fila, no todo.
            continue
            
    # 6. COMMIT FINAL DE LA TRANSACCIÓN
    try:
        db.commit()
        print("Sincronización de artículos y códigos de barras completada.")
    except Exception as e:
        print(f"ERROR FATAL DURANTE EL COMMIT: Se revirtió la transacción. Detalle: {e}")
        db.rollback()
        # Aquí podrías añadir un log más detallado del error de commit si es necesario.
        
    return resumen