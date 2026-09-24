# testing/test_cajas_abiertas_grupo.py
"""Panel/arqueos deben incluir cajas ABIERTA del grupo de transferencia."""
from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from back.gestion.caja import consultas_caja


def test_ids_empresas_grupo_incluye_hermanas():
    db = MagicMock()
    perfil = SimpleNamespace(empresas_transferencia_ids=[35, 36])
    with patch(
        "back.gestion.perfil_operativo_manager.obtener_perfil_resuelto",
        return_value=perfil,
    ):
        assert consultas_caja._ids_empresas_para_estadisticas(db, 35) == [35, 36]
        assert consultas_caja._ids_empresas_para_estadisticas(db, 36) == [35, 36]


def test_ids_empresas_sin_grupo_solo_propia():
    db = MagicMock()
    perfil = SimpleNamespace(empresas_transferencia_ids=[])
    with patch(
        "back.gestion.perfil_operativo_manager.obtener_perfil_resuelto",
        return_value=perfil,
    ):
        assert consultas_caja._ids_empresas_para_estadisticas(db, 10) == [10]


def test_ids_empresas_fuera_del_grupo_no_expande():
    db = MagicMock()
    perfil = SimpleNamespace(empresas_transferencia_ids=[35, 36])
    with patch(
        "back.gestion.perfil_operativo_manager.obtener_perfil_resuelto",
        return_value=perfil,
    ):
        # Usuario de otra empresa no debe ver el grupo por accidente
        assert consultas_caja._ids_empresas_para_estadisticas(db, 99) == [99]
