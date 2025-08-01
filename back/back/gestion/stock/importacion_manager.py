# /back/gestion/stock/importacion_manager.py

import pandas as pd
import io
from sqlmodel import Session, select
from typing import List

# Asegúrate de que las rutas de importación sean correctas para tu estructura
from back.modelos import Articulo, PlantillaMapeoProveedor, ArticuloProveedor
from back.schemas.importacion_schemas import ArticuloPreview, ImportacionPreviewResponse, ConfirmacionImportacionRequest

def _calcular_precio_venta(costo: float, margen: float, iva: float) -> float:
    """Calcula el precio de venta final aplicando margen e IVA."""
    precio_con_margen = costo * (1 + margen)
    precio_final = precio_con_margen * (1 + iva)
    return round(precio_final, 2)

def generar_previsualizacion_desde_archivo(
    db: Session,
    id_proveedor: int,
    id_empresa: int,
    archivo_bytes: bytes
) -> ImportacionPreviewResponse:
    """Lee un archivo Excel, lo compara con los datos actuales y devuelve una previsualización."""
    
    # 1. Obtener la plantilla de mapeo para este proveedor
    statement = select(PlantillaMapeoProveedor).where(
        PlantillaMapeoProveedor.id_proveedor == id_proveedor,
        PlantillaMapeoProveedor.id_empresa == id_empresa
    )
    plantilla = db.exec(statement).first()
    if not plantilla:
        raise ValueError("No se encontró una plantilla de importación para este proveedor.")

    # 2. Leer el archivo Excel usando pandas
    try:
        df = pd.read_excel(
            io.BytesIO(archivo_bytes),
            sheet_name=plantilla.nombre_hoja_excel or 0,
            skiprows=plantilla.fila_inicio - 1
        )
    except Exception as e:
        raise ValueError(f"Error al leer el archivo Excel: {e}")

    # 3. Preparar datos para la comparación
    mapeo = plantilla.mapeo_columnas
    # Invertimos el mapeo para renombrar las columnas del DataFrame a nuestros nombres estándar
    mapeo_inverso = {v: k for k, v in mapeo.items()}
    df.rename(columns=mapeo_inverso, inplace=True)

    required_cols = ["codigo_articulo_proveedor", "precio_costo"]
    if not all(col in df.columns for col in required_cols):
        raise ValueError(f"El archivo Excel debe contener las columnas mapeadas a: {required_cols}")

    # 4. Optimización: Pre-cargar todos los datos necesarios en memoria
    codigos_proveedor_df = df["codigo_articulo_proveedor"].dropna().tolist()
    
    stmt_asociaciones = select(ArticuloProveedor).where(
        ArticuloProveedor.id_proveedor == id_proveedor,
        ArticuloProveedor.codigo_articulo_proveedor.in_(codigos_proveedor_df)
    )
    asociaciones = db.exec(stmt_asociaciones).all()
    asociacion_map = {asc.codigo_articulo_proveedor: asc for asc in asociaciones}

    ids_articulos = [asc.id_articulo for asc in asociaciones]
    stmt_articulos = select(Articulo).where(Articulo.id.in_(ids_articulos), Articulo.id_empresa == id_empresa)
    articulos_db = db.exec(stmt_articulos).all()
    articulo_map = {art.id: art for art in articulos_db}

    # 5. Iterar y comparar
    previews = []
    codigos_no_encontrados = []

    for _, row in df.iterrows():
        codigo_prov = row.get("codigo_articulo_proveedor")
        costo_nuevo_str = row.get("precio_costo")
        
        if not codigo_prov or pd.isna(codigo_prov) or pd.isna(costo_nuevo_str):
            continue

        try:
            costo_nuevo = float(costo_nuevo_str)
        except (ValueError, TypeError):
            continue # Ignorar filas con costos no numéricos

        asociacion = asociacion_map.get(str(codigo_prov))
        if not asociacion:
            codigos_no_encontrados.append(str(codigo_prov))
            continue
        
        articulo = articulo_map.get(asociacion.id_articulo)
        if not articulo:
            # Esto no debería pasar si la BD está consistente, pero es una buena guarda
            continue

        # Comparamos precios (usando una pequeña tolerancia para floats)
        if abs(articulo.precio_costo - costo_nuevo) > 0.01:
            precio_venta_nuevo = articulo.precio_venta
            if articulo.auto_actualizar_precio:
                precio_venta_nuevo = _calcular_precio_venta(costo_nuevo, articulo.margen_ganancia, articulo.tasa_iva)

            preview = ArticuloPreview(
                id_articulo=articulo.id,
                codigo_interno=articulo.codigo_interno,
                descripcion=articulo.descripcion,
                costo_actual=articulo.precio_costo,
                costo_nuevo=round(costo_nuevo, 2),
                precio_venta_actual=articulo.precio_venta,
                precio_venta_nuevo=precio_venta_nuevo
            )
            previews.append(preview)

    # 6. Construir la respuesta
    resumen = f"Se encontraron {len(previews)} artículos para actualizar y {len(codigos_no_encontrados)} códigos de proveedor no fueron encontrados en el sistema."
    return ImportacionPreviewResponse(
        articulos_a_actualizar=previews,
        articulos_no_encontrados=codigos_no_encontrados,
        resumen=resumen
    )

def aplicar_actualizacion_de_precios(
    db: Session,
    id_empresa: int,
    confirmacion_data: ConfirmacionImportacionRequest
) -> dict:
    """Aplica las actualizaciones de precios confirmadas a la base de datos."""
    
    ids_articulos_a_actualizar = [item.id_articulo for item in confirmacion_data.articulos_a_actualizar]
    if not ids_articulos_a_actualizar:
        return {"status": "ok", "message": "No hay artículos para actualizar."}

    # Obtenemos los artículos de la BD en una sola consulta para actualizar
    stmt = select(Articulo).where(
        Articulo.id.in_(ids_articulos_a_actualizar),
        Articulo.id_empresa == id_empresa
    )
    articulos_map = {articulo.id: articulo for articulo in db.exec(stmt).all()}

    # Iteramos sobre los datos confirmados por el usuario
    for item_actualizar in confirmacion_data.articulos_a_actualizar:
        articulo_db = articulos_map.get(item_actualizar.id_articulo)
        if articulo_db:
            articulo_db.precio_costo = item_actualizar.costo_nuevo
            articulo_db.precio_venta = item_actualizar.precio_venta_nuevo
            db.add(articulo_db) # SQLModel se encarga de marcarlo para UPDATE
    
    db.commit()
    
    return {"status": "ok", "message": f"Se actualizaron {len(articulos_map)} artículos correctamente."}