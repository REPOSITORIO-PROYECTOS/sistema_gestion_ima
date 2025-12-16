# /back/crear_hash.py
import sys
from passlib.context import CryptContext

# Esta línea DEBE ser idéntica a la de tu archivo de seguridad
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

if len(sys.argv) < 2:
    print("\nERROR: Debes proporcionar una contraseña.")
    print("Uso: python crear_hash.py 'tu_contraseña_secreta'\n")
    sys.exit(1)

password_plana = sys.argv[1]
hash_generado = pwd_context.hash(password_plana)

print("\n=============================================================")
print(f"  Contraseña Plana: {password_plana}")
print(f"  Hash Bcrypt Válido: {hash_generado}")
print("=============================================================")
print("\nCopia y pega este hash en la columna 'password_hash' de tu base de datos.\n")
