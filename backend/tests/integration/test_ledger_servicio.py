"""Integración del ledger vía ServicioContabilidad (S1-T04/T05, INV-01..03/RN-060)."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import (
    SaldoInsuficiente,
    ViolacionSeparacionDeFondos,
)
from app.modules.contabilidad.infrastructure.repositorios import (
    FabricaContabilidadSQLAlchemy,
    RepositorioFondosSQLAlchemy,
    RepositorioLedgerSQLAlchemy,
)
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen
from tests.conftest import crear_natillera, crear_usuario

_REF = ReferenciaOrigen(TipoOrigen.CUOTA, 1)


def _asiento(concepto: ConceptoContable, fondo: TipoFondo, naturaleza: Naturaleza) -> Asiento:
    return Asiento(
        monto=Dinero("100000"),
        naturaleza=naturaleza,
        concepto=concepto,
        fondo=fondo,
        referencia=_REF,
        descripcion="prueba",
    )


@pytest.fixture()
def contexto(session: Session) -> tuple[int, int]:
    usuario = crear_usuario(session)
    nat = crear_natillera(session)  # el helper ya crea los dos fondos (RN-001)
    session.flush()
    return nat.id, usuario.id


def test_registrar_asiento_valido_y_saldo(session: Session, contexto: tuple[int, int]) -> None:
    nat_id, autor = contexto
    svc = FabricaContabilidadSQLAlchemy(session).para(nat_id)
    leido = svc.registrar_asiento(
        _asiento(ConceptoContable.CUOTA_AHORRO, TipoFondo.AHORRO, Naturaleza.CREDITO), autor
    )
    assert leido.uuid
    ledger = RepositorioLedgerSQLAlchemy(session, nat_id)
    assert len(ledger.listar()) == 1
    fondos = RepositorioFondosSQLAlchemy(session, nat_id)
    assert fondos.saldo(TipoFondo.AHORRO) == Dinero("100000")


def test_asiento_invalido_viola_separacion(session: Session, contexto: tuple[int, int]) -> None:
    nat_id, autor = contexto
    svc = FabricaContabilidadSQLAlchemy(session).para(nat_id)
    # INTERES_PAGADO no puede afectar el Fondo de Ahorro (INV-03).
    with pytest.raises(ViolacionSeparacionDeFondos):
        svc.registrar_asiento(
            _asiento(ConceptoContable.INTERES_PAGADO, TipoFondo.AHORRO, Naturaleza.CREDITO),
            autor,
        )


def test_saldo_insuficiente_en_egreso(session: Session, contexto: tuple[int, int]) -> None:
    nat_id, autor = contexto
    svc = FabricaContabilidadSQLAlchemy(session).para(nat_id)
    # Desembolso (débito a Ahorro) sin saldo => SaldoInsuficiente (RN-007).
    with pytest.raises(SaldoInsuficiente):
        svc.registrar_asiento(
            _asiento(
                ConceptoContable.DESEMBOLSO_PRESTAMO, TipoFondo.AHORRO, Naturaleza.DEBITO
            ),
            autor,
        )


def test_ledger_no_expone_update_ni_delete(session: Session, contexto: tuple[int, int]) -> None:
    nat_id, _ = contexto
    ledger = RepositorioLedgerSQLAlchemy(session, nat_id)
    # RN-060: el repositorio del ledger es append-only.
    assert not hasattr(ledger, "update")
    assert not hasattr(ledger, "delete")
    assert not hasattr(ledger, "eliminar")
    assert not hasattr(ledger, "actualizar")
