import sys
import os
from sqlalchemy import text

# Add current directory to path so we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine

def fix_propina():
    print("Intentando agregar columnas 'propina' y 'porcentaje_propina' a 'consumo_mesa'...")
    with engine.connect() as connection:
        try:
            # Add propina
            try:
                connection.execute(text("ALTER TABLE consumo_mesa ADD COLUMN propina FLOAT DEFAULT 0.0"))
                print("✅ Columna 'propina' agregada.")
            except Exception as e:
                print(f"⚠️  Error al agregar 'propina' (puede que ya exista): {e}")

            # Add porcentaje_propina
            try:
                connection.execute(text("ALTER TABLE consumo_mesa ADD COLUMN porcentaje_propina FLOAT DEFAULT 0.0"))
                print("✅ Columna 'porcentaje_propina' agregada.")
            except Exception as e:
                print(f"⚠️  Error al agregar 'porcentaje_propina' (puede que ya exista): {e}")
                
            connection.commit()
            print("✅ Proceso finalizado.")
        except Exception as e:
            print(f"❌ Error de conexión o transacción: {e}")

if __name__ == "__main__":
    fix_propina()
