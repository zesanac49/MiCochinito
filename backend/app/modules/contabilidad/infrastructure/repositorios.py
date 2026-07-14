"""Repositorios concretos de contabilidad (doc 05 §4).

`RepositorioLedgerSQLAlchemy` es append-only: NO expone update/delete (RN-060).
Los saldos se derivan del ledger sumando en Python con Decimal exacto (no en SQL,
para no depender de la aritmética numérica de SQLite; TEC-01/07).
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NoEncontrado
from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.fondo import Fondo
from app.modules.contabilidad.domain.periodos import calcular_periodos_mensuales
from app.modules.contabilidad.infrastructure.modelos import (
    AsientoModel,
    FondoModel,
    PeriodoModel,
)
from app.shared.domain.dinero import Dinero


class RepositorioFondosSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def crear_par(self) -> None:
        for tipo in (TipoFondo.AHORRO, TipoFondo.RENTABILIDAD):
            self._session.add(
                FondoModel(tipo=tipo.value, natillera_id=self._natillera_id, saldo_cache=0)
            )

    def existe_par(self) -> bool:
        stmt = select(func.count()).select_from(FondoModel).where(
            FondoModel.natillera_id == self._natillera_id
        )
        return (self._session.scalar(stmt) or 0) >= 2

    def id_de(self, tipo: TipoFondo) -> int | None:
        stmt = select(FondoModel.id).where(
            FondoModel.natillera_id == self._natillera_id, FondoModel.tipo == tipo.value
        )
        return self._session.scalar(stmt)

    def cargar(self, tipo: TipoFondo) -> Fondo:
        fondo_id = self.id_de(tipo)
        if fondo_id is None:
            raise NoEncontrado(f"Fondo {tipo.value} inexistente en la natillera.")
        return Fondo(tipo, self._natillera_id, id=fondo_id)

    def saldo(self, tipo: TipoFondo) -> Dinero:
        fondo_id = self.id_de(tipo)
        if fondo_id is None:
            return Dinero.cero()
        stmt = select(AsientoModel.naturaleza, AsientoModel.monto).where(
            AsientoModel.natillera_id == self._natillera_id,
            AsientoModel.fondo_id == fondo_id,
        )
        total = Dinero.cero()
        for naturaleza, monto in self._session.execute(stmt).all():
            d = Dinero(monto)  # monto llega como Decimal (SQLAlchemy Numeric)
            total = total + d if naturaleza == Naturaleza.CREDITO.value else total - d
        return total

    def saldo_cache(self, tipo: TipoFondo) -> Dinero:
        modelo = self._session.scalar(
            select(FondoModel).where(
                FondoModel.natillera_id == self._natillera_id,
                FondoModel.tipo == tipo.value,
            )
        )
        return Dinero(modelo.saldo_cache) if modelo is not None else Dinero.cero()

    def actualizar_cache(self, tipo: TipoFondo, saldo: Dinero) -> None:
        modelo = self._session.scalar(
            select(FondoModel).where(
                FondoModel.natillera_id == self._natillera_id,
                FondoModel.tipo == tipo.value,
            )
        )
        if modelo is not None:
            modelo.saldo_cache = saldo.monto
            modelo.saldo_cache_actualizado = datetime.now(UTC)


class RepositorioLedgerSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def append(self, asiento: Asiento, fondo_id: int, creado_por: int) -> AsientoLeido:
        modelo = AsientoModel(
            natillera_id=self._natillera_id,
            fondo_id=fondo_id,
            participante_id=asiento.participante_id,
            naturaleza=asiento.naturaleza.value,
            concepto=asiento.concepto.value,
            monto=asiento.monto.monto,
            periodo_id=asiento.periodo_id,
            origen_tipo=asiento.referencia.tipo.value,
            origen_id=asiento.referencia.id_origen,
            reversa_de_id=asiento.reversa_de_id,
            descripcion=asiento.descripcion,
            creado_por=creado_por,
        )
        self._session.add(modelo)
        self._session.flush()  # asigna id/uuid/created_at
        return self._a_leido(modelo, asiento.fondo)

    def listar(
        self,
        *,
        fondo: TipoFondo | None = None,
        concepto: ConceptoContable | None = None,
        participante_id: int | None = None,
    ) -> list[AsientoLeido]:
        stmt = (
            select(AsientoModel, FondoModel.tipo)
            .join(FondoModel, AsientoModel.fondo_id == FondoModel.id)
            .where(AsientoModel.natillera_id == self._natillera_id)
            .order_by(AsientoModel.created_at, AsientoModel.id)
        )
        if fondo is not None:
            stmt = stmt.where(FondoModel.tipo == fondo.value)
        if concepto is not None:
            stmt = stmt.where(AsientoModel.concepto == concepto.value)
        if participante_id is not None:
            stmt = stmt.where(AsientoModel.participante_id == participante_id)
        return [
            self._a_leido(modelo, TipoFondo(tipo))
            for modelo, tipo in self._session.execute(stmt).all()
        ]

    def rentabilidad_por_fuente(self) -> dict[str, Dinero]:
        """Σ créditos a Rentabilidad por concepto (RF-901). Jamás RETORNO_CAPITAL."""
        fuentes = (
            ConceptoContable.INTERES_PAGADO,
            ConceptoContable.UTILIDAD_ACTIVIDAD,
            ConceptoContable.MULTA_PAGADA,
        )
        resultado: dict[str, Dinero] = {}
        for concepto in fuentes:
            total = Dinero.cero()
            for a in self.listar(fondo=TipoFondo.RENTABILIDAD, concepto=concepto):
                if a.naturaleza is Naturaleza.CREDITO:
                    total = total + a.monto
            resultado[concepto.value] = total
        return resultado

    def obtener_por_uuid(self, uuid: str) -> AsientoLeido | None:
        fila = self._session.execute(
            select(AsientoModel, FondoModel.tipo)
            .join(FondoModel, AsientoModel.fondo_id == FondoModel.id)
            .where(
                AsientoModel.natillera_id == self._natillera_id,
                AsientoModel.uuid == uuid,
            )
        ).first()
        if fila is None:
            return None
        modelo, tipo = fila
        return self._a_leido(modelo, TipoFondo(tipo))

    @staticmethod
    def _a_leido(modelo: AsientoModel, fondo: TipoFondo) -> AsientoLeido:
        return AsientoLeido(
            uuid=modelo.uuid,
            creado_en=modelo.created_at,
            fondo=fondo,
            naturaleza=Naturaleza(modelo.naturaleza),
            concepto=ConceptoContable(modelo.concepto),
            monto=Dinero(modelo.monto),
            descripcion=modelo.descripcion,
            origen_tipo=modelo.origen_tipo,
            origen_id=modelo.origen_id,
            participante_id=modelo.participante_id,
            id=modelo.id,
        )


class FabricaContabilidadSQLAlchemy:
    """Construye un ServicioContabilidad ligado a un tenant (composición)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def para(self, natillera_id: int) -> ServicioContabilidad:
        return ServicioContabilidad(
            RepositorioFondosSQLAlchemy(self._session, natillera_id),
            RepositorioLedgerSQLAlchemy(self._session, natillera_id),
        )


class RepositorioPeriodosSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    def existe(self, anio: int, mes: int) -> bool:
        stmt = select(func.count()).select_from(PeriodoModel).where(
            PeriodoModel.natillera_id == self._natillera_id,
            PeriodoModel.anio == anio,
            PeriodoModel.mes == mes,
        )
        return (self._session.scalar(stmt) or 0) > 0

    def listar(self) -> list[PeriodoModel]:
        stmt = (
            select(PeriodoModel)
            .where(PeriodoModel.natillera_id == self._natillera_id)
            .order_by(PeriodoModel.anio, PeriodoModel.mes)
        )
        return list(self._session.scalars(stmt).all())

    def obtener_por_uuid(self, uuid: str) -> PeriodoModel | None:
        return self._session.scalar(
            select(PeriodoModel).where(
                PeriodoModel.natillera_id == self._natillera_id,
                PeriodoModel.uuid == uuid,
            )
        )

    def obtener_id_por_uuid(self, uuid: str) -> int | None:
        m = self.obtener_por_uuid(uuid)
        return m.id if m is not None else None


class GeneradorPeriodosSQLAlchemy:
    """Genera los períodos mensuales del ciclo (idempotente)."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def generar(
        self, natillera_id: int, ciclo_inicio: date, ciclo_fin: date, dia_limite: int
    ) -> int:
        repo = RepositorioPeriodosSQLAlchemy(self._session, natillera_id)
        creados = 0
        for anio, mes, fecha_limite in calcular_periodos_mensuales(
            ciclo_inicio, ciclo_fin, dia_limite
        ):
            if repo.existe(anio, mes):
                continue
            self._session.add(
                PeriodoModel(
                    natillera_id=natillera_id,
                    anio=anio,
                    mes=mes,
                    fecha_limite_cuota=fecha_limite,
                    conciliado=False,
                )
            )
            creados += 1
        return creados
