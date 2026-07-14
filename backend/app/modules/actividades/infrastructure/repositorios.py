"""Repositorio y mappers de actividades (doc 05 §4).

La actividad es un agregado con colecciones (números, movimientos, sorteo). Al
guardar se reescriben números y movimientos (son pequeños y sin FKs externas); el
sorteo es inmutable: solo se inserta si aún no existe.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.modules.actividades.domain.actividad import (
    Actividad,
    Movimiento,
    Numero,
    Sorteo,
)
from app.modules.actividades.domain.estados import (
    EstadoActividad,
    TipoActividad,
    TipoMovimiento,
)
from app.modules.actividades.infrastructure.modelos import (
    ActividadModel,
    ActividadMovimientoModel,
    ActividadNumeroModel,
    SorteoModel,
)
from app.shared.domain.dinero import Dinero


def _dinero_opt(valor: object) -> Dinero | None:
    return Dinero(valor) if valor is not None else None  # type: ignore[arg-type]


class RepositorioActividadesSQLAlchemy:
    def __init__(self, session: Session, natillera_id: int) -> None:
        self._session = session
        self._natillera_id = natillera_id

    # --- Escritura ----------------------------------------------------------
    def agregar(self, actividad: Actividad) -> Actividad:
        m = ActividadModel(
            natillera_id=self._natillera_id,
            tipo=actividad.tipo.value,
            nombre=actividad.nombre,
            periodo_id=actividad.periodo_id,
            estado=actividad.estado.value,
            valor_numero=actividad.valor_numero.monto if actividad.valor_numero else None,
            cantidad_numeros=actividad.cantidad_numeros,
            premio=actividad.premio.monto if actividad.premio else None,
            fecha_sorteo=actividad.fecha_sorteo,
            clonada_de_id=actividad.clonada_de_id,
        )
        self._session.add(m)
        self._session.flush()
        actividad._asignar_id(m.id)
        actividad.uuid = m.uuid
        self._sincronizar(actividad, m.id)
        return actividad

    def guardar(self, actividad: Actividad) -> None:
        assert actividad.id is not None
        m = self._session.get(ActividadModel, actividad.id)
        if m is None or m.natillera_id != self._natillera_id:
            raise ValueError("Actividad inexistente en el tenant.")
        m.estado = actividad.estado.value
        if actividad.estado is EstadoActividad.CERRADA:
            m.utilidad_cierre = actividad.utilidad().monto
        self._sincronizar(actividad, actividad.id)

    def _sincronizar(self, actividad: Actividad, actividad_id: int) -> None:
        # Números y movimientos: reescritura completa (pequeños, sin FKs externas).
        self._session.execute(
            delete(ActividadNumeroModel).where(
                ActividadNumeroModel.actividad_id == actividad_id
            )
        )
        self._session.execute(
            delete(ActividadMovimientoModel).where(
                ActividadMovimientoModel.actividad_id == actividad_id
            )
        )
        for n in actividad.numeros:
            self._session.add(
                ActividadNumeroModel(
                    natillera_id=self._natillera_id,
                    actividad_id=actividad_id,
                    numero=n.numero,
                    participante_id=n.participante_id,
                    pagado=n.pagado,
                    pagado_en=datetime.now(UTC) if n.pagado else None,
                )
            )
        for mov in actividad.movimientos:
            self._session.add(
                ActividadMovimientoModel(
                    natillera_id=self._natillera_id,
                    actividad_id=actividad_id,
                    tipo=mov.tipo.value,
                    concepto=mov.concepto,
                    valor=mov.valor.monto,
                    participante_id=mov.participante_id,
                )
            )
        # Sorteo: inmutable, se inserta solo si aún no existe.
        sorteo = actividad.sorteo
        if sorteo is not None:
            existe = self._session.scalar(
                select(SorteoModel).where(SorteoModel.actividad_id == actividad_id)
            )
            if existe is None:
                self._session.add(
                    SorteoModel(
                        natillera_id=self._natillera_id,
                        actividad_id=actividad_id,
                        numero_ganador=sorteo.numero_ganador,
                        hubo_ganador=sorteo.hubo_ganador,
                        participante_ganador_id=sorteo.participante_ganador_id,
                        fuente=sorteo.fuente,
                    )
                )

    # --- Lectura ------------------------------------------------------------
    def obtener_por_uuid(self, uuid: str) -> Actividad | None:
        m = self._session.scalar(
            select(ActividadModel).where(
                ActividadModel.natillera_id == self._natillera_id,
                ActividadModel.uuid == uuid,
            )
        )
        return self._a_dominio(m) if m is not None else None

    def listar(
        self,
        *,
        periodo_id: int | None = None,
        tipo: TipoActividad | None = None,
        estado: EstadoActividad | None = None,
    ) -> list[Actividad]:
        stmt = select(ActividadModel).where(
            ActividadModel.natillera_id == self._natillera_id
        )
        if periodo_id is not None:
            stmt = stmt.where(ActividadModel.periodo_id == periodo_id)
        if tipo is not None:
            stmt = stmt.where(ActividadModel.tipo == tipo.value)
        if estado is not None:
            stmt = stmt.where(ActividadModel.estado == estado.value)
        modelos = self._session.scalars(stmt.order_by(ActividadModel.id)).all()
        return [self._a_dominio(m) for m in modelos]

    def ids_no_cerradas(self) -> list[int]:
        stmt = select(ActividadModel.id).where(
            ActividadModel.natillera_id == self._natillera_id,
            ActividadModel.estado != EstadoActividad.CERRADA.value,
        )
        return list(self._session.scalars(stmt).all())

    def _a_dominio(self, m: ActividadModel) -> Actividad:
        numeros = [
            Numero(numero=n.numero, participante_id=n.participante_id, pagado=n.pagado)
            for n in self._session.scalars(
                select(ActividadNumeroModel).where(
                    ActividadNumeroModel.actividad_id == m.id
                )
            ).all()
        ]
        movimientos = [
            Movimiento(
                tipo=TipoMovimiento(mo.tipo),
                concepto=mo.concepto,
                valor=Dinero(mo.valor),
                participante_id=mo.participante_id,
            )
            for mo in self._session.scalars(
                select(ActividadMovimientoModel).where(
                    ActividadMovimientoModel.actividad_id == m.id
                )
            ).all()
        ]
        sm = self._session.scalar(
            select(SorteoModel).where(SorteoModel.actividad_id == m.id)
        )
        sorteo = (
            Sorteo(
                numero_ganador=sm.numero_ganador,
                hubo_ganador=sm.hubo_ganador,
                participante_ganador_id=sm.participante_ganador_id,
                fuente=sm.fuente,
            )
            if sm is not None
            else None
        )
        return Actividad(
            tipo=TipoActividad(m.tipo),
            nombre=m.nombre,
            periodo_id=m.periodo_id,
            estado=EstadoActividad(m.estado),
            valor_numero=_dinero_opt(m.valor_numero),
            cantidad_numeros=m.cantidad_numeros,
            premio=_dinero_opt(m.premio),
            fecha_sorteo=m.fecha_sorteo,
            clonada_de_id=m.clonada_de_id,
            numeros=numeros,
            movimientos=movimientos,
            sorteo=sorteo,
            id=m.id,
            uuid=m.uuid,
        )
