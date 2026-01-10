# back/api/blueprints/empresa_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

# --- Dependencias, Modelos y Managers ---
from back.database import get_db
from back.security import es_admin
from back.modelos import Usuario, Empresa # Importamos los modelos necesarios

# Importamos ambos managers porque este router orquesta acciones en ambos
import back.gestion.empresa_manager as empresa_manager
import back.gestion.configuracion_manager as configuracion_manager 

# --- Schemas ---
from back.schemas.empresa_schemas import EmpresaCreate, EmpresaResponse
# Renombramos la importación para que el código sea más claro y evitar conflictos
from back.schemas.configuracion_schemas import ConfiguracionResponse as SchemaConfigResponse, ConfiguracionUpdate

router = APIRouter(
    prefix="/empresas",
    tags=["Gestión de Empresas (Super Admin)"], # Tag actualizado para más claridad
    dependencies=[Depends(es_admin)]
)

@router.post("/admin/crear", response_model=EmpresaResponse, status_code=201)
def api_crear_empresa(req: EmpresaCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva empresa y su primer administrador de forma atómica.
    """
    try:
        nueva_empresa = empresa_manager.crear_empresa_y_primer_admin(db, req)

        # Construimos la respuesta final a medida, tal como la define el schema EmpresaResponse
        respuesta_final = EmpresaResponse(
            id=nueva_empresa.id,
            nombre_legal=nueva_empresa.nombre_legal,
            nombre_fantasia=nueva_empresa.nombre_fantasia,
            cuit=nueva_empresa.cuit,
            activa=nueva_empresa.activa,
            link_google_sheets=nueva_empresa.configuracion.link_google_sheets if nueva_empresa.configuracion else None,
            admin_username=req.admin_username 
        )
        return respuesta_final

    except (ValueError, RuntimeError) as e:
        if "ya está registrado" in str(e) or "ya está en uso" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

@router.get("/admin/lista", response_model=List[EmpresaResponse])
def api_obtener_empresas(db: Session = Depends(get_db)):
    """Obtiene la lista de todas las empresas registradas."""
    empresas_db = empresa_manager.obtener_todas_las_empresas(db)
    
    respuesta = []
    for emp in empresas_db:
        # Buscamos el primer usuario admin preferentemente con rol "Admin", si no existe usamos "Gerente"
        primer_admin = db.exec(
            select(Usuario).where(Usuario.id_empresa == emp.id, Usuario.rol.has(nombre="Admin"))
        ).first()
        if not primer_admin:
            primer_admin = db.exec(
                select(Usuario).where(Usuario.id_empresa == emp.id, Usuario.rol.has(nombre="Gerente"))
            ).first()

        respuesta.append(EmpresaResponse(
            id=emp.id,
            nombre_legal=emp.nombre_legal,
            nombre_fantasia=emp.nombre_fantasia,
            cuit=emp.cuit,
            activa=emp.activa,
            link_google_sheets=emp.configuracion.link_google_sheets if emp.configuracion else None,
            admin_username=primer_admin.nombre_usuario if primer_admin else "N/A",
            admin_user_id=primer_admin.id if primer_admin else None
        ))
    return respuesta

# =================================================================================
# === ENDPOINTS CORREGIDOS Y AÑADIDOS PARA EL FORMULARIO DE CONFIGURACIÓN ===
# =================================================================================

@router.get("/admin/{id_empresa}/configuracion", response_model=SchemaConfigResponse)
def api_obtener_configuracion_de_empresa(
    id_empresa: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene la configuración completa de una empresa específica por su ID.
    Este endpoint es el que soluciona el problema de los campos vacíos en el formulario.
    """
    try:
        # La lógica de negocio ya está en el manager, solo la llamamos.
        # El manager es lo suficientemente inteligente para crear una config si no existe.
        config = configuracion_manager.obtener_configuracion_empresa(db, id_empresa)
        
        # FastAPI se encarga de convertir el objeto 'config' en un JSON que coincide
        # con el 'response_model=SchemaConfigResponse', ya que los nombres de campo coinciden.
        return config
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.patch("/admin/{id_empresa}/configuracion", response_model=SchemaConfigResponse)
def api_actualizar_configuracion_de_empresa(
    id_empresa: int,
    data: ConfiguracionUpdate,
    db: Session = Depends(get_db)
):
    """
    Actualiza parcialmente la configuración de una empresa específica.
    """
    try:
        config_actualizada = configuracion_manager.actualizar_configuracion_parcial(
            db=db,
            id_empresa=id_empresa,
            data=data
        )
        return config_actualizada
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
