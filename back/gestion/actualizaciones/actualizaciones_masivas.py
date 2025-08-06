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
                "condicion_iva": str(cliente_sheet.get("Tipo de Cliente", "")).strip() or "Consumidor Final",
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
            ubicacion_crudo = articulo_sheet.get("ubicacion", "Sin informacion")
            activo_crudo = articulo_sheet.get("Activo", "TRUE")
            activo_texto = str(activo_crudo).strip().upper()
            
            datos_limpios = {
                "descripcion": nombre_texto,
                "precio_venta": limpiar_precio(articulo_sheet.get("precio", 0)),
                "venta_negocio": limpiar_precio(articulo_sheet.get("precio negocio", 0)),
                "stock_actual": limpiar_precio(articulo_sheet.get("cantidad", 0)),
                "activo": activo_texto == "TRUE",
                "id_empresa": id_empresa_actual,
                "ubicacion": ubicacion_crudo,
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
                # Limpiamos y nos aseguramos de que sea una cadena. Este es el estado final deseado.
                codigo_barras_sheet = str(codigo_barras_crudo).strip()

                # 2. OBTENER EL CÓDIGO "ACTUAL" DESDE LA BASE DE DATOS PARA ESTE ARTÍCULO
                # Accedemos al primer código de la lista, si es que existe alguno.
                # Usamos la relación `codigos` definida en tus modelos.
                codigo_actual_db_obj = next(iter(articulo_actual_db.codigos), None)
                codigo_actual_db_str = codigo_actual_db_obj.codigo if codigo_actual_db_obj else ""

                # 3. COMPARAR Y DECIDIR SI SE NECESITA UNA ACCIÓN
                # Si el código en la base de datos ya es el mismo que el de la hoja, no hacemos nada.
                if codigo_actual_db_str == codigo_barras_sheet:
                    # print(f"--> Código de barras para '{articulo_actual_db.codigo_interno}' ya está actualizado. Sin cambios.")
                    pass # O puedes usar 'continue' si esto está dentro de un bucle más grande
                else:
                    # Si son diferentes, procedemos a la sincronización.
                    print(f"--> Actualizando código de barras para '{articulo_actual_db.codigo_interno}'. "
                        f"Viejo: '{codigo_actual_db_str}', Nuevo: '{codigo_barras_sheet}'.")

                    # 4. ELIMINAR EL CÓDIGO ANTIGUO (SI EXISTÍA)
                    # Este es el paso clave que faltaba en tu lógica original.
                    if codigo_actual_db_obj:
                        print(f"    - Eliminando código obsoleto: '{codigo_actual_db_str}'.")
                        # Quitamos la referencia del diccionario global para evitar inconsistencias
                        if codigo_actual_db_str in codigos_barras_db_dict:
                            del codigos_barras_db_dict[codigo_actual_db_str]
                        db.delete(codigo_actual_db_obj)
                        
                    # 5. AÑADIR EL CÓDIGO NUEVO (SI NO ESTÁ VACÍO)
                    # Aquí reutilizamos tu lógica original para manejar la creación y los conflictos.
                    if codigo_barras_sheet:
                        # Verificamos si el nuevo código ya existe en el sistema
                        codigo_barras_existente_db = codigos_barras_db_dict.get(codigo_barras_sheet)

                        if not codigo_barras_existente_db:
                            print(f"    + Creando y asociando nuevo código: '{codigo_barras_sheet}'.")
                            nuevo_codigo_barras = ArticuloCodigo(codigo=codigo_barras_sheet, articulo=articulo_actual_db)
                            db.add(nuevo_codigo_barras)
                            # Lo añadimos al diccionario para que las siguientes iteraciones lo reconozcan
                            codigos_barras_db_dict[codigo_barras_sheet] = nuevo_codigo_barras
                        else:
                            # El código existe, aplicamos lógica de re-asociación o conflicto
                            articulo_asociado = codigo_barras_existente_db.articulo
                            if not articulo_asociado:
                                print(f"    * Re-asociando código de barras huérfano '{codigo_barras_sheet}'.")
                                codigo_barras_existente_db.articulo = articulo_actual_db
                                db.add(codigo_barras_existente_db)
                            elif articulo_asociado.id_empresa == id_empresa_actual:
                                if articulo_asociado.id != articulo_actual_db.id:
                                    print(f"    * Re-asociando código '{codigo_barras_sheet}' (pertenecía a otro artículo de la misma empresa).")
                                    codigo_barras_existente_db.articulo = articulo_actual_db
                                    db.add(codigo_barras_existente_db)
                            else:
                                # Conflicto: El código pertenece a otra empresa y no se puede reasignar.
                                print(f"## ERROR DE CONFLICTO ##: El código '{codigo_barras_sheet}' ya está asignado "
                                    f"al artículo '{articulo_asociado.codigo_interno}' de la empresa ID {articulo_asociado.id_empresa}. "
                                    f"No se puede asignar al artículo '{articulo_actual_db.codigo_interno}'.")
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