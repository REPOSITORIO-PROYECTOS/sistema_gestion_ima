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
    """
    def __init__(self, base_url: str, api_key: str):
        if not base_url.endswith('/'):
            base_url += '/'
        self.base_url = base_url
        self.headers = {
            "X-API-KEY": api_key,
            "Content-Type": "application/json"
        }
        self.session = requests.Session()
        self.session.headers.update(self.headers)

    def guardar_secreto(self, cuit: str, certificado: str, clave_privada: str) -> dict:
        """
        Guarda un nuevo secreto en la bóveda.
        Llama al endpoint: POST /secretos/{cuit}
        """
        url = f"{self.base_url}secretos/{cuit}"
        payload = SecretoPayload(certificado=certificado, clave_privada=clave_privada)
        
        try:
            response = self.session.post(url, data=payload.model_dump_json())
            # Lanza una excepción para errores HTTP (4xx o 5xx)
            response.raise_for_status() 
            return response.json()
        except requests.exceptions.HTTPError as e:
            # Errores específicos de la API de la bóveda
            if e.response.status_code == 409:
                raise ValueError(f"Conflicto: Ya existe un secreto para el CUIT {cuit}.")
            elif e.response.status_code == 403:
                raise PermissionError("Error de autenticación: La API Key es inválida.")
            # Otros errores del servidor
            raise ConnectionError(f"Error al conectar con la bóveda: {e}")
        except requests.exceptions.RequestException as e:
            raise ConnectionError(f"No se pudo conectar al servicio de bóveda en {self.base_url}. Error: {e}")



    def obtener_secreto(self, cuit: str) -> Optional[SecretoPayload]:
        """
        Obtiene un secreto descifrado de la bóveda.
        Llama al endpoint: GET /secretos/{cuit}
        """
        url = f"{self.base_url}secretos/{cuit}"
        
        try:
            response = self.session.get(url)
            response.raise_for_status()
            
            # Validamos que la respuesta coincida con nuestro modelo Pydantic
            secreto_data = response.json()
            return SecretoPayload(**secreto_data)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                # Es común que un secreto no exista, devolvemos None para que el código
                # que llama pueda manejarlo.
                return None
            elif e.response.status_code == 403:
                raise PermissionError("Error de autenticación: La API Key es inválida.")
            raise ConnectionError(f"Error al obtener secreto de la bóveda: {e}")
        except (requests.exceptions.RequestException, ValidationError) as e:
            raise ConnectionError(f"Error de conexión o datos inválidos desde la bóveda. Error: {e}")