"""Agregado `Actividad` (doc 02 §4.5, INV-05..09).

Módulo genérico: una sola entidad `Actividad` con tipo (polla, rifa, ...). La
utilidad se calcula de los movimientos (`utilidad = Σingresos − Σpremios −
Σgastos`, RN-041); no es editable. La polla añade números anuales (INV-08),
sorteo solo entre pagados (INV-07) y "sin ganador → utilidad íntegra a
Rentabilidad" (INV-09).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.modules.actividades.domain.estados import (
    EstadoActividad,
    TipoActividad,
    TipoMovimiento,
    transicion_valida,
)
from app.modules.actividades.domain.excepciones import (
    NumeroNoDisponible,
    SorteoYaRegistrado,
)
from app.shared.domain.base import RaizDeAgregado
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio, TransicionInvalida
from app.shared.domain.numero_polla import NumeroPolla


@dataclass(slots=True)
class Numero:
    numero: int
    participante_id: int
    pagado: bool = False


@dataclass(frozen=True, slots=True)
class Movimiento:
    tipo: TipoMovimiento
    concepto: str
    valor: Dinero
    participante_id: int | None = None


@dataclass(frozen=True, slots=True)
class Sorteo:
    numero_ganador: int
    hubo_ganador: bool
    participante_ganador_id: int | None
    fuente: str


class Actividad(RaizDeAgregado):
    def __init__(
        self,
        tipo: TipoActividad,
        nombre: str,
        periodo_id: int,
        estado: EstadoActividad = EstadoActividad.BORRADOR,
        valor_numero: Dinero | None = None,
        cantidad_numeros: int | None = None,
        premio: Dinero | None = None,
        fecha_sorteo: date | None = None,
        clonada_de_id: int | None = None,
        numeros: list[Numero] | None = None,
        movimientos: list[Movimiento] | None = None,
        sorteo: Sorteo | None = None,
        id: int | None = None,
        uuid: str | None = None,
    ) -> None:
        super().__init__(id)
        if not nombre.strip():
            raise ErrorDeValidacionDeDominio("La actividad requiere nombre.")
        self._tipo = tipo
        self._nombre = nombre
        self._periodo_id = periodo_id
        self._estado = estado
        self._valor_numero = valor_numero
        self._cantidad_numeros = cantidad_numeros
        self._premio = premio
        self._fecha_sorteo = fecha_sorteo
        self._clonada_de_id = clonada_de_id
        self._numeros: dict[int, Numero] = {n.numero: n for n in (numeros or [])}
        self._movimientos: list[Movimiento] = list(movimientos or [])
        self._sorteo = sorteo
        self.uuid = uuid

    # --- Fábrica ------------------------------------------------------------
    @classmethod
    def crear(
        cls,
        tipo: TipoActividad,
        nombre: str,
        periodo_id: int,
        valor_numero: Dinero | None = None,
        cantidad_numeros: int | None = None,
        fecha_sorteo: date | None = None,
    ) -> Actividad:
        # El premio ya no se digita: se calcula del pozo al sortear (premio_calculado).
        return cls(
            tipo,
            nombre,
            periodo_id,
            valor_numero=valor_numero,
            cantidad_numeros=cantidad_numeros,
            fecha_sorteo=fecha_sorteo,
        )

    # --- Acceso -------------------------------------------------------------
    @property
    def tipo(self) -> TipoActividad:
        return self._tipo

    @property
    def nombre(self) -> str:
        return self._nombre

    @property
    def periodo_id(self) -> int:
        return self._periodo_id

    @property
    def estado(self) -> EstadoActividad:
        return self._estado

    @property
    def valor_numero(self) -> Dinero | None:
        return self._valor_numero

    @property
    def cantidad_numeros(self) -> int | None:
        return self._cantidad_numeros

    @property
    def premio(self) -> Dinero | None:
        return self._premio

    @property
    def fecha_sorteo(self) -> date | None:
        return self._fecha_sorteo

    @property
    def clonada_de_id(self) -> int | None:
        return self._clonada_de_id

    @property
    def numeros(self) -> list[Numero]:
        return sorted(self._numeros.values(), key=lambda n: n.numero)

    @property
    def movimientos(self) -> list[Movimiento]:
        return list(self._movimientos)

    @property
    def sorteo(self) -> Sorteo | None:
        return self._sorteo

    # --- Estado -------------------------------------------------------------
    def _transicionar(self, hacia: EstadoActividad) -> None:
        if not transicion_valida(self._estado, hacia):
            raise TransicionInvalida(
                "Transición de estado de actividad no permitida.",
                {"desde": self._estado.value, "hacia": hacia.value},
            )
        self._estado = hacia

    def abrir(self) -> None:
        self._transicionar(EstadoActividad.ABIERTA)

    def _exigir_editable(self) -> None:
        if self._estado in (EstadoActividad.SORTEADA, EstadoActividad.CERRADA):
            raise TransicionInvalida(
                "La actividad no admite cambios en este estado.",
                {"estado": self._estado.value},
            )

    # --- Números (polla) ----------------------------------------------------
    def asignar_numero(self, numero: int, participante_id: int) -> None:
        self._exigir_editable()
        if self._cantidad_numeros is None:
            raise ErrorDeValidacionDeDominio("La actividad no tiene números configurados.")
        NumeroPolla(numero, self._cantidad_numeros)  # valida rango
        if numero in self._numeros:
            raise NumeroNoDisponible(
                "El número ya está asignado.", {"numero": numero}
            )
        self._numeros[numero] = Numero(numero=numero, participante_id=participante_id)

    def marcar_pago_numero(self, numero: int) -> None:
        """Marca pagado un número y registra el ingreso de la actividad (RF-503)."""
        self._exigir_editable()
        n = self._numeros.get(numero)
        if n is None:
            raise NumeroNoDisponible("El número no está asignado.", {"numero": numero})
        if n.pagado:
            return  # idempotente
        if self._valor_numero is None:
            raise ErrorDeValidacionDeDominio("La actividad no tiene valor por número.")
        n.pagado = True
        self._movimientos.append(
            Movimiento(
                tipo=TipoMovimiento.INGRESO,
                concepto=f"Pago de número {numero}",
                valor=self._valor_numero,
                participante_id=n.participante_id,
            )
        )

    def numeros_activos(self) -> list[Numero]:
        """Solo los números pagados participan (RN-046, INV-07)."""
        return [n for n in self._numeros.values() if n.pagado]

    # --- Movimientos --------------------------------------------------------
    def registrar_movimiento(
        self, tipo: TipoMovimiento, concepto: str, valor: Dinero, participante_id: int | None = None
    ) -> None:
        self._exigir_editable()
        if not valor.es_positivo():
            raise ErrorDeValidacionDeDominio("El valor del movimiento debe ser positivo.")
        self._movimientos.append(Movimiento(tipo, concepto, valor, participante_id))

    # --- Sorteo -------------------------------------------------------------
    def sortear(self, numero_ganador: int, fuente: str) -> Sorteo:
        """Registra el número ganador externo. Solo los números pagados pueden
        ganar (INV-07); si el ganador no está pagado, no hay ganador (INV-09)."""
        if self._sorteo is not None:
            raise SorteoYaRegistrado("El sorteo ya fue registrado.")
        if self._estado is not EstadoActividad.ABIERTA:
            raise TransicionInvalida(
                "Solo una actividad abierta puede sortearse.", {"estado": self._estado.value}
            )
        ganador = next(
            (n for n in self.numeros_activos() if n.numero == numero_ganador), None
        )
        hubo_ganador = ganador is not None
        if hubo_ganador and ganador is not None:
            # El premio es todo el pozo: valor por número × números pagados
            # (RF-503 ajustado). El ganador se lleva lo recaudado; el fondo solo
            # gana cuando no hay ganador (INV-09).
            premio = self.premio_calculado()
            if premio.es_positivo():
                self._movimientos.append(
                    Movimiento(
                        tipo=TipoMovimiento.PREMIO,
                        concepto=f"Premio del sorteo (número {numero_ganador})",
                        valor=premio,
                        participante_id=ganador.participante_id,
                    )
                )
        self._sorteo = Sorteo(
            numero_ganador=numero_ganador,
            hubo_ganador=hubo_ganador,
            participante_ganador_id=ganador.participante_id if ganador else None,
            fuente=fuente,
        )
        self._transicionar(EstadoActividad.SORTEADA)
        return self._sorteo

    # --- Premio y utilidad --------------------------------------------------
    def premio_calculado(self) -> Dinero:
        """Premio = todo lo recaudado por los números pagados (valor_numero ×
        números pagados). Es lo que se lleva el ganador; se usa en el sorteo y
        para mostrar el pozo actual antes del sorteo."""
        return self._suma(TipoMovimiento.INGRESO)

    def utilidad(self) -> Dinero:
        ingresos = self._suma(TipoMovimiento.INGRESO)
        premios = self._suma(TipoMovimiento.PREMIO)
        gastos = self._suma(TipoMovimiento.GASTO)
        return ingresos - premios - gastos

    def _suma(self, tipo: TipoMovimiento) -> Dinero:
        total = Dinero.cero()
        for m in self._movimientos:
            if m.tipo is tipo:
                total = total + m.valor
        return total

    def cerrar(self) -> Dinero:
        """Cierra la actividad y devuelve su utilidad (RF-506). El asiento al
        Fondo de Rentabilidad lo hace el servicio de aplicación."""
        if self._estado not in (EstadoActividad.ABIERTA, EstadoActividad.SORTEADA):
            raise TransicionInvalida(
                "La actividad no puede cerrarse en este estado.",
                {"estado": self._estado.value},
            )
        utilidad = self.utilidad()
        self._estado = EstadoActividad.CERRADA
        return utilidad

    # --- Clonación (INV-08, RN-049) ----------------------------------------
    def clonar_para(self, periodo_id: int) -> Actividad:
        """Copia participantes, números, configuración, premio y valor; excluye
        pagos, ganador, sorteo, movimientos y auditoría. Nace en BORRADOR."""
        numeros = [
            Numero(numero=n.numero, participante_id=n.participante_id, pagado=False)
            for n in self._numeros.values()
        ]
        return Actividad(
            tipo=self._tipo,
            nombre=self._nombre,
            periodo_id=periodo_id,
            estado=EstadoActividad.BORRADOR,
            valor_numero=self._valor_numero,
            cantidad_numeros=self._cantidad_numeros,
            premio=self._premio,
            fecha_sorteo=None,
            clonada_de_id=self._id,
            numeros=numeros,
            movimientos=None,
            sorteo=None,
        )
