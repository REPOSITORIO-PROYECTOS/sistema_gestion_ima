"""Ingreso masivo a otra sucursal: envío pendiente, sin stock negativo ni espejo cruzado."""

from pathlib import Path

import pytest
from sqlmodel import Session, select

from back.database import engine
from back.gestion.modo_especial_manager import neto_reparto, recibir_transferencia_stock, registrar_ingreso_masivo
from back.gestion.stock.espejo_stock import ids_destino_visibles
from back.modelos import (
    Articulo,
    ConfiguracionEmpresa,
    Empresa,
    StockMovimiento,
    TransferenciaStock,
    TransferenciaStockDetalle,
    Usuario,
)
from back.schemas.modo_especial_schemas import IngresoStockItem, IngresoStockRequest, RecibirTransferenciaItem, RecibirTransferenciaRequest


def test_excluye_el_par_espejo_sin_hardcodear_el_selector():
    assert ids_destino_visibles(37, [37, 38]) == []
    assert ids_destino_visibles(38, [37, 38, 39]) == [39]
    assert ids_destino_visibles(35, [35, 36]) == [36]
    assert 38 not in ids_destino_visibles(37, [37, 38, 36])


def test_reparto_10_queda_6_y_rechaza_enviar_de_mas():
    assert neto_reparto(10, 4) == (6.0, 4.0)
    assert neto_reparto(10, 0) == (10.0, 0.0)
    assert neto_reparto(10, None) == (10.0, 0.0)
    assert neto_reparto(10, 10) == (0.0, 10.0)
    with pytest.raises(ValueError, match="solo ingresan"):
        neto_reparto(10, 11)
    with pytest.raises(ValueError):
        IngresoStockItem(codigo_interno="A", cantidad=10, cantidad_enviar=11)


def test_el_manager_no_toca_ventas_pendientes():
    src = (Path(__file__).resolve().parents[1] / "back/gestion/modo_especial_manager.py").read_text(encoding="utf-8")
    assert "ventas_pendientes" not in src
    assert "clearOfflineEmpresa" not in src


def _db_lista():
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
    except Exception as exc:
        pytest.skip(f"sin base local: {exc}")


def test_destino_propio_suma_y_envio_queda_pendiente_hasta_la_recepcion():
    _db_lista()
    codigo = "LOC-DEST-TEST"
    with Session(engine) as db:
        usuario = db.exec(select(Usuario).where(Usuario.nombre_usuario == "admin_local")).first()
        origen = db.exec(select(Empresa).where(Empresa.cuit == "20999999999")).first()
        if usuario is None or origen is None:
            pytest.skip("semilla local ausente")
        config_origen = db.get(ConfiguracionEmpresa, origen.id)
        perfil_original = dict(config_origen.perfil_operativo or {})
        version_original = config_origen.catalogo_version

        destino = db.exec(select(Empresa).where(Empresa.cuit == "20999999998")).first()
        if destino is None:
            destino = Empresa(
                nombre_legal="Sucursal Pytest Destino SRL",
                nombre_fantasia="Sucursal Pytest",
                cuit="20999999998",
                activa=True,
            )
            db.add(destino)
            db.flush()
            perfil_dest = dict(perfil_original)
            perfil_dest["empresas_transferencia_ids"] = [origen.id, destino.id]
            perfil_dest["modo_especial"] = True
            db.add(ConfiguracionEmpresa(
                id_empresa=destino.id,
                cuit=destino.cuit,
                nombre_negocio="Sucursal Pytest",
                modo_especial_habilitado=True,
                tipo_esquema_empresa="especial",
                perfil_operativo=perfil_dest,
            ))
            db.commit()
            db.refresh(destino)

        perfil_grupo = dict(perfil_original)
        perfil_grupo["empresas_transferencia_ids"] = [origen.id, destino.id]
        perfil_grupo["modo_especial"] = True
        config_origen.perfil_operativo = perfil_grupo
        config_dest = db.get(ConfiguracionEmpresa, destino.id)
        config_dest.perfil_operativo = dict(perfil_grupo)
        config_dest.modo_especial_habilitado = True
        db.add(config_origen)
        db.add(config_dest)
        db.commit()

        art_origen = Articulo(
            codigo_interno=codigo,
            descripcion="Producto pytest destino",
            precio_venta=1000,
            venta_negocio=1000,
            stock_actual=10,
            id_empresa=origen.id,
            activo=True,
        )
        art_destino = Articulo(
            codigo_interno=codigo,
            descripcion="Producto pytest destino",
            precio_venta=1000,
            venta_negocio=1000,
            stock_actual=4,
            id_empresa=destino.id,
            activo=True,
        )
        db.add(art_origen)
        db.add(art_destino)
        db.commit()
        db.refresh(art_origen)
        db.refresh(art_destino)

        transferencia_id = None
        transferencia_total_id = None
        transferencia_faltante_id = None
        art_faltante = None
        try:
            local = registrar_ingreso_masivo(
                db,
                origen.id,
                usuario.id,
                IngresoStockRequest(
                    items=[IngresoStockItem(codigo_interno=codigo, cantidad=2, cantidad_enviar=0)],
                    id_empresa_destino=destino.id,
                ),
            )
            db.refresh(art_origen)
            assert local["total"] == 1
            assert local.get("pendiente_recepcion") is not True
            assert art_origen.stock_actual == 12

            enviado = registrar_ingreso_masivo(
                db,
                origen.id,
                usuario.id,
                IngresoStockRequest(
                    items=[IngresoStockItem(codigo_interno=codigo, cantidad=10, cantidad_enviar=4)],
                    id_empresa_destino=destino.id,
                    observacion="pytest reparto",
                ),
            )
            db.refresh(art_origen)
            db.refresh(art_destino)
            assert enviado["pendiente_recepcion"] is True
            assert enviado["transferencia"]["estado"] == "PENDIENTE"
            assert enviado["transferencia"]["detalles"][0]["cantidad"] == 4
            assert art_origen.stock_actual == 18
            assert art_destino.stock_actual == 4
            transferencia_id = enviado["transferencia"]["id"]
            detalle_id = enviado["transferencia"]["detalles"][0]["id"]

            recibida = recibir_transferencia_stock(
                db,
                destino.id,
                usuario.id,
                transferencia_id,
                RecibirTransferenciaRequest(
                    aplicar_precios=False,
                    items=[RecibirTransferenciaItem(id_detalle=detalle_id, cantidad_recibida=4)],
                ),
            )
            db.refresh(art_destino)
            assert recibida["estado"] == "RECIBIDA"
            assert art_destino.stock_actual == 8

            total = registrar_ingreso_masivo(
                db,
                origen.id,
                usuario.id,
                IngresoStockRequest(
                    items=[IngresoStockItem(codigo_interno=codigo, cantidad=5, cantidad_enviar=5)],
                    id_empresa_destino=destino.id,
                ),
            )
            db.refresh(art_origen)
            assert art_origen.stock_actual == 18
            assert total["transferencia"]["detalles"][0]["cantidad"] == 5
            transferencia_total_id = total["transferencia"]["id"]
            detalle_total = total["transferencia"]["detalles"][0]["id"]
            recibir_transferencia_stock(
                db,
                destino.id,
                usuario.id,
                transferencia_total_id,
                RecibirTransferenciaRequest(
                    aplicar_precios=False,
                    items=[RecibirTransferenciaItem(id_detalle=detalle_total, cantidad_recibida=5)],
                ),
            )
            db.refresh(art_destino)
            assert art_destino.stock_actual == 13

            with pytest.raises(ValueError, match="solo ingresan"):
                registrar_ingreso_masivo(
                    db,
                    origen.id,
                    usuario.id,
                    IngresoStockRequest(
                        items=[IngresoStockItem(codigo_interno=codigo, cantidad=3, cantidad_enviar=4)],
                        id_empresa_destino=destino.id,
                    ),
                )
            db.rollback()
            db.refresh(art_origen)
            assert art_origen.stock_actual == 18

            art_faltante = Articulo(
                codigo_interno="LOC-DEST-FALTA",
                descripcion="Solo en origen",
                precio_venta=500,
                venta_negocio=500,
                stock_actual=5,
                id_empresa=origen.id,
                activo=True,
            )
            db.add(art_faltante)
            db.commit()
            db.refresh(art_faltante)
            aviso = registrar_ingreso_masivo(
                db,
                origen.id,
                usuario.id,
                IngresoStockRequest(
                    items=[IngresoStockItem(codigo_interno="LOC-DEST-FALTA", cantidad=1, cantidad_enviar=1)],
                    id_empresa_destino=destino.id,
                ),
            )
            db.refresh(art_faltante)
            assert aviso["codigos_sin_producto_en_destino"] == ["LOC-DEST-FALTA"]
            assert art_faltante.stock_actual == 5
            transferencia_faltante_id = aviso["transferencia"]["id"]
        finally:
            db.rollback()
            for tid in (transferencia_id, transferencia_total_id, transferencia_faltante_id):
                if tid is None:
                    continue
                for detalle in db.exec(
                    select(TransferenciaStockDetalle).where(TransferenciaStockDetalle.id_transferencia == tid)
                ).all():
                    db.delete(detalle)
                transferencia = db.get(TransferenciaStock, tid)
                if transferencia is not None:
                    db.delete(transferencia)
            for articulo in (art_origen, art_destino, art_faltante):
                if articulo is None or articulo.id is None:
                    continue
                vigente = db.get(Articulo, articulo.id)
                if vigente is None:
                    continue
                for mov in db.exec(
                    select(StockMovimiento).where(StockMovimiento.id_articulo == vigente.id)
                ).all():
                    db.delete(mov)
                db.delete(vigente)
            config_vigente = db.get(ConfiguracionEmpresa, origen.id)
            config_vigente.perfil_operativo = perfil_original
            config_vigente.catalogo_version = version_original
            db.add(config_vigente)
            db.commit()
