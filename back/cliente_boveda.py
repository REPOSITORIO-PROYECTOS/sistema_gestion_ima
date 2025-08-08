# sistema_ima/cliente_boveda.py
import requests
from pydantic import BaseModel, ValidationError
from typing import Optional

# Este modelo debe ser idéntico al SecretoPayload de la bóveda
# para asegurar la consistencia de los datos.
class SecretoPayload(BaseModel):
    certificado: str
    clave_privada: str

class ClienteBoveda:
    """
    Cliente para interactuar con el microservicio de la Bóveda de Secretos.
    Ahora con lógica de "Upsert" (crear o actualizar).
    """
    def __init__(self, base_url: str, api_key: str):
        # Aseguramos que la URL base termine en '/'
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    # ====================================================================
    # ===       MÉTODO GUARDAR_SECRETO MODIFICADO CON LÓGICA DE UPSERT     ===
    # ====================================================================
    def guardar_secreto(self, cuit: str, certificado: str, clave_privada: str) -> dict:
        """
        Guarda o ACTUALIZA un secreto en la bóveda.
        Intenta crear el secreto (POST). Si falla porque ya existe (409 Conflict),
        automáticamente intenta actualizarlo con tu nuevo endpoint PUT.
        """
        # La URL para crear es /secretos/{cuit} según tu código anterior
        url_crear = f"{self.base_url}secretos/{cuit}"
        
        # El payload debe coincidir con el 'SecretoPayload' de la bóveda
        payload = SecretoPayload(certificado=certificado, clave_privada=clave_privada)
        
        try:
            print(f"[ClienteBoveda] Intentando crear (POST) secreto para CUIT: {cuit}")
            response = self.session.post(url_crear, data=payload.model_dump_json())
            
            # Si el POST tiene éxito, devolvemos la respuesta
            response.raise_for_status()
            print(f"[ClienteBoveda] Secreto para CUIT {cuit} creado correctamente.")
            return response.json()

        except requests.exceptions.HTTPError as e:
            # --- LÓGICA DE UPSERT ---
            # Si el error es 409 (Conflict), significa que el secreto ya existe.
            if e.response.status_code == 409:
                print(f"[ClienteBoveda] CUIT {cuit} ya existe. Intentando actualizar (PUT)...")
                
                # La URL para actualizar es la misma: /secretos/{cuit}
                url_actualizar = url_crear
                
                try:
                    # Hacemos la petición PUT con el mismo payload
                    response_put = self.session.put(url_actualizar, data=payload.model_dump_json())
                    response_put.raise_for_status() # Lanza excepción si el PUT falla
                    
                    print(f"[ClienteBoveda] Secreto para CUIT {cuit} actualizado correctamente.")
                    return response_put.json()
                
                except requests.exceptions.RequestException as put_error:
                    # Si incluso el PUT falla, lanzamos un error claro
                    raise ConnectionError(f"Falló la creación y también la actualización del secreto. Error PUT: {put_error}")
            
            elif e.response.status_code == 403:
                raise PermissionError("Error de autenticación: La API Key es inválida.")
            
            # Si el error POST fue otro (ej. 500), lo relanzamos
            raise ConnectionError(f"Error al conectar con la bóveda: {e}")

        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"No se pudo conectar al servicio de bóveda. Error: {e}")


    def obtener_secreto(self, cuit: str) -> Optional[SecretoPayload]:
        """
        (Sin cambios)
        Obtiene un secreto descifrado de la bóveda.
        Llama al endpoint: GET /secretos/{cuit}
        """
        url = f"{self.base_url}secretos/{cuit}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            secreto_data = response.json()
            return SecretoPayload(**secreto_data)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                return None
            elif e.response.status_code == 403:
                raise PermissionError("Error de autenticación: La API Key es inválida.")
            raise ConnectionError(f"Error al obtener secreto de la bóveda: {e}")
        except (requests.exceptions.RequestException, ValidationError) as e:
            raise ConnectionError(f"Error de conexión o datos inválidos desde la bóveda. Error: {e}")