# back/api/blueprints/empresa_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from back.database import get_db
from back.security import es_admin
import back.gestion.empresa_manager as empresa_manager
from back.schemas.empresa_schemas import EmpresaCreate, EmpresaResponse

router = APIRouter(
    prefix="/empresas",
    tags=["Gestión de Empresas"],
    dependencies=[Depends(es_admin)]
)

@router.post("/admin/crear", response_model=EmpresaResponse, status_code=201)
def api_crear_empresa(req: EmpresaCreate, db: Session = Depends(get_db)):
    """
    Crea una nueva empresa y su primer administrador. Devuelve una respuesta
    unificada con los datos creados.
    """
    try:
        # 1. El manager hace todo el trabajo de base de datos de forma atómica
        nueva_empresa = empresa_manager.crear_empresa_y_primer_admin(db, req)

        # 2. Construimos la respuesta final a medida, tal como la define el schema EmpresaResponse
        #    Esto es necesario porque la respuesta contiene datos de diferentes fuentes.
        respuesta_final = EmpresaResponse(
            id=nueva_empresa.id,
            nombre_legal=nueva_empresa.nombre_legal,
            nombre_fantasia=nueva_empresa.nombre_fantasia,
            cuit=nueva_empresa.cuit,
            activa=nueva_empresa.activa,
            # Accedemos al dato de configuración a través de la relación
            link_google_sheets=nueva_empresa.configuracion.link_google_sheets,
            # Tomamos el nombre de usuario de la petición original
            admin_username=req.admin_username 
        )
        return respuesta_final

    except (ValueError, RuntimeError) as e:
        # Manejo de errores de negocio y de base de datos
        if "ya está registrado" in str(e) or "ya está en uso" in str(e):
            raise HTTPException(status_code=409, detail=str(e))
        else:
            raise HTTPException(status_code=500, detail=f"Error interno del servidor: {e}")

@router.get("/admin/lista", response_model=List[EmpresaResponse])
def api_obtener_empresas(db: Session = Depends(get_db)):
    """Obtiene la lista de todas las empresas registradas."""

    empresas_db = empresa_manager.obtener_todas_las_empresas(db)
    
    # Adaptamos la respuesta para que coincida con el schema (simplificado para la lista)
    respuesta = []
    for emp in empresas_db:
        respuesta.append(EmpresaResponse(
            id=emp.id,
            nombre_legal=emp.nombre_legal,
            cuit=emp.cuit,
            activa=emp.activa,
            # Para la lista, podemos omitir campos detallados o poner placeholders
            link_google_sheets=emp.configuracion.link_google_sheets if emp.configuracion else None,
            admin_username="" # Este campo no tiene sentido en una lista de empresas
        ))
    return respuesta