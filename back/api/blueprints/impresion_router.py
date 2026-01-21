from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session
from starlette.responses import Response
from back.database import get_db
from back.security import obtener_usuario_actual
from back.modelos import Usuario
from back.gestion.impresion_manager import abrir_sesion_impresion, cerrar_sesion_impresion, obtener_sesion_abierta
from back.gestion.reportes.adapters_mesas import construir_request_comanda, construir_request_ticket_mesa
from back.gestion.reportes.generador_comprobantes import generar_comprobante_stateless
from back.modelos import ConsumoMesa, ConsumoMesaDetalle
from sqlmodel import select

router = APIRouter(prefix="/impresion", tags=["Impresion"])

@router.get("/estado")
def api_estado_impresion(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    sesion = obtener_sesion_abierta(db, current_user.id_empresa)
    return {"estado": "ABIERTA" if sesion else "CERRADA", "sesion_id": sesion.id if sesion else None}

@router.post("/sesion/abrir")
def api_abrir_sesion_impresion(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    sesion = abrir_sesion_impresion(db, current_user)
    return {"mensaje": "Sesion de impresion abierta", "sesion_id": sesion.id}

@router.post("/sesion/cerrar")
def api_cerrar_sesion_impresion(
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    sesion = cerrar_sesion_impresion(db, current_user)
    if not sesion:
        raise HTTPException(status_code=404, detail="No hay sesion de impresion abierta")
    return {"mensaje": "Sesion de impresion cerrada", "sesion_id": sesion.id}

@router.post("/comanda/pdf")
def api_generar_comanda_pdf(
    ids_detalles: list[int],
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if not obtener_sesion_abierta(db, current_user.id_empresa):
        raise HTTPException(status_code=403, detail="Debe abrir la sesión de impresión")
    stmt = select(ConsumoMesaDetalle).join(ConsumoMesa).where(
        ConsumoMesaDetalle.id.in_(ids_detalles),
        ConsumoMesa.id_empresa == current_user.id_empresa
    )
    detalles = db.exec(stmt).all()
    req = construir_request_comanda(db, detalles, current_user.id_empresa)
    pdf = generar_comprobante_stateless(req)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="comanda.pdf"'})

@router.post("/mesa/pdf")
def api_generar_mesa_pdf(
    id_consumo_mesa: int,
    current_user: Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    if not obtener_sesion_abierta(db, current_user.id_empresa):
        raise HTTPException(status_code=403, detail="Debe abrir la sesión de impresión")
    consumo = db.exec(select(ConsumoMesa).where(ConsumoMesa.id == id_consumo_mesa, ConsumoMesa.id_empresa == current_user.id_empresa)).first()
    if not consumo:
        raise HTTPException(status_code=404, detail="Consumo no encontrado")
    req = construir_request_ticket_mesa(db, consumo)
    pdf = generar_comprobante_stateless(req)
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": 'inline; filename="ticket_mesa.pdf"'})
