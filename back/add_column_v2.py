
import sys
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load env from current directory or parent
load_dotenv()

DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = "127.0.0.1" # Force IPv4 localhost
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME")

print(f"Connecting to {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}...")

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
engine = create_engine(DATABASE_URL)

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
