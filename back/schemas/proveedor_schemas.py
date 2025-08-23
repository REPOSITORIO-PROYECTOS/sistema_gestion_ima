from pydantic import BaseModel, Field, computed_field
from typing import Optional, Dict, List

# === Schemas para las Plantillas de Mapeo (Sin cambios, pero necesarios para la relación) ===
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

# === Schemas para Tercero (Proveedor) (Sin cambios) ===
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

# --- INICIO DE LA SOLUCIÓN ---
# Este es el schema que "traduce" la estructura del modelo a la estructura que el frontend necesita.

class ProveedorReadConPlantilla(ProveedorRead):
    """
    Schema para leer un proveedor que inteligentemente extrae la plantilla única
    de la lista de plantillas que tiene el modelo.
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
        if self.plantillas_mapeo:  # Comprueba si la lista no está vacía
            return self.plantillas_mapeo[0]  # Devuelve el primer y único elemento
        return None  # Si la lista está vacía, devuelve null en el JSON

# --- FIN DE LA SOLUCIÓN ---

# === Schemas para la Asociación Artículo-Proveedor (Sin cambios) ===
class ArticuloProveedorLink(BaseModel):
    id_articulo: int
    codigo_articulo_proveedor: str

class ProveedorConArticulos(ProveedorRead):
    articulos_asociados: List[ArticuloProveedorLink] = []