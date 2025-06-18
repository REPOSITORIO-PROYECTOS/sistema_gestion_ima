# gestion/auth.py
import json
import os
import random
import time
from datetime import datetime, timedelta

from back.utils.sheets_google_handler import GoogleSheetsHandler
from back.config import (
    ADMIN_TOKEN_KEYWORDS,
    ADMIN_TOKEN_DURATION_SECONDS,
    SHEET_NAME_ADMIN_TOKEN,
    ADMIN_TOKEN_LOCAL_FILE # Opcional, si prefieres archivo local a Sheet
)

# ------ GESTIÓN DE TOKEN DE ADMINISTRADOR ------
# Usaremos un archivo local para el token, pero podría ser una hoja de cálculo también.

def _cargar_token_data():
    """Carga los datos del token desde un archivo local."""
    if os.path.exists(ADMIN_TOKEN_LOCAL_FILE):
        try:
            with open(ADMIN_TOKEN_LOCAL_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return None # Archivo corrupto
    return None

def _guardar_token_data(token_data):
    """Guarda los datos del token en un archivo local."""
    with open(ADMIN_TOKEN_LOCAL_FILE, 'w') as f:
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
        if now_ts < generated_at_ts + ADMIN_TOKEN_DURATION_SECONDS:
            print(f"Usando token de administrador existente: {token_data['token']} (válido hasta {datetime.fromtimestamp(generated_at_ts + ADMIN_TOKEN_DURATION_SECONDS).strftime('%Y-%m-%d %H:%M:%S')})")
            return token_data['token'] # Token actual sigue siendo válido

    # Generar nuevo token
    palabra = random.choice(ADMIN_TOKEN_KEYWORDS)
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

    if now_ts >= generated_at_ts + ADMIN_TOKEN_DURATION_SECONDS:
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