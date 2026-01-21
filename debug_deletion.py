
import sys
import os

# Añadimos el directorio raíz al path para poder importar módulos de 'back'
sys.path.append(os.getcwd())

from sqlmodel import Session, select, create_engine
from back.modelos import Articulo, ConfiguracionEmpresa
from back.utils.tablas_handler import TablasHandler
from back.config import DB_HOST, DB_USER, DB_PASSWORD, DB_PORT, DB_NAME

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Configuración
ID_EMPRESA = 33  # Según logs previos
PRODUCTO_BUSCADO = "yogurt dahi x 200g"

def debug_sync():
    print(f"--- INICIANDO DIAGNÓSTICO PARA EMPRESA {ID_EMPRESA} ---")
    
    # 1. Conectar a la DB
    engine = create_engine(DATABASE_URL)
    
    with Session(engine) as db:
        # 2. Buscar el artículo en la DB
        print(f"Buscando '{PRODUCTO_BUSCADO}' en la base de datos...")
        articulos = db.exec(
            select(Articulo).where(Articulo.id_empresa == ID_EMPRESA)
        ).all()
        
        articulo_target = None
        for art in articulos:
            if PRODUCTO_BUSCADO.lower() in art.descripcion.lower():
                print(f"!!! ENCONTRADO EN DB: ID={art.id}, Codigo='{art.codigo_interno}', Desc='{art.descripcion}'")
                articulo_target = art
                # No hacemos break por si hay duplicados
        
        if not articulo_target:
            print("❌ El producto no se encontró en la base de datos local. (¿Ya fue borrado?)")
            return

        # 3. Leer el Google Sheet
        print("\nLeyendo Google Sheet...")
        handler = TablasHandler(id_empresa=ID_EMPRESA, db=db)
        
        # Simulamos la lógica de sincronizacion_manager.py
        try:
            articulos_del_sheet = handler.cargar_articulos()
        except Exception as e:
            print(f"❌ Error al cargar sheet: {e}")
            return

        print(f"Se encontraron {len(articulos_del_sheet)} filas en el Sheet.")
        
        # 4. Verificar si el código existe en el Sheet
        codigos_en_sheet = set()
        
        print("\nAnalizando códigos del Sheet...")
        encontrado_en_sheet = False
        
        for i, fila in enumerate(articulos_del_sheet):
            # Lógica exacta del manager
            raw_codigo = fila.get('codigo_interno') or fila.get('Código') or fila.get('codigo')
            codigo_normalizado = str(raw_codigo).strip() if raw_codigo else None
            
            if codigo_normalizado:
                codigos_en_sheet.add(codigo_normalizado)
                
                # Chequeo específico para nuestro target
                if codigo_normalizado == str(articulo_target.codigo_interno).strip():
                    print(f"⚠️ EL CÓDIGO '{codigo_normalizado}' SÍ ESTÁ EN EL SHEET (Fila {i+2})")
                    print(f"   Datos fila: {fila}")
                    encontrado_en_sheet = True

        # 5. Conclusión
        codigo_db_norm = str(articulo_target.codigo_interno).strip()
        print(f"\n--- CONCLUSIÓN ---")
        print(f"Código en DB (normalizado): '{codigo_db_norm}'")
        print(f"¿Está en el set de códigos del Sheet?: {codigo_db_norm in codigos_en_sheet}")
        
        if codigo_db_norm in codigos_en_sheet:
            print("❌ EL SISTEMA NO LO BORRA PORQUE SIGUE EXISTIENDO EN EL SHEET.")
            print("   Revise bien el archivo de Google Sheets. Busque el código exacto.")
        else:
            print("✅ EL SISTEMA DEBERÍA BORRARLO. Si no lo hace, el problema es que la función de sync no se está ejecutando o falla antes de llegar al delete.")

if __name__ == "__main__":
    debug_sync()
