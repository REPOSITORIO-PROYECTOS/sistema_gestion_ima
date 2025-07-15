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
    2. Lee todos los clientes de la base de datos.
    3. Compara y decide si crear o actualizar.
    Retorna un diccionario con el resumen de las operaciones.
    """
    handler = TablasHandler()
    
    # 1. Obtener datos de las dos fuentes
    print("Obteniendo datos de Google Sheets...")
    clientes_sheets = handler.cargar_clientes() # Usamos la función que ya existe
    
    print("Obteniendo datos de la base de datos...")
    clientes_db_objetos = db.exec(select(Tercero).where(Tercero.es_cliente == True)).all()
    
    if not clientes_sheets:
        return {"error": "No se pudieron cargar los datos de Google Sheets."}

    # Convertimos la lista de objetos de la BDD en un diccionario para búsqueda rápida
    # Usamos la identificación fiscal (CUIT/CUIL) como clave única
    clientes_db_dict = {cliente.identificacion_fiscal: cliente for cliente in clientes_db_objetos if cliente.identificacion_fiscal}

    resumen = {"creados": 0, "actualizados": 0, "errores": 0}

    # 2. Iterar sobre los clientes de Google Sheets
    for cliente_sheet in clientes_sheets:
        cuit = str(cliente_sheet.get("CUIT-CUIL", "")).strip()
        if not cuit:
            resumen["errores"] += 1
            continue # Saltamos filas sin CUIT/CUIL

        # 3. Decidir si es una creación o una actualización
        cliente_existente = clientes_db_dict.get(cuit)

        if cliente_existente:
            # ACTUALIZAR
            print(f"Actualizando cliente: {cuit}")
            cliente_existente.nombre_razon_social = cliente_sheet.get("nombre-usuario", cliente_existente.nombre_razon_social)
            cliente_existente.telefono = str(cliente_sheet.get("whatsapp", cliente_existente.telefono))
            cliente_existente.email = cliente_sheet.get("mail", cliente_existente.email)
            cliente_existente.direccion = cliente_sheet.get("direccion", cliente_existente.direccion)
            cliente_existente.notas = cliente_sheet.get("observaciones", cliente_existente.notas)
            # Podrías añadir más campos para actualizar aquí
            resumen["actualizados"] += 1
        else:
            # CREAR
            print(f"Creando nuevo cliente: {cuit}")
            nuevo_cliente = Tercero(
                es_cliente=True,
                identificacion_fiscal=cuit,
                nombre_razon_social=cliente_sheet.get("nombre-usuario", "Sin Nombre"),
                telefono=str(cliente_sheet.get("whatsapp", "")),
                email=cliente_sheet.get("mail"),
                direccion=cliente_sheet.get("direccion"),
                notas=cliente_sheet.get("observaciones"),
                condicion_iva=cliente_sheet.get("Tipo de Cliente", "Consumidor Final"),
                activo=True
            )
            db.add(nuevo_cliente)
            resumen["creados"] += 1
            
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