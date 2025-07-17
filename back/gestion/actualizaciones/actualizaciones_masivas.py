# /home/sgi_user/proyectos/sistema_gestion_ima/back/gestion/actualizaciones_masivas.py

from sqlmodel import Session, select
from typing import Dict, List, Any
import re

from back.modelos import Tercero, Articulo
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
def sincronizar_clientes_desde_sheets(db: Session) -> Dict[str, int]:
    """
    Sincroniza clientes en MODO DEPURACIÓN: guarda cada cliente uno por uno
    para identificar la fila exacta que causa el error.
    """
    handler = TablasHandler()
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
                "condicion_iva": cliente_sheet.get("Tipo de Cliente", "").strip() or "Consumidor Final"
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
def sincronizar_articulos_desde_sheets(db: Session) -> Dict[str, int]:
    """
    Sincroniza los artículos desde la hoja 'stock' de Google Sheets a la tabla 'articulos'.
    """
    handler = TablasHandler()
    
    # Asumimos que tienes una función para cargar artículos en tu handler
    print("Obteniendo datos de Google Sheets...")
    articulos_sheets = handler.cargar_articulos() # NECESITARÁS CREAR ESTA FUNCIÓN
    
    print("Obteniendo datos de la base de datos...")
    articulos_db_objetos = db.exec(select(Articulo)).all()

    if not articulos_sheets:
        return {"error": "No se pudieron cargar los datos de Google Sheets."}

    # Usamos el código de barras como clave única
    articulos_db_dict = {articulo.codigo_barras: articulo for articulo in articulos_db_objetos if articulo.codigo_barras}

    resumen = {"creados": 0, "actualizados": 0, "errores": 0}

    for articulo_sheet in articulos_sheets:
        codigo = str(articulo_sheet.get("Código", "")).strip()
        if not codigo:
            resumen["errores"] += 1
            continue

        articulo_existente = articulos_db_dict.get(codigo)
        
        # Extraer y limpiar datos del sheet
        descripcion = articulo_sheet.get("nombre", "Sin Descripción")
        precio_venta = limpiar_precio(articulo_sheet.get("precio", 0))
        venta_negocio = limpiar_precio(articulo_sheet.get("precio negocio", 0))
        stock_actual = limpiar_precio(articulo_sheet.get("cantidad", 0))
        activo = str(articulo_sheet.get("Activo", "TRUE")).upper() == "TRUE"

        if articulo_existente:
            # ACTUALIZAR
            print(f"Actualizando artículo: {codigo}")
            articulo_existente.descripcion = descripcion
            articulo_existente.precio_venta = precio_venta
            articulo_existente.venta_negocio = venta_negocio
            articulo_existente.stock_actual = stock_actual
            articulo_existente.activo = activo
            resumen["actualizados"] += 1
        else:
            # CREAR
            print(f"Creando nuevo artículo: {codigo}")
            nuevo_articulo = Articulo(
                codigo_barras=codigo,
                descripcion=descripcion,
                precio_venta=precio_venta,
                venta_negocio=venta_negocio,
                stock_actual=stock_actual,
                activo=activo
            )
            db.add(nuevo_articulo)
            resumen["creados"] += 1
            
    db.commit()
    print("Sincronización de artículos completada.")
    return resumen