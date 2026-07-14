"""`Fondo` — agregado donde vive la separación de fondos (INV-01..03).

`validar_asiento` es la ÚNICA puerta de escritura contable válida: consulta la
matriz (doc 02 §5) y rechaza cualquier combinación concepto/fondo/naturaleza no
permitida con `ViolacionSeparacionDeFondos`. El saldo se deriva del ledger
(RN-063), nunca se guarda como fuente de verdad.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import ViolacionSeparacionDeFondos
from app.modules.contabilidad.domain.matriz import naturaleza_permitida
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero


class Fondo(RaizDeAgregado):
    """Bolsa contable con reglas de ingreso/egreso. Exactamente dos por natillera."""

    def __init__(self, tipo: TipoFondo, natillera_id: int, id: int | None = None) -> None:
        super().__init__(id)
        self._tipo = tipo
        self._natillera_id = natillera_id

    @property
    def tipo(self) -> TipoFondo:
        return self._tipo

    @property
    def natillera_id(self) -> int:
        return self._natillera_id

    def validar_asiento(self, asiento: Asiento) -> None:
        """Lanza `ViolacionSeparacionDeFondos` si el asiento no respeta la matriz.

        Aquí viven INV-01..03. Todo asiento que se escriba al ledger pasa por
        aquí (doc 02 §2: Contabilidad es el único módulo que escribe asientos).
        """
        if asiento.fondo is not self._tipo:
            raise ViolacionSeparacionDeFondos(
                "El asiento apunta a un fondo distinto del que lo valida.",
                {"asiento_fondo": asiento.fondo.value, "fondo": self._tipo.value},
            )

        # REVERSION es espejo del asiento revertido (RN-061): cualquier
        # naturaleza es válida sobre cualquier fondo, pero exige referenciar el
        # asiento que revierte.
        if asiento.concepto is ConceptoContable.REVERSION:
            if asiento.reversa_de_id is None:
                raise ViolacionSeparacionDeFondos(
                    "Una REVERSION debe referenciar el asiento que revierte "
                    "(reversa_de_id).",
                    {"concepto": asiento.concepto.value},
                )
            return

        permitida = naturaleza_permitida(asiento.concepto, self._tipo)
        if permitida is None:
            raise ViolacionSeparacionDeFondos(
                "El concepto no puede afectar este fondo (matriz de separación "
                "de fondos, INV-01..03).",
                {"concepto": asiento.concepto.value, "fondo": self._tipo.value},
            )
        if asiento.naturaleza is not permitida:
            raise ViolacionSeparacionDeFondos(
                "Naturaleza incorrecta para el concepto en este fondo.",
                {
                    "concepto": asiento.concepto.value,
                    "fondo": self._tipo.value,
                    "naturaleza_recibida": asiento.naturaleza.value,
                    "naturaleza_esperada": permitida.value,
                },
            )

    @staticmethod
    def saldo(asientos: Iterable[Asiento]) -> Dinero:
        """Saldo derivado del ledger: Σ créditos − Σ débitos (RN-063)."""
        total = Dinero.cero()
        for a in asientos:
            total = (
                total + a.monto
                if a.naturaleza is Naturaleza.CREDITO
                else total - a.monto
            )
        return total
