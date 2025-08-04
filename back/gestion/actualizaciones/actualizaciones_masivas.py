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
    Sincroniza los artículos y sus códigos de barras desde Google Sheets, adaptado
    para un entorno multi-empresa seguro.
    """
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)

    if not config_empresa or not config_empresa.link_google_sheets:
        print(f"Error: Falta configuración o link de Google Sheets para la empresa ID: {id_empresa_actual}.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}
    
    handler = TablasHandler(id_empresa=id_empresa_actual, db=db)
    
    print("Obteniendo datos de Google Sheets...")
    articulos_sheets = handler.cargar_articulos()
    
    if not articulos_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": 0}

    print("Obteniendo datos de la base de datos...")
    # Esta parte ya era correcta: solo carga artículos de la empresa actual.
    articulos_db_objetos = db.exec(select(Articulo).where(Articulo.id_empresa == id_empresa_actual)).all()
    articulos_db_dict = {articulo.codigo_interno: articulo for articulo in articulos_db_objetos if articulo.codigo_interno}
    
    ## ================================================================ ##
    ## CAMBIO CLAVE 1: Cargar códigos de barras con información de su   ##
    ## artículo y empresa asociados para detectar conflictos.           ##
    ## ================================================================ ##
    print("Obteniendo TODOS los códigos de barras de la base de datos...")
    
    # Usamos selectinload para cargar eficientemente el artículo relacionado
    # y así poder acceder a su id_empresa sin hacer más consultas.
    query_codigos = select(ArticuloCodigo).options(selectinload(ArticuloCodigo.articulo))
    codigos_barras_db_objetos = db.exec(query_codigos).all()
    
    # El diccionario sigue siendo global, porque los códigos de barras son únicos globalmente.
    codigos_barras_db_dict = {cb.codigo: cb for cb in codigos_barras_db_objetos}
    
    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    for articulo_sheet in articulos_sheets:
        try:
            # La clave para buscar artículos es el 'codigo_interno', pero solo dentro
            # del diccionario de la empresa actual, lo cual es correcto.
            codigo_interno = str(articulo_sheet.get("Código", "")).strip()
            if not codigo_interno:
                resumen["errores"] += 1
                continue

            articulo_existente = articulos_db_dict.get(codigo_interno)
            
            datos_limpios = {
                "descripcion": articulo_sheet.get("nombre", "Sin Descripción").strip(),
                "precio_venta": limpiar_precio(articulo_sheet.get("precio", 0)),
                "venta_negocio": limpiar_precio(articulo_sheet.get("precio negocio", 0)),
                "stock_actual": limpiar_precio(articulo_sheet.get("cantidad", 0)),
                "activo": str(articulo_sheet.get("Activo", "TRUE")).upper() == "TRUE",
                "id_empresa": id_empresa_actual, # Aseguramos siempre la empresa correcta
            }

            articulo_actual_db = None

            if articulo_existente:
                # --- ACTUALIZAR ARTÍCULO ---
                # Esta lógica es segura porque articulo_existente solo puede provenir de la empresa actual.
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
                # Esta lógica es segura, ya que el 'id_empresa' se pasa en datos_limpios.
                print(f"Creando nuevo artículo '{codigo_interno}' para empresa {id_empresa_actual}")
                nuevo_articulo = Articulo(codigo_interno=codigo_interno, **datos_limpios)
                db.add(nuevo_articulo)
                resumen["creados"] += 1
                
                articulo_actual_db = nuevo_articulo

            ## ================================================================ ##
            ## CAMBIO CLAVE 2: Nueva lógica de validación multi-empresa         ##
            ## para los códigos de barras.                                      ##
            ## ================================================================ ##
            
            codigo_barras_sheet = str(articulo_sheet.get("Codigo de barras", "")).strip()

            if codigo_barras_sheet:
                codigo_barras_existente_db = codigos_barras_db_dict.get(codigo_barras_sheet)

                if not codigo_barras_existente_db:
                    # CASO 1: El código de barras es totalmente nuevo. Se crea y asocia.
                    print(f"--> Creando y asociando nuevo código de barras '{codigo_barras_sheet}' al artículo '{codigo_interno}'.")
                    nuevo_codigo_barras = ArticuloCodigo(
                        codigo=codigo_barras_sheet,
                        articulo=articulo_actual_db
                    )
                    db.add(nuevo_codigo_barras)
                    codigos_barras_db_dict[codigo_barras_sheet] = nuevo_codigo_barras
                else:
                    # CASO 2: El código de barras YA EXISTE en la base de datos.
                    articulo_asociado = codigo_barras_existente_db.articulo
                    
                    if not articulo_asociado:
                        # Caso raro: código de barras huérfano. Lo re-asociamos.
                        print(f"--> Re-asociando código de barras huérfano '{codigo_barras_sheet}' al artículo '{codigo_interno}'.")
                        codigo_barras_existente_db.articulo = articulo_actual_db
                        db.add(codigo_barras_existente_db)
                    
                    elif articulo_asociado.id_empresa == id_empresa_actual:
                        # El código de barras pertenece a un artículo de la MISMA empresa.
                        if articulo_asociado.id != articulo_actual_db.id:
                            # Se está moviendo el código de barras a otro producto DENTRO de la misma empresa.
                            print(f"--> Re-asociando código de barras '{codigo_barras_sheet}' al artículo '{codigo_interno}' (misma empresa).")
                            codigo_barras_existente_db.articulo = articulo_actual_db
                            db.add(codigo_barras_existente_db)
                    
                    else:
                        # ¡CONFLICTO! El código de barras ya está en uso por OTRA empresa.
                        print(f"## ERROR DE CONFLICTO ##: El código de barras '{codigo_barras_sheet}' ya está asignado "
                              f"al artículo '{articulo_asociado.codigo_interno}' de la empresa ID {articulo_asociado.id_empresa}. "
                              f"No se puede asignar al artículo '{codigo_interno}' de la empresa {id_empresa_actual}.")
                        resumen["errores"] += 1
                        # No hacemos nada con este código de barras, se omite.

        except Exception as e:
            print(f"Error procesando la fila del sheet: {articulo_sheet}. Detalle: {e}")
            resumen["errores"] += 1
            db.rollback() 
            continue
            
    try:
        db.commit()
        print("Sincronización de artículos y códigos de barras completada.")
    except Exception as e:
        print(f"ERROR FATAL DURANTE EL COMMIT: Se revirtió la transacción. Detalle: {e}")
        db.rollback()
        
    return resumen