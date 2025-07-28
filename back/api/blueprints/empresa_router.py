# back/api/blueprints/empresa_router.py

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from typing import List

from back.database import get_db
from back.security import es_admin # Asumimos que solo un admin puede crear empresas
import back.gestion.empresa_manager as empresa_manager
from back.schemas.empresa_schemas import EmpresaCreate, EmpresaResponse

router = APIRouter(
    prefix="/empresas",
    tags=["Gestión de Empresas (Multi-Tenant)"],
    dependencies=[Depends(es_admin)] # ¡Protegido!
)

@router.post("/admin/crear", response_model=EmpresaResponse, status_code=201)
def api_crear_empresa(req: EmpresaCreate, db: Session = Depends(get_db)):
    """Crea una nueva empresa cliente en el sistema."""
    try:
        nueva_empresa = empresa_manager.crear_empresa(db, req)
        return nueva_empresa
    except ValueError as e:
        # Errores de negocio (ej: CUIT duplicado)
        raise HTTPException(status_code=409, detail=str(e))
    except RuntimeError as e:
        # Errores de base de datos
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/admin/lista", response_model=List[EmpresaResponse])
def api_obtener_empresas(db: Session = Depends(get_db)):
    """Obtiene una lista de todas las empresas registradas."""
    return empresa_manager.obtener_todas_las_empresas(db)