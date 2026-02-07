import sys
import os
from sqlalchemy import text

# Add current directory to path so we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine

def add_estado_cocina():
    print("Intentando agregar columna 'estado_cocina' a 'consumo_mesa_detalle'...")
    with engine.connect() as connection:
        try:
            connection.execute(text("ALTER TABLE consumo_mesa_detalle ADD COLUMN estado_cocina VARCHAR(20) NOT NULL DEFAULT 'PENDIENTE'"))
            connection.commit()
            print("✅ Columna 'estado_cocina' agregada exitosamente.")
        except Exception as e:
            print(f"⚠️  Error (puede que ya exista): {e}")

if __name__ == "__main__":
    add_estado_cocina()
