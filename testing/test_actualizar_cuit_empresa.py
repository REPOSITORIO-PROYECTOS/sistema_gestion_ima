"""CUIT del formulario debe persistir en empresas y configuracion_empresa."""
from __future__ import annotations

import os
import sys
from datetime import datetime, timezone

from sqlalchemy.pool import StaticPool
from sqlmodel import Session, SQLModel, create_engine

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from back.gestion.configuracion_manager import actualizar_configuracion_parcial
from back.modelos import ConfiguracionEmpresa, Empresa
from back.schemas.configuracion_schemas import ConfiguracionUpdate


CUIT_VIEJO = "20364237740"
CUIT_NUEVO = "30718863380"


def _engine_memoria():
    return create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )


def test_patch_cuit_sincroniza_empresa_y_config():
    engine = _engine_memoria()
    SQLModel.metadata.create_all(engine)
    with Session(engine) as db:
        empresa = Empresa(
            nombre_legal="Swing Jugos SA",
            nombre_fantasia="Swing",
            cuit=CUIT_VIEJO,
            activa=True,
            creada_en=datetime.now(timezone.utc),
        )
        db.add(empresa)
        db.commit()
        db.refresh(empresa)

        config = ConfiguracionEmpresa(
            id_empresa=empresa.id,
            cuit=CUIT_VIEJO,
            nombre_negocio="Swing",
        )
        db.add(config)
        db.commit()

        actualizar_configuracion_parcial(
            db,
            empresa.id,
            ConfiguracionUpdate(cuit=CUIT_NUEVO),
        )

        empresa_db = db.get(Empresa, empresa.id)
        config_db = db.get(ConfiguracionEmpresa, empresa.id)
        assert empresa_db is not None and config_db is not None
        assert empresa_db.cuit == CUIT_NUEVO
        assert config_db.cuit == CUIT_NUEVO


def test_schema_acepta_cuit_string_empresa():
    data = ConfiguracionUpdate(cuit=CUIT_NUEVO)
    assert data.cuit == CUIT_NUEVO


if __name__ == "__main__":
    test_patch_cuit_sincroniza_empresa_y_config()
    print("OK: test_patch_cuit_sincroniza_empresa_y_config")
    test_schema_acepta_cuit_string_empresa()
    print("OK: test_schema_acepta_cuit_string_empresa")
