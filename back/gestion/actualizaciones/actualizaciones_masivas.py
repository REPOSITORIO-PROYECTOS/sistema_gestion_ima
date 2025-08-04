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
def limpiar_precio(valor_texto: str) -> float:
    if isinstance(valor_texto, (int, float)):
        return float(valor_texto)
    try:
        # Elimina el símbolo '$', espacios, y usa el punto como separador de miles
        valor_limpio = re.sub(r'[$\s.]', '', str(valor_texto)).replace(',', '.')
        return float(valor_limpio)
    except (ValueError, TypeError):
        return 0.0

# ----- LÓGICA PARA CLIENTES -----
def sincronizar_clientes_desde_sheets(db: Session, id_empresa_actual: int) -> Dict[str, int]:
    """
    Sincroniza clientes en MODO DEPURACIÓN: guarda cada cliente uno por uno
    para identificar la fila exacta que causa el error.
    """
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)

    if not config_empresa or not config_empresa.link_google_sheets:
        print("error falta algo")
        return
    
    link_de_la_empresa = config_empresa.link_google_sheets

    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    print("Obteniendo datos de clientes desde Google Sheets...")
    clientes_sheets = handler.cargar_clientes()
    print("Obteniendo datos de clientes desde la base de datos...")
    clientes_db_objetos = db.exec(select(Tercero).where(Tercero.es_cliente == True)).all()

    if not clientes_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": len(clientes_db_objetos)}

    clientes_db_dict = {str(cliente.id): cliente for cliente in clientes_db_objetos}
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    # Iterar sobre los clientes de Google Sheets
    for cliente_sheet in clientes_sheets:
        id_cliente_sheet_str = "" # Inicializamos para el bloque except
        try:
            # --- LIMPIEZA Y VALIDACIÓN ---
            id_cliente_sheet_str = str(cliente_sheet.get("id-cliente", "")).strip()
            if not id_cliente_sheet_str:
                print(f"Error: Fila en Google Sheets sin 'id-cliente'. Datos: {cliente_sheet}")
                resumen["errores"] += 1
                continue
            id_cliente_sheet_int = int(id_cliente_sheet_str)

            # --- BÚSQUEDA Y LÓGICA ---
            cliente_existente = clientes_db_dict.get(id_cliente_sheet_str)
            cuit_raw = str(cliente_sheet.get("CUIT-CUIL", "")).strip()
            cuit_limpio = cuit_raw if cuit_raw else None # Convierte cadenas vacías a None

            datos_limpios = {
                "nombre_razon_social": cliente_sheet.get("nombre-usuario", f"Cliente #{id_cliente_sheet_str}").strip(),
                "telefono": str(cliente_sheet.get("whatsapp", "")).strip(),
                "email": cliente_sheet.get("mail", "").strip() or None,
                "direccion": cliente_sheet.get("direccion", "").strip(),
                "notas": cliente_sheet.get("observaciones", "").strip(),
                "cuit": cuit_limpio, # <-- USAMOS EL CUIT YA VALIDADO
                "condicion_iva": cliente_sheet.get("Tipo de Cliente", "").strip() or "Consumidor Final",
                "id_empresa": id_empresa_actual,
            }

            if cliente_existente:
                # --- ACTUALIZAR ---
                cambios_detectados = False
                for campo, valor_nuevo in datos_limpios.items():
                    valor_viejo = getattr(cliente_existente, campo)
                    if valor_nuevo is not None and str(valor_viejo) != str(valor_nuevo):
                        setattr(cliente_existente, campo, valor_nuevo)
                        cambios_detectados = True
                
                if cambios_detectados:
                    print(f"Actualizando cliente con ID: {id_cliente_sheet_str}")
                    db.add(cliente_existente)
                    resumen["actualizados"] += 1
                else:
                    resumen["sin_cambios"] += 1
            
            else:
                # --- CREAR ---
                print(f"Creando nuevo cliente con ID de Sheets: {id_cliente_sheet_str}")
                nuevo_cliente = Tercero(
                    id=id_cliente_sheet_int,
                    es_cliente=True,
                    activo=True,
                    **datos_limpios
                )
                db.add(nuevo_cliente)
                resumen["creados"] += 1

            # <<<<<<< CAMBIO CLAVE: HACEMOS COMMIT DENTRO DEL BUCLE >>>>>>>
            # Intentamos guardar los cambios para ESTE cliente específico.
            db.commit()

        except Exception as e:
            # Si algo falla, será para el cliente actual.
            print(f"!!!!!!!! ERROR AL PROCESAR/GUARDAR CLIENTE ID {id_cliente_sheet_str} !!!!!!!!")
            print(f"!!!!!!!! DETALLE DEL ERROR: {e} !!!!!!!!")
            print(f"!!!!!!!! DATOS DE LA FILA: {cliente_sheet} !!!!!!!!")
            resumen["errores"] += 1
            db.rollback() # Revertimos la operación fallida para este cliente.
            continue # Y continuamos con el siguiente.
            
    print("Sincronización de clientes (modo depuración) completada.")
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