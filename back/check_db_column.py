import os
from pathlib import Path
from sqlmodel import create_engine, inspect, text
from dotenv import load_dotenv

# Load env variables from .env file in root (parent of back/)
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# Construct connection string
DB_USER = os.getenv("DB_USER", "gestion_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "password_secreto_123")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "3306")
DB_NAME = os.getenv("DB_NAME", "gestion_ima_db")

# Force IPv4 if localhost
if DB_HOST == "localhost":
    DB_HOST = "127.0.0.1"

DATABASE_URL = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

print(f"Connecting to: {DATABASE_URL}")

try:
    engine = create_engine(DATABASE_URL)
    inspector = inspect(engine)
    
    print("Connection successful!")
    
    columns = inspector.get_columns("consumo_mesa_detalle")
    print("\nColumns in 'consumo_mesa_detalle':")
    found_impreso = False
    for col in columns:
        print(f"- {col['name']} ({col['type']})")
        if col['name'] == 'impreso':
            found_impreso = True
            
    if found_impreso:
        print("\n✅ Column 'impreso' EXISTS.")
    else:
        print("\n❌ Column 'impreso' MISSING.")

except Exception as e:
    print(f"\n❌ Error connecting or inspecting: {e}")
