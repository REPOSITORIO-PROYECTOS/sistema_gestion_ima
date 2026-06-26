# back/api/blueprints/modo_especial_router.py

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from back.database import get_db
from back.gestion import configuracion_manager, modo_especial_manager
from back.modelos import Usuario
from back.schemas.modo_especial_schemas import (
    BulkProductosRequest,
    ImportExportResumen,
    IngresoStockRequest,
    ProductoModoEspecialCreate,
    ProductoModoEspecialResponse,
    ProductoModoEspecialUpdate,
    SubaPreciosRequest,
)
from back.security import es_admin, obtener_usuario_actual

router = APIRouter(prefix="/modo-especial", tags=["Modo Especial"])


def _verificar_modo_especial(db: Session, id_empresa: int) -> None:
    if not configuracion_manager.es_modo_especial_habilitado(db, id_empresa):
        raise HTTPException(
            status_code=403,
            detail="Modo especial no habilitado para esta empresa.",
        )


@router.get("/productos", response_model=list[ProductoModoEspecialResponse])
def api_listar_productos(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    return modo_especial_manager.listar_productos(db, current_user.id_empresa)


@router.post(
    "/productos",
    response_model=ProductoModoEspecialResponse,
    status_code=201,
    dependencies=[Depends(es_admin)],
)
def api_crear_producto(
    req: ProductoModoEspecialCreate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.crear_producto(db, current_user.id_empresa, req)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put(
    "/productos/bulk",
    response_model=ImportExportResumen,
    dependencies=[Depends(es_admin)],
)
def api_bulk_productos(
    req: BulkProductosRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    return modo_especial_manager.bulk_upsert(db, current_user.id_empresa, req)


@router.put(
    "/productos/{codigo_interno}",
    response_model=ProductoModoEspecialResponse,
    dependencies=[Depends(es_admin)],
)
def api_actualizar_producto(
    codigo_interno: str,
    req: ProductoModoEspecialUpdate,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.actualizar_producto(db, current_user.id_empresa, codigo_interno, req)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/ingreso-stock", dependencies=[Depends(es_admin)])
def api_ingreso_stock(
    req: IngresoStockRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.ingresar_stock(
            db, current_user.id_empresa, current_user.id, req
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/suba-precios", dependencies=[Depends(es_admin)])
def api_suba_precios(
    req: SubaPreciosRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.subir_precios(db, current_user.id_empresa, req)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/exportar", response_class=PlainTextResponse)
def api_exportar(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    contenido = modo_especial_manager.exportar_csv(db, current_user.id_empresa)
    return PlainTextResponse(
        content=contenido,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="productos_modo_especial.csv"'},
    )


@router.post("/importar", response_model=ImportExportResumen, dependencies=[Depends(es_admin)])
async def api_importar(
    archivo: UploadFile = File(...),
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    raw = await archivo.read()
    try:
        contenido = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        contenido = raw.decode("latin-1")
    return modo_especial_manager.importar_csv(db, current_user.id_empresa, contenido)
