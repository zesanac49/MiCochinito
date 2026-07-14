"""Reglas de dominio de acceso (RF-1002): participante↔rol y último admin."""

from __future__ import annotations

import pytest

from app.shared.domain.acceso import (
    ClienteRequiereParticipante,
    UltimoAdministrador,
    normalizar_participante,
    validar_rol,
    verificar_no_ultimo_admin,
)
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio


def test_cliente_sin_participante_falla() -> None:
    with pytest.raises(ClienteRequiereParticipante):
        normalizar_participante("CLIENTE", None)


def test_cliente_con_participante_se_conserva() -> None:
    assert normalizar_participante("CLIENTE", 7) == 7


def test_roles_no_cliente_descartan_participante() -> None:
    # Un ADMINISTRADOR/SUPERVISOR no lleva participante vinculado aunque se pase.
    assert normalizar_participante("ADMINISTRADOR", 7) is None
    assert normalizar_participante("SUPERVISOR", 7) is None


def test_rol_invalido() -> None:
    with pytest.raises(ErrorDeValidacionDeDominio):
        validar_rol("TESORERO")


def test_degradar_unico_admin_falla() -> None:
    with pytest.raises(UltimoAdministrador):
        verificar_no_ultimo_admin("ADMINISTRADOR", "SUPERVISOR", total_administradores=1)


def test_quitar_unico_admin_falla() -> None:
    # rol_nuevo=None representa eliminación de la membresía.
    with pytest.raises(UltimoAdministrador):
        verificar_no_ultimo_admin("ADMINISTRADOR", None, total_administradores=1)


def test_degradar_admin_con_otro_admin_ok() -> None:
    verificar_no_ultimo_admin("ADMINISTRADOR", "SUPERVISOR", total_administradores=2)


def test_admin_que_sigue_admin_ok() -> None:
    verificar_no_ultimo_admin("ADMINISTRADOR", "ADMINISTRADOR", total_administradores=1)


def test_quitar_no_admin_no_afecta_regla() -> None:
    verificar_no_ultimo_admin("SUPERVISOR", None, total_administradores=0)
