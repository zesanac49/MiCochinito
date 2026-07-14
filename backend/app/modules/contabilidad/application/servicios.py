"""Servicio de aplicación de contabilidad (doc 02 §2, doc 05 §5).

Contabilidad es el ÚNICO módulo que escribe asientos. Otros módulos piden
registrar un asiento a través de `registrar_asiento`, que:
  1. resuelve el fondo destino,
  2. valida con `Fondo.validar_asiento` (INV-01..03),
  3. verifica saldo no negativo en egresos (RN-007),
  4. hace append al ledger y actualiza el caché reconciliable del fondo.
Todo dentro de la transacción del Unit of Work (RNF-03).
"""

from __future__ import annotations

from app.core.errors import NoEncontrado
from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.puertos import (
    RepositorioFondos,
    RepositorioLedger,
)
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import SaldoInsuficiente
from app.shared.domain.dinero import Dinero
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen


class ServicioContabilidad:
    def __init__(self, fondos: RepositorioFondos, ledger: RepositorioLedger) -> None:
        self._fondos = fondos
        self._ledger = ledger

    def crear_fondos(self) -> None:
        """Crea los dos fondos de la natillera si no existen (RN-001)."""
        if not self._fondos.existe_par():
            self._fondos.crear_par()

    def saldo(self, tipo: TipoFondo) -> Dinero:
        """Saldo derivado del fondo desde el ledger (RN-063)."""
        return self._fondos.saldo(tipo)

    def saldo_participante(self, participante_id: int, tipo: TipoFondo) -> Dinero:
        """Saldo de un participante en un fondo (créditos − débitos de sus asientos)."""
        total = Dinero.cero()
        for a in self._ledger.listar(fondo=tipo, participante_id=participante_id):
            total = total + a.monto if a.naturaleza is Naturaleza.CREDITO else total - a.monto
        return total

    def registrar_asiento(self, asiento: Asiento, creado_por: int) -> AsientoLeido:
        fondo = self._fondos.cargar(asiento.fondo)
        fondo.validar_asiento(asiento)  # INV-01..03

        # RN-007: ningún fondo puede quedar en negativo.
        if asiento.naturaleza is Naturaleza.DEBITO:
            saldo_actual = self._fondos.saldo(asiento.fondo)
            if (saldo_actual - asiento.monto).es_negativo():
                raise SaldoInsuficiente(
                    "El fondo no tiene saldo suficiente para el egreso.",
                    {
                        "fondo": asiento.fondo.value,
                        "saldo_disponible": saldo_actual.como_str(),
                        "monto": asiento.monto.como_str(),
                    },
                )

        fondo_id = self._fondos.id_de(asiento.fondo)
        assert fondo_id is not None  # el fondo existe (cargar habría fallado si no)
        leido = self._ledger.append(asiento, fondo_id, creado_por)

        # Actualiza el caché de saldo (reconciliable, RN-063) en la misma tx.
        self._fondos.actualizar_cache(asiento.fondo, self._fondos.saldo(asiento.fondo))
        return leido

    def revertir(self, asiento_uuid: str, motivo: str, creado_por: int) -> AsientoLeido:
        """Corrige un asiento con un asiento de REVERSION espejo (RN-061).

        Nunca UPDATE/DELETE: se registra un asiento con la naturaleza opuesta,
        mismo fondo y monto, referenciando al original. La reversión no valida
        saldo (es una corrección, no un egreso de negocio)."""
        original = self._ledger.obtener_por_uuid(asiento_uuid)
        if original is None or original.id is None:
            raise NoEncontrado("Asiento inexistente.")
        naturaleza_opuesta = (
            Naturaleza.DEBITO
            if original.naturaleza is Naturaleza.CREDITO
            else Naturaleza.CREDITO
        )
        reverso = Asiento(
            monto=original.monto,
            naturaleza=naturaleza_opuesta,
            concepto=ConceptoContable.REVERSION,
            fondo=original.fondo,
            referencia=ReferenciaOrigen(TipoOrigen.REVERSION, original.id),
            descripcion=f"Reversión: {motivo}",
            participante_id=original.participante_id,
            reversa_de_id=original.id,
        )
        fondo = self._fondos.cargar(original.fondo)
        fondo.validar_asiento(reverso)  # REVERSION con reversa_de_id => válido
        fondo_id = self._fondos.id_de(original.fondo)
        assert fondo_id is not None
        leido = self._ledger.append(reverso, fondo_id, creado_por)
        self._fondos.actualizar_cache(original.fondo, self._fondos.saldo(original.fondo))
        return leido
