
import sys
import os
from sqlalchemy import text

# Add current directory to path so we can import database
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import engine

def add_column():
    print("Intentando agregar columna 'impreso' a 'consumo_mesa_detalle'...")
    with engine.connect() as connection:
        try:
            # Check if column exists first (MySQL specific syntax or just try/except)
            # We'll just try to add it.
            connection.execute(text("ALTER TABLE consumo_mesa_detalle ADD COLUMN impreso BOOLEAN DEFAULT FALSE"))
            connection.commit()
            print("✅ Columna agregada exitosamente.")
        except Exception as e:
            print(f"⚠️  Error (puede que ya exista): {e}")

if __name__ == "__main__":
    add_column()
