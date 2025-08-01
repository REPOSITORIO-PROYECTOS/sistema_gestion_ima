# /back/gestion/sincronizacion_manager.py

"""
Módulo de lógica de negocio para operaciones de sincronización.
Su principal responsabilidad es tomar datos de fuentes externas (como Google Sheets)
y poblarlos de manera inteligente en nuestra base de datos SQL, que es la
fuente única de verdad de la aplicación.
"""

from fastapi import HTTPException, status
from sqlmodel import Session, select
from typing import List, Dict, Any, Type

# Importamos los modelos de nuestra base de datos con los que vamos a trabajar
from back.modelos import Articulo, Categoria, Marca, ConfiguracionEmpresa

# Importamos nuestro "operario" para leer Google Sheets
from back.utils.tablas_handler import TablasHandler

# --- Función Auxiliar para manejar Categorías y Marcas ---
def _obtener_o_crear_relacion(db: Session, id_empresa: int, modelo: Type[Any], nombre: str) -> Any:
    """
    Busca una instancia de un modelo (Categoria o Marca) por su nombre.
    Si no existe, la crea. Esto evita duplicados.
    """
    if not nombre: # Si el nombre viene vacío desde el sheet
        return None

    # Busca si ya existe una con ese nombre para esa empresa
    instancia = db.exec(
        select(modelo).where(modelo.nombre == nombre, modelo.id_empresa == id_empresa)
    ).first()

    if instancia:
        return instancia
    else:
        # Si no existe, la crea y la añade a la sesión
        print(f"Creando nueva {modelo.__name__}: '{nombre}'")
        nueva_instancia = modelo(nombre=nombre, id_empresa=id_empresa)
        db.add(nueva_instancia)
        # No hacemos commit aquí, esperamos al final de la transacción principal.
        return nueva_instancia


def sincronizar_articulos_desde_sheet(db: Session, id_empresa_actual: int) -> Dict[str, Any]:
    """
    Orquesta el proceso completo de sincronización de artículos.
    1. Obtiene el link del Google Sheet desde la configuración de la empresa.
    2. Lee los datos del Sheet usando el TablasHandler.
    3. Itera sobre cada fila y decide si crear un nuevo artículo en SQL o actualizar uno existente.
    """
    print(f"--- Iniciando Sincronización de Artículos para Empresa ID: {id_empresa_actual} ---")
    
    # 1. OBTENER CONFIGURACIÓN DE LA EMPRESA
    config_empresa = db.get(ConfiguracionEmpresa, id_empresa_actual)
    if not config_empresa or not config_empresa.link_google_sheets:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail="Operación fallida: La empresa no tiene un Google Sheet configurado."
        )
    link_de_la_empresa = config_empresa.link_google_sheets

    # 2. LEER DATOS DEL GOOGLE SHEET
    handler = TablasHandler()
    articulos_del_sheet = handler.cargar_articulos(google_sheet_id=link_de_la_empresa)

    if not articulos_del_sheet:
        return {"mensaje": "Sincronización finalizada. No se encontraron artículos en el Google Sheet.", "creados": 0, "actualizados": 0, "errores": 0}

    print(f"Se encontraron {len(articulos_del_sheet)} filas en Google Sheets. Procesando...")
    
    # Contadores para el reporte final
    creados = 0
    actualizados = 0
    filas_con_error = 0
    
    # 3. PROCESAR CADA FILA Y SINCRONIZAR
    for i, fila_sheet in enumerate(articulos_del_sheet):
        try:
            # --- Lectura Segura de Columnas ---
            # Usamos .get() para evitar errores si una columna no existe en el Sheet.
            codigo_interno = fila_sheet.get('codigo_interno')
            descripcion = fila_sheet.get('descripcion')
            
            # Si el código o la descripción no existen, la fila es inválida.
            if not codigo_interno or not descripcion:
                print(f"Error en fila {i+2}: 'codigo_interno' o 'descripcion' están vacíos. Saltando.")
                filas_con_error += 1
                continue

            # --- Lógica de UPSERT (Update or Insert) ---
            articulo_existente = db.exec(
                select(Articulo).where(Articulo.codigo_interno == codigo_interno, Articulo.id_empresa == id_empresa_actual)
            ).first()

            # Manejo de relaciones (Categoría y Marca)
            nombre_categoria = fila_sheet.get('categoria')
            nombre_marca = fila_sheet.get('marca')
            
            categoria_obj = _obtener_o_crear_relacion(db, id_empresa_actual, Categoria, nombre_categoria)
            marca_obj = _obtener_o_crear_relacion(db, id_empresa_actual, Marca, nombre_marca)

            if articulo_existente:
                # --- ACTUALIZAR ARTÍCULO EXISTENTE ---
                print(f"Actualizando artículo: {codigo_interno} - {descripcion}")
                articulo_existente.descripcion = descripcion
                articulo_existente.precio_costo = float(fila_sheet.get('precio_costo', 0.0))
                articulo_existente.precio_venta = float(fila_sheet.get('precio_venta', 0.0))
                articulo_existente.stock_actual = float(fila_sheet.get('stock_actual', 0.0))
                articulo_existente.tasa_iva = float(fila_sheet.get('tasa_iva', 0.21))
                # Asigna las relaciones
                articulo_existente.categoria = categoria_obj
                articulo_existente.marca = marca_obj
                
                db.add(articulo_existente)
                actualizados += 1
            else:
                # --- CREAR NUEVO ARTÍCULO ---
                print(f"Creando nuevo artículo: {codigo_interno} - {descripcion}")
                nuevo_articulo = Articulo(
                    id_empresa=id_empresa_actual,
                    codigo_interno=codigo_interno,
                    descripcion=descripcion,
                    precio_costo=float(fila_sheet.get('precio_costo', 0.0)),
                    precio_venta=float(fila_sheet.get('precio_venta', 0.0)),
                    stock_actual=float(fila_sheet.get('stock_actual', 0.0)),
                    tasa_iva=float(fila_sheet.get('tasa_iva', 0.21)),
                    # Asigna las relaciones
                    categoria=categoria_obj,
                    marca=marca_obj
                )
                db.add(nuevo_articulo)
                creados += 1
        
        except Exception as e:
            print(f"Error fatal procesando la fila {i+2} ({fila_sheet.get('codigo_interno')}): {e}")
            filas_con_error += 1
            
    # 4. GUARDAR TODOS LOS CAMBIOS EN LA BASE DE DATOS
    # El commit se hace una sola vez al final, haciendo la operación atómica.
    db.commit()
    
    print("--- Sincronización Finalizada ---")
    
    # 5. DEVOLVER UN REPORTE DEL RESULTADO
    return {
        "mensaje": "Sincronización completada.",
        "leidos_de_sheet": len(articulos_del_sheet),
        "creados_en_db": creados,
        "actualizados_en_db": actualizados,
        "filas_con_error": filas_con_error
    }