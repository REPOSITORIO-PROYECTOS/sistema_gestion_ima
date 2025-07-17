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
    Sincroniza los clientes desde la hoja 'clientes' de Google Sheets a la tabla 'terceros'.
    
    1. Lee todos los clientes de Google Sheets.
    2. Usa el 'id_cliente' de la hoja como clave única de sincronización.
    3. Almacena este 'id_cliente' en el campo 'codigo_interno' de la tabla 'terceros'.
    4. Si un cliente con ese 'codigo_interno' existe, lo actualiza si hay campos diferentes o faltantes.
    5. Si no existe, lo crea.
    
    Retorna un diccionario con el resumen de las operaciones.
    """
    handler = TablasHandler()
    
    # 1. Obtener datos de las dos fuentes
    print("Obteniendo datos de clientes desde Google Sheets...")
    clientes_sheets = handler.cargar_clientes()
    
    print("Obteniendo datos de clientes desde la base de datos...")
    clientes_db_objetos = db.exec(select(Tercero).where(Tercero.es_cliente == True)).all()
    
    if not clientes_sheets:
        print("Advertencia: No se pudieron cargar datos de Google Sheets o la hoja está vacía.")
        return {"creados": 0, "actualizados": 0, "errores": 0, "sin_cambios": len(clientes_db_objetos)}

    # Creamos un diccionario de los clientes de la BD para una búsqueda rápida y eficiente
    # La clave será el 'codigo_interno', que almacena el 'id_cliente' de la hoja de cálculo.
    clientes_db_dict = {cliente.codigo_interno: cliente for cliente in clientes_db_objetos if cliente.codigo_interno}

    resumen = {"creados": 0, "actualizados": 0, "sin_cambios": 0, "errores": 0}

    # 2. Iterar sobre los clientes de Google Sheets
    for cliente_sheet in clientes_sheets:
        # ASUMIMOS que tu hoja de cálculo tiene una columna llamada 'id_cliente'.
        # Si se llama diferente, cámbialo aquí.
        id_cliente_sheet = str(cliente_sheet.get("id-cliente", "")).strip()
        
        if not id_cliente_sheet:
            print(f"Error: Fila en Google Sheets sin 'id_cliente'. Datos: {cliente_sheet}")
            resumen["errores"] += 1
            continue  # Saltamos filas que no tienen el ID, son inutilizables.

        # 3. Buscar si el cliente ya existe en nuestra base de datos usando el ID de la hoja
        cliente_existente = clientes_db_dict.get(id_cliente_sheet)

        if cliente_existente:
            # ACTUALIZAR: El cliente existe, ahora verificamos si algún campo necesita actualización.
            cambios_detectados = False
            
            # Comparamos campo por campo para ver si algo ha cambiado o está incompleto
            # Usamos 'or' para actualizar solo si el campo en la BD está vacío o es diferente
            if cliente_sheet.get("nombre-usuario") and cliente_existente.nombre_razon_social != cliente_sheet.get("nombre-usuario"):
                cliente_existente.nombre_razon_social = cliente_sheet.get("nombre-usuario")
                cambios_detectados = True
            
            if cliente_sheet.get("whatsapp") and str(cliente_existente.telefono) != str(cliente_sheet.get("whatsapp")):
                cliente_existente.telefono = str(cliente_sheet.get("whatsapp"))
                cambios_detectados = True

            if cliente_sheet.get("mail") and cliente_existente.email != cliente_sheet.get("mail"):
                cliente_existente.email = cliente_sheet.get("mail")
                cambios_detectados = True

            if cliente_sheet.get("direccion") and cliente_existente.direccion != cliente_sheet.get("direccion"):
                cliente_existente.direccion = cliente_sheet.get("direccion")
                cambios_detectados = True
            
            if cliente_sheet.get("observaciones") and cliente_existente.notas != cliente_sheet.get("observaciones"):
                cliente_existente.notas = cliente_sheet.get("observaciones")
                cambios_detectados = True
                
            if cliente_sheet.get("CUIT-CUIL") and cliente_existente.identificacion_fiscal != str(cliente_sheet.get("CUIT-CUIL")).strip():
                cliente_existente.identificacion_fiscal = str(cliente_sheet.get("CUIT-CUIL")).strip()
                cambios_detectados = True

            if cambios_detectados:
                print(f"Actualizando cliente con ID: {id_cliente_sheet}")
                db.add(cliente_existente) # Se marca para la sesión de SQLAlchemy
                resumen["actualizados"] += 1
            else:
                resumen["sin_cambios"] += 1
        
        else:
            # CREAR: No se encontró un cliente con este 'codigo_interno', así que lo creamos.
            print(f"Creando nuevo cliente con ID de Sheets: {id_cliente_sheet}")
            
            nuevo_cliente = Tercero(
                codigo_interno=id_cliente_sheet, # Guardamos el ID de sheets aquí
                es_cliente=True,
                identificacion_fiscal=str(cliente_sheet.get("CUIT-CUIL", "")).strip(),
                nombre_razon_social=cliente_sheet.get("nombre-usuario", f"Cliente #{id_cliente_sheet}"),
                telefono=str(cliente_sheet.get("whatsapp", "")),
                email=cliente_sheet.get("mail"),
                direccion=cliente_sheet.get("direccion"),
                notas=cliente_sheet.get("observaciones"),
                condicion_iva=cliente_sheet.get("Tipo de Cliente", "Consumidor Final"),
                activo=True
            )
            db.add(nuevo_cliente)
            resumen["creados"] += 1
            
    # Hacemos commit una sola vez al final para mayor eficiencia
    db.commit() 
    print("Sincronización de clientes completada.")
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