# back/gestion/inventario/actualizacion_manager.py

import pandas as pd
from fastapi import UploadFile
from sqlmodel import Session, select
from typing import Dict

from back.modelos import Articulo, PlantillaProveedor, Tercero
from back.schemas.inventario_schemas import PlantillaCreate

def obtener_plantilla_por_proveedor(db: Session, proveedor_id: int) -> PlantillaProveedor | None:
    statement = select(PlantillaProveedor).where(PlantillaProveedor.id_proveedor == proveedor_id)
    return db.exec(statement).first()

def crear_o_actualizar_plantilla(db: Session, proveedor_id: int, plantilla_data: PlantillaCreate) -> PlantillaProveedor:
    # Verificamos si el proveedor existe
    proveedor = db.get(Tercero, proveedor_id)
    if not proveedor or not proveedor.es_proveedor:
        raise ValueError("El proveedor especificado no existe o no es un proveedor.")

    plantilla_actual = obtener_plantilla_por_proveedor(db, proveedor_id)

    if plantilla_actual:
        # Actualizamos la plantilla existente
        plantilla_actual.nombre_plantilla = plantilla_data.nombre_plantilla
        plantilla_actual.mapeo_columnas = plantilla_data.mapeo_columnas
        db_plantilla = plantilla_actual
    else:
        # Creamos una nueva plantilla
        db_plantilla = PlantillaProveedor.from_orm(plantilla_data, update={'id_proveedor': proveedor_id})
    
    db.add(db_plantilla)
    db.commit()
    db.refresh(db_plantilla)
    return db_plantilla

def procesar_archivo_precios(db: Session, proveedor_id: int, archivo: UploadFile) -> Dict:
    plantilla = obtener_plantilla_por_proveedor(db, proveedor_id)
    if not plantilla:
        raise ValueError("No existe una plantilla de importación para este proveedor. Por favor, cree una primero.")

    try:
        # Usamos pandas para leer el archivo Excel directamente desde la memoria
        df = pd.read_excel(archivo.file)
    except Exception as e:
        raise ValueError(f"Error al leer el archivo Excel: {e}")

    # Extraemos el mapeo de la plantilla
    mapeo = plantilla.mapeo_columnas
    col_codigo = mapeo.get("codigo_proveedor")
    col_precio = mapeo.get("precio_costo")

    if not col_codigo or not col_precio:
        raise ValueError("La plantilla no tiene definido 'codigo_proveedor' y/o 'precio_costo'.")

    # Renombramos las columnas del DataFrame para un acceso fácil y seguro
    df.columns = [str(c).upper() for c in df.columns]
    col_codigo = col_codigo.upper()
    col_precio = col_precio.upper()

    if col_codigo not in df.columns or col_precio not in df.columns:
        raise ValueError(f"Las columnas '{col_codigo}' o '{col_precio}' no se encontraron en el archivo Excel.")

    # --- Inicializamos contadores y listas para el informe ---
    actualizados = 0
    no_encontrados = []
    variaciones = []

    # --- Iteramos sobre cada fila del archivo Excel ---
    for index, row in df.iterrows():
        codigo = str(row[col_codigo]).strip()
        try:
            nuevo_precio = float(row[col_precio])
        except (ValueError, TypeError):
            continue # Si el precio no es un número válido, saltamos esta fila

        # Buscamos el artículo en nuestra BD por el código del proveedor
        statement = select(Articulo).where(Articulo.codigo_proveedor == codigo, Articulo.id_proveedor_principal == proveedor_id)
        articulo = db.exec(statement).first()

        if articulo:
            # Si lo encontramos, actualizamos
            if articulo.precio_costo > 0:
                variacion = ((nuevo_precio - articulo.precio_costo) / articulo.precio_costo) * 100
                variaciones.append(variacion)
            
            articulo.precio_costo = nuevo_precio
            db.add(articulo)
            actualizados += 1
        else:
            # Si no lo encontramos, lo añadimos a la lista de informe
            no_encontrados.append(codigo)

    db.commit() # Guardamos todos los cambios en la base de datos de una sola vez

    # --- Generamos el informe final ---
    variacion_promedio = sum(variaciones) / len(variaciones) if variaciones else 0.0
    
    return {
        "mensaje": "Archivo procesado exitosamente.",
        "articulos_actualizados": actualizados,
        "articulos_no_encontrados": no_encontrados,
        "variacion_promedio_porcentaje": round(variacion_promedio, 2)
    }