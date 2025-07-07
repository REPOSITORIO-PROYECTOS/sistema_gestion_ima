# back/gestion/fiscal/providers/base.py

from abc import ABC, abstractmethod

class FiscalProvider(ABC):
    """
    Define la interfaz (el contrato) que todos los proveedores fiscales deben cumplir.
    Nuestro sistema solo hablará con esta interfaz, no directamente con los proveedores.
    """
    
    @abstractmethod
    def __init__(self, api_key: str):
        """Cada proveedor necesitará una clave de API para inicializarse."""
        self.api_key = api_key
        self.base_url = ""

    @abstractmethod
    def generar_comprobante(self, datos_factura: dict) -> dict:
        """
        El método principal para generar una factura.
        
        Args:
            datos_factura (dict): Un diccionario con un formato ESTÁNDAR definido por nosotros.
        
        Returns:
            dict: Un diccionario con una respuesta ESTÁNDAR, ej:
                  {"status": "APROBADO", "cae": "...", "numero_comprobante": "...", "error": None}
        """
        pass

    @abstractmethod
    def _mapear_a_formato_proveedor(self, datos_factura: dict) -> dict:
        """
        Método privado para traducir nuestros datos estándar al formato específico del proveedor.
        """
        pass

    @abstractmethod
    def _mapear_de_formato_proveedor(self, respuesta_proveedor: dict) -> dict:
        """
        Método privado para traducir la respuesta del proveedor a nuestro formato estándar.
        """
        pass