# Archivo: /back/schemas/proveedor_schemas.py

from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict, List

# === Schemas para las Plantillas de Mapeo ===
class PlantillaMapeoBase(BaseModel):
    nombre_plantilla: str
    mapeo_columnas: Dict[str, str] = Field(
        ..., 
        example={"CODIGO_PROV": "codigo_articulo_proveedor", "PRECIO_COSTO": "precio_costo"}
    )
    nombre_hoja_excel: Optional[str] = None
    fila_inicio: int = 2

class PlantillaMapeoCreate(PlantillaMapeoBase):
    id_proveedor: int

class PlantillaMapeoRead(PlantillaMapeoBase):
    id: int
    id_proveedor: int
    
    class Config:
        from_attributes = True

# === Schemas para Tercero (Proveedor) ===
class ProveedorBase(BaseModel):
    nombre_razon_social: str
    nombre_fantasia: Optional[str] = None
    cuit: Optional[str] = None
    condicion_iva: str
    email: Optional[str] = None
    telefono: Optional[str] = None
    direccion: Optional[str] = None
    notas: Optional[str] = None

class ProveedorCreate(ProveedorBase):
    pass

class ProveedorRead(ProveedorBase):
    id: int
    activo: bool
    class Config:
        from_attributes = True

# --- INICIO DE LA SOLUCIÓN CLAVE ---
# Este es el schema que "traduce" la estructura del modelo a la que el frontend necesita.

class ProveedorReadConPlantilla(ProveedorRead):
    """
    Schema para leer un proveedor que inteligentemente extrae la plantilla única
    de la lista de plantillas que tiene el modelo, sin crashear si no existe.
    """
    
    # Usamos @computed_field para crear un campo en el JSON de salida que no existe
    # directamente con este nombre y tipo en el modelo.
    @computed_field
    @property
    def plantilla_mapeo(self) -> Optional[PlantillaMapeoRead]:
        """
        El modelo 'Tercero' tiene 'plantillas_mapeo' (una lista).
        Esta función toma el primer elemento de esa lista (si existe) y lo devuelve.
        Si la lista está vacía, devuelve None.
        Esto soluciona el mismatch entre el modelo (uno-a-muchos) y la lógica de negocio (uno-a-uno).
        """
        # 'self' aquí es la instancia del modelo 'Tercero' que FastAPI está procesando.
        # hasattr() comprueba si el objeto tiene el atributo 'plantillas_mapeo' para evitar errores.
        if hasattr(self, 'plantillas_mapeo') and self.plantillas_mapeo:
            return self.plantillas_mapeo[0]  # Devuelve el primer elemento
        return None  # Si no hay plantillas, devuelve null en el JSON

# --- FIN DE LA SOLUCIÓN CLAVE ---

# === Schemas para la Asociación Artículo-Proveedor ===
class ArticuloProveedorLink(BaseModel):
    id_articulo: int
    codigo_articulo_proveedor: str

class ProveedorConArticulos(ProveedorRead):
    articulos_asociados: List[ArticuloProveedorLink] = []