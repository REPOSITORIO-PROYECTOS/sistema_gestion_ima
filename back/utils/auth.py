# gestion/auth.py
import json
import os
import random
import time
from datetime import datetime, timedelta
# Importaciones necesarias para la nueva función
from .mysql_handler import get_db_connection
from passlib.context import CryptContext
from back.utils.sheets_google_handler import GoogleSheetsHandler
from back import config

# ------ GESTIÓN DE TOKEN DE ADMINISTRADOR ------
# Usaremos un archivo local para el token, pero podría ser una hoja de cálculo también.

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verificar_password(plain_password: str, hashed_password: str) -> bool:
    """Verifica una contraseña en texto plano contra una hasheada."""
    return pwd_context.verify(plain_password, hashed_password)



def _cargar_token_data():
    """Carga los datos del token desde un archivo local."""
    if os.path.exists(config.ADMIN_TOKEN_LOCAL_FILE):
        try:
            with open(config.ADMIN_TOKEN_LOCAL_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None # Archivo corrupto
    return None


def autenticar_usuario(nombre_usuario: str, password: str):
    """
    Busca al usuario en la base de datos y verifica su contraseña.
    (VERSIÓN DE DEPURACIÓN FORENSE)
    """
    print("\n--- INICIO DE AUTENTICACIÓN ---")
    print(f"DEBUG: Intentando autenticar usuario: '{nombre_usuario}' con contraseña: '{password}'")
    
    conn = get_db_connection()
    if not conn:
        print("DEBUG: FALLO - No se pudo obtener conexión a la base de datos.")
        return None

    try:
        cursor = conn.cursor(dictionary=True)
        
        query = """
            SELECT u.id, u.nombre_usuario, u.password_hash, r.nombre AS nombre_rol
            FROM usuarios u
            JOIN roles r ON u.id_rol = r.id
            WHERE u.nombre_usuario = %s
        """
        
        cursor.execute(query, (nombre_usuario,))
        user_data = cursor.fetchone()
        
        print(f"DEBUG: Datos del usuario encontrados en la BD: {user_data}")
        
        if not user_data:
            print("DEBUG: FALLO - El usuario no fue encontrado (la consulta no devolvió filas).")
            return None
        
        print(f"DEBUG: Verificando contraseña...")
        print(f"DEBUG: HASH de la BD: {user_data['password_hash']}")
        
        resultado_verificacion = verificar_password(password, user_data['password_hash'])
        print(f"DEBUG: Resultado de verificar_password(): {resultado_verificacion}")
        
        if not resultado_verificacion:
            print("DEBUG: FALLO - La contraseña no coincide.")
            return None
        
        print("DEBUG: ÉXITO - Autenticación completada.")
        
        # ¡Autenticación exitosa!
        return {
            "id_usuario": user_data['id'],
            "nombre_usuario": user_data['nombre_usuario'],
            "nombre_rol": user_data['nombre_rol']
        }

    except Exception as e:
        print(f"DEBUG: FALLO - Ocurrió una excepción: {e}")
        return None
    finally:
        print("--- FIN DE AUTENTICACIÓN ---\n")
        if conn.is_connected():
            cursor.close()
            conn.close()


def _guardar_token_data(token_data):
    """Guarda los datos del token en un archivo local."""
    with open(config.ADMIN_TOKEN_LOCAL_FILE, 'w') as f:
        json.dump(token_data, f)

def generar_y_guardar_admin_token(forzar_nuevo=False):
    """
    Genera un nuevo token de administrador si el actual ha expirado o no existe,
    o si forzar_nuevo es True.
    Guarda el token y su tiempo de generación.
    Retorna el token.
    """
    token_data = _cargar_token_data()
    now_ts = time.time()

    if not forzar_nuevo and token_data and 'token' in token_data and 'generated_at' in token_data:
        generated_at_ts = token_data['generated_at']
        if now_ts < generated_at_ts + config.ADMIN_TOKEN_DURATION_SECONDS:
            print(f"Usando token de administrador existente: {token_data['token']} (válido hasta {datetime.fromtimestamp(generated_at_ts + config.ADMIN_TOKEN_DURATION_SECONDS).strftime('%Y-%m-%d %H:%M:%S')})")
            return token_data['token'] # Token actual sigue siendo válido

    # Generar nuevo token
    palabra = random.choice(config.ADMIN_TOKEN_KEYWORDS)
    numeros = str(random.randint(100, 999)).zfill(3)
    nuevo_token = f"{palabra}{numeros}"
    
    nuevo_token_data = {
        "token": nuevo_token,
        "generated_at": now_ts
    }
    _guardar_token_data(nuevo_token_data)
    print(f"Nuevo token de administrador generado: {nuevo_token} (válido por 8 horas)")
    # En un sistema real, este token debería ser comunicado de forma segura al administrador
    return nuevo_token

def verificar_admin_token(token_ingresado: str):
    """
    Verifica si el token ingresado es el token de administrador actual y válido.
    """
    token_data = _cargar_token_data()
    if not token_data or 'token' not in token_data or 'generated_at' not in token_data:
        print("No hay token de administrador configurado o datos corruptos. Generando uno nuevo.")
        generar_y_guardar_admin_token(forzar_nuevo=True) # Genera uno si no existe
        return False # El token ingresado no puede ser válido si no había uno antes

    generated_at_ts = token_data['generated_at']
    now_ts = time.time()

    if now_ts >= generated_at_ts + config.ADMIN_TOKEN_DURATION_SECONDS:
        print("El token de administrador ha expirado. Se necesita generar uno nuevo.")
        # Aquí, el administrador debería tener una forma de "solicitar" uno nuevo.
        # Por ahora, para el flujo, diremos que falló la verificación.
        # Podríamos regenerarlo aquí, pero el token_ingresado sería el viejo.
        # generar_y_guardar_admin_token(forzar_nuevo=True)
        return False

    if token_data['token'] == token_ingresado:
        return True
    else:
        print("Token de administrador incorrecto.")
        return False

def solicitar_y_verificar_admin_token():
    """Pide al usuario el token de admin y lo verifica."""
    token_ingresado = input("Ingrese el token de administrador: ")
    return verificar_admin_token(token_ingresado)

# ------ GESTIÓN DE USUARIO ACTUAL (en esta PC) ------
# Podríamos usar un archivo local para recordar quién fue el último usuario en esta PC
# Esto es para la comodidad de no tener que escribir el nombre cada vez.

def obtener_usuario_actual_local():
    """Obtiene el usuario guardado localmente para esta sesión de PC."""
    if os.path.exists(config.CURRENT_USER_FILE):
        try:
            with open(config.CURRENT_USER_FILE, 'r') as f:
                data = json.load(f)
                return data.get("current_user")
        except json.JSONDecodeError:
            return None
    return None

def guardar_usuario_actual_local(username: str):
    """Guarda el usuario para esta sesión de PC."""
    with open(config.CURRENT_USER_FILE, 'w') as f:
        json.dump({"current_user": username}, f)

# Nota: La validación de si el 'username' existe en el sistema (ej. en una hoja 'Usuarios')
# se haría en el main o en funciones que requieran un usuario logueado.