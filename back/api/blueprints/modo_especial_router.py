# back/api/blueprints/modo_especial_router.py

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import PlainTextResponse
from sqlmodel import Session

from back.database import get_db
from back.gestion import configuracion_manager, modo_especial_manager
from back.modelos import Usuario
from back.schemas.modo_especial_schemas import (
    BulkProductosRequest,
    CrearTransferenciaStockRequest,
    EmpresaTransferenciaResponse,
    ImportExportResumen,
    IngresoStockRequest,
    ProductoModoEspecialCreate,
    ProductoModoEspecialResponse,
    ProductoModoEspecialUpdate,
    RecibirTransferenciaRequest,
    SubaPreciosRequest,
    TransferenciaStockResponse,
)
from back.security import es_admin, es_gerente, obtener_usuario_actual

router = APIRouter(prefix="/modo-especial", tags=["Modo Especial"])


def _verificar_modo_especial(db: Session, id_empresa: int) -> None:
    if not configuracion_manager.es_modo_especial_habilitado(db, id_empresa):
        raise HTTPException(
            status_code=403,
            detail="Modo especial no habilitado para esta empresa.",
        )


def _http_desde_value_error(error: ValueError, *, not_found: bool = False) -> HTTPException:
    msg = str(error)
    lower = msg.lower()
    if "código de barras" in lower or "duplicad" in lower or "repetid" in lower:
        return HTTPException(status_code=409, detail=msg)
    if not_found:
        return HTTPException(status_code=404, detail=msg)
    return HTTPException(status_code=409, detail=msg)


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
        raise _http_desde_value_error(e) from e


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
        raise _http_desde_value_error(e, not_found=True) from e


@router.post("/ingreso-stock", dependencies=[Depends(es_gerente)])
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


@router.get("/empresas-transferencia", response_model=list[EmpresaTransferenciaResponse])
def api_empresas_transferencia(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.listar_empresas_transferencia(db, current_user.id_empresa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/transferencias-stock",
    response_model=TransferenciaStockResponse,
    dependencies=[Depends(es_gerente)],
)
def api_crear_transferencia(
    req: CrearTransferenciaStockRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.crear_transferencia_stock(
            db, current_user.id_empresa, current_user.id, req
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/transferencias-stock/pendientes", response_model=list[TransferenciaStockResponse])
def api_transferencias_pendientes(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.listar_transferencias_pendientes(db, current_user.id_empresa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get(
    "/transferencias-stock/enviadas",
    response_model=list[TransferenciaStockResponse],
    dependencies=[Depends(es_gerente)],
)
def api_transferencias_enviadas(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.listar_transferencias_enviadas(db, current_user.id_empresa)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.post(
    "/transferencias-stock/{id_transferencia}/recibir",
    response_model=TransferenciaStockResponse,
    dependencies=[Depends(es_gerente)],
)
def api_recibir_transferencia(
    id_transferencia: int,
    req: RecibirTransferenciaRequest,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db),
):
    _verificar_modo_especial(db, current_user.id_empresa)
    try:
        return modo_especial_manager.recibir_transferencia_stock(
            db, current_user.id_empresa, current_user.id, id_transferencia, req
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
