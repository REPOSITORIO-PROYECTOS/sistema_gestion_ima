import pytest
import requests

# Configuración de URLs basada en lo que hemos verificado
BASE_URL = "http://localhost:8000"
FRONT_URL = "http://localhost:3000"

def test_backend_root_accessible():
    """
    Verifica que el backend responde en la raíz.
    Valida que el servicio backend está levantado (UP).
    """
    print(f"\nProbando conexión al Backend en {BASE_URL}...")
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Sistema de Gestión IMA" in data["message"]
        print("✅ Backend Root: OK")
    except requests.exceptions.ConnectionError:
        pytest.fail("❌ No se pudo conectar al Backend en el puerto 8000. ¿Está corriendo?")

def test_backend_api_prefix_configured():
    """
    Verifica que el prefijo /api está configurado correctamente.
    Esto valida el cambio realizado en main.py.
    """
    print(f"Probando prefijo /api en {BASE_URL}/api/auth/llave-actual...")
    url = f"{BASE_URL}/api/auth/llave-actual"
    try:
        response = requests.get(url, timeout=5)
        # Si devuelve 404, significa que el prefijo /api NO está funcionando.
        assert response.status_code != 404, "❌ El endpoint devolvió 404. El prefijo /api no parece estar configurado."
        
        # Esperamos 200 OK porque este endpoint es público/verificado
        assert response.status_code == 200
        data = response.json()
        assert "llave_maestra" in data
        print("✅ Backend API Prefix (/api): OK")
    except requests.exceptions.ConnectionError:
        pytest.fail("❌ Error de conexión al probar el endpoint de API.")

def test_backend_db_connection_indirect():
    """
    Verifica indirectamente la conexión a la base de datos intentando un login.
    Si la DB falla, el servidor suele devolver 500.
    Si la DB está bien pero las credenciales son malas, devuelve 401.
    """
    print("Probando conexión lógica a DB a través de Login...")
    url = f"{BASE_URL}/api/auth/token"
    # Datos falsos para forzar validación
    payload = {"username": "usuario_test_inexistente", "password": "password_falso"}
    
    try:
        response = requests.post(url, data=payload, timeout=5)
        
        # 500 indica error de servidor (probablemente DB)
        assert response.status_code != 500, "❌ Error Interno del Servidor (500). Posible fallo de conexión a DB."
        
        # 401 indica que la app procesó la solicitud y rechazó las credenciales -> DB OK
        assert response.status_code == 401
        print("✅ Backend DB Connection: OK (Respondió 401 correctamente)")
    except requests.exceptions.ConnectionError:
        pytest.fail("❌ Error de conexión al probar login.")

def test_frontend_accessible():
    """
    Verifica que el frontend responde en el puerto 3000.
    """
    print(f"Probando conexión al Frontend en {FRONT_URL}...")
    try:
        response = requests.get(FRONT_URL, timeout=5)
        assert response.status_code == 200
        print("✅ Frontend Accessible: OK")
    except requests.exceptions.ConnectionError:
        pytest.fail("❌ No se pudo conectar al Frontend en el puerto 3000. ¿Está corriendo?")
