# back/gestion/seguridad/llave_maestra_manager.py
import datetime
from back.utils.generador_llaves import generar_nueva_llave

# --- ALMACÉN EN MEMORIA (Singleton) ---
# Esta es una forma simple de tener una variable global controlada dentro de un módulo.
class AlmacenLlave:
    def __init__(self):
        self.llave_actual = None
        self.fecha_expiracion = None
        self._generar_si_es_necesario()

    def _generar_si_es_necesario(self):
        """Genera una nueva llave si no hay ninguna o si la actual ha expirado."""
        ahora = datetime.datetime.utcnow()
        if not self.llave_actual or ahora >= self.fecha_expiracion:
            self.llave_actual = generar_nueva_llave()
            # La nueva llave será válida por 24 horas
            self.fecha_expiracion = ahora + datetime.timedelta(hours=24)
            print(f"🔑 NUEVA LLAVE MAESTRA GENERADA: '{self.llave_actual}' (Válida hasta {self.fecha_expiracion.isoformat()}Z)")

    def obtener_llave_actual(self) -> str:
        """Devuelve la llave actual, regenerándola si ha expirado."""
        self._generar_si_es_necesario()
        return self.llave_actual

    def validar_llave(self, llave_proporcionada: str) -> bool:
        """Compara una llave proporcionada con la llave maestra actual."""
        llave_actual = self.obtener_llave_actual()
        return llave_proporcionada.lower().strip() == llave_actual.lower().strip()

# Creamos una única instancia que será usada por toda la aplicación
almacen_llave_maestra = AlmacenLlave()

# --- Funciones públicas que usará la API ---
def validar_llave_maestra(llave_proporcionada: str) -> bool:
    return almacen_llave_maestra.validar_llave(llave_proporcionada)

def obtener_llave_actual_para_admin() -> dict:
    """Función segura para que un admin pueda consultar la llave actual."""
    return {
        "llave_maestra": almacen_llave_maestra.obtener_llave_actual(),
        "expira_en": almacen_llave_maestra.fecha_expiracion.isoformat() + "Z"
    }