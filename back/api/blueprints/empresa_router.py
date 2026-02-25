# back/api/blueprints/empresa_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select
from typing import List

# --- Dependencias, Modelos y Managers ---
from back.database import get_db
from back.security import es_admin, obtener_usuario_actual
from back.modelos import Usuario, Empresa # Importamos los modelos necesarios

# Importamos ambos managers porque este router orquesta acciones en ambos
import back.gestion.empresa_manager as empresa_manager
import back.gestion.configuracion_manager as configuracion_manager 

# --- Schemas ---
from back.schemas.empresa_schemas import EmpresaCreate, EmpresaResponse, EmpresaListaResponse
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

@router.get("/admin/lista", response_model=List[EmpresaListaResponse])
def api_obtener_empresas(current_user: Usuario = Depends(obtener_usuario_actual), db: Session = Depends(get_db)):
    """
    Obtiene la lista de todas las empresas registradas (INFORMACIÓN PÚBLICA ÚNICAMENTE).
    
    ⚠️ SEGURIDAD: 
    - Solo usuarios Admin pueden acceder
    - Se devuelven SOLO campos públicos: id, nombre_legal, nombre_fantasia, cuit, activa
    - NO se exponen: nombres de usuario, IDs de usuario, URLs de Google Sheets, configuración privada
    """
    # Verificar que el usuario sea realmente admin
    if not current_user.rol or current_user.rol.nombre != "Admin":
        raise HTTPException(status_code=403, detail="Solo administradores pueden acceder a la lista de empresas")
    
    empresas_db = empresa_manager.obtener_todas_las_empresas(db)
    
    # Convertir directamente a lista de objetos seguros - Pydantic valida automáticamente
    return [EmpresaListaResponse.model_validate(emp) for emp in empresas_db]

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

@router.patch("/admin/{id_empresa}/nombre-legal", response_model=dict)
def api_actualizar_nombre_legal(
    id_empresa: int,
    data: dict,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    """
    Actualiza el nombre legal de una empresa.
    ⚠️ REQUIERE SER ADMIN
    
    Body JSON:
    {
      "nombre_legal": "NUEVO NOMBRE"
    }
    """
    try:
        # Verificar autenticación
        if not current_user.rol or current_user.rol.nombre != "Admin":
            raise HTTPException(status_code=403, detail="Solo administradores pueden actualizar empresas")
        
        # Obtener la empresa
        empresa = db.exec(select(Empresa).where(Empresa.id == id_empresa)).first()
        if not empresa:
            raise HTTPException(status_code=404, detail=f"Empresa con ID {id_empresa} no encontrada")
        
        # Validar que se envió el campo
        if "nombre_legal" not in data or not data["nombre_legal"]:
            raise HTTPException(status_code=400, detail="Falta el campo 'nombre_legal'")
        
        # Actualizar
        nombre_anterior = empresa.nombre_legal
        empresa.nombre_legal = data["nombre_legal"].strip()
        db.add(empresa)
        db.commit()
        db.refresh(empresa)
        
        return {
            "status": "success",
            "message": f"Nombre legal actualizado correctamente",
            "anterior": nombre_anterior,
            "nuevo": empresa.nombre_legal,
            "id_empresa": empresa.id
        }
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al actualizar empresa: {str(e)}")

