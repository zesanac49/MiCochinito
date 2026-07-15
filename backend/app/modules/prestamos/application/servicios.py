"""Servicio de aplicación de préstamos (RF-401..405).

Contabilidad sigue siendo el único que escribe asientos: aquí se orquesta el
préstamo y se delega cada asiento en `ServicioContabilidad.registrar_asiento`.
El pago genera DOS asientos separados (capital → Ahorro, interés → Rentabilidad),
nunca combinados (RN-033).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.core.errors import NoEncontrado
from app.modules.contabilidad.application.dtos import AsientoLeido
from app.modules.contabilidad.application.servicios import ServicioContabilidad
from app.modules.contabilidad.domain.asiento import Asiento
from app.modules.contabilidad.domain.conceptos import (
    ConceptoContable,
    Naturaleza,
    TipoFondo,
)
from app.modules.contabilidad.domain.excepciones import SaldoInsuficiente
from app.modules.natilleras.application.consultas import ConsultaNatillera
from app.modules.participantes.application.puertos import RepositorioParticipantes
from app.modules.prestamos.application.puertos import (
    RepositorioPrestamoPagos,
    RepositorioPrestamos,
)
from app.modules.prestamos.domain.descomposicion import Descomposicion
from app.modules.prestamos.domain.excepciones import (
    TopeCapitalExcedido,
    TopePrestamosExcedido,
)
from app.modules.prestamos.domain.prestamo import Prestamo
from app.shared.application.unidad_de_trabajo import UnidadDeTrabajo
from app.shared.domain.dinero import Dinero
from app.shared.domain.excepciones import ErrorDeValidacionDeDominio
from app.shared.domain.referencia import ReferenciaOrigen, TipoOrigen
from app.shared.domain.tasa import TasaInteres


@dataclass(frozen=True, slots=True)
class ResultadoPago:
    descomposicion: Descomposicion
    prestamo: Prestamo
    asientos: list[AsientoLeido]


class ServicioPrestamos:
    def __init__(
        self,
        uow: UnidadDeTrabajo,
        consulta: ConsultaNatillera,
        participantes: RepositorioParticipantes,
        prestamos: RepositorioPrestamos,
        pagos: RepositorioPrestamoPagos,
        contabilidad: ServicioContabilidad,
    ) -> None:
        self._uow = uow
        self._consulta = consulta
        self._participantes = participantes
        self._prestamos = prestamos
        self._pagos = pagos
        self._contabilidad = contabilidad

    def _participante_id(self, uuid: str) -> int:
        p = self._participantes.obtener_por_uuid(uuid)
        if p is None or p.id is None:
            raise NoEncontrado("Participante inexistente.")
        return p.id

    def _cargar(self, uuid: str) -> Prestamo:
        prestamo = self._prestamos.obtener_por_uuid(uuid)
        if prestamo is None:
            raise NoEncontrado("Préstamo inexistente.")
        return prestamo

    # --- RF-401 -------------------------------------------------------------
    def solicitar(
        self,
        natillera_uuid: str,
        participante_uuid: str,
        capital: Dinero,
        tasa: Decimal,
        plazo_meses: int,
    ) -> Prestamo:
        with self._uow:
            datos = self._consulta.datos_para_prestamo(natillera_uuid, "CREAR_PRESTAMO")
            participante_id = self._participante_id(participante_uuid)
            tasa_vo = TasaInteres(tasa, tope=datos.tasa_max)
            if tasa_vo.porcentaje < datos.tasa_min:
                raise ErrorDeValidacionDeDominio(
                    "La tasa es menor que el mínimo configurado.",
                    {"tasa": str(tasa), "min": str(datos.tasa_min)},
                )
            prestamo = Prestamo.solicitar(participante_id, capital, tasa_vo, plazo_meses)
            self._prestamos.agregar(prestamo)
            self._uow.commit()
        return prestamo

    # --- RF-402 -------------------------------------------------------------
    def decidir(
        self, natillera_uuid: str, prestamo_uuid: str, aprobar: bool, motivo: str | None
    ) -> Prestamo:
        with self._uow:
            prestamo = self._cargar(prestamo_uuid)
            if not aprobar:
                prestamo.rechazar(motivo or "Sin motivo")
                self._prestamos.guardar(prestamo)
                self._uow.commit()
                return prestamo

            datos = self._consulta.datos_para_prestamo(natillera_uuid, "CREAR_PRESTAMO")
            activos = self._prestamos.cuenta_activos(prestamo.participante_id)
            if activos >= datos.max_prestamos_activos:
                raise TopePrestamosExcedido(
                    "El participante alcanzó el tope de préstamos activos.",
                    {"tope": datos.max_prestamos_activos},
                )
            vigente = self._prestamos.capital_vigente_de(prestamo.participante_id)
            if (vigente + prestamo.capital) > datos.max_capital_vigente:
                raise TopeCapitalExcedido(
                    "El capital vigente excedería el tope del participante.",
                    {
                        "vigente": vigente.como_str(),
                        "solicitado": prestamo.capital.como_str(),
                        "tope": datos.max_capital_vigente.como_str(),
                    },
                )
            self._exigir_saldo_ahorro(prestamo.capital)
            prestamo.aprobar()
            self._prestamos.guardar(prestamo)
            self._uow.commit()
        return prestamo

    # --- RF-403 -------------------------------------------------------------
    def desembolsar(
        self, natillera_uuid: str, prestamo_uuid: str, hoy: date, autor: int
    ) -> Prestamo:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "CREAR_PRESTAMO")
            prestamo = self._cargar(prestamo_uuid)
            self._exigir_saldo_ahorro(prestamo.capital)  # revalida al confirmar
            prestamo.desembolsar(hoy)
            assert prestamo.id is not None
            self._contabilidad.registrar_asiento(
                Asiento(
                    monto=prestamo.capital,
                    naturaleza=Naturaleza.DEBITO,
                    concepto=ConceptoContable.DESEMBOLSO_PRESTAMO,
                    fondo=TipoFondo.AHORRO,
                    referencia=ReferenciaOrigen(TipoOrigen.PRESTAMO, prestamo.id),
                    descripcion="Desembolso de préstamo",
                    participante_id=prestamo.participante_id,
                ),
                autor,
            )
            self._prestamos.guardar(prestamo)
            self._uow.commit()
        return prestamo

    # --- RF-404 -------------------------------------------------------------
    def pagar(
        self, natillera_uuid: str, prestamo_uuid: str, monto: Dinero, hoy: date, autor: int
    ) -> ResultadoPago:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "COBRAR_CARTERA")
            prestamo = self._cargar(prestamo_uuid)
            desc = prestamo.registrar_pago(monto, hoy)
            assert prestamo.id is not None
            asientos: list[AsientoLeido] = []
            asiento_cap_id: int | None = None
            asiento_int_id: int | None = None
            if desc.capital.es_positivo():
                cap = self._contabilidad.registrar_asiento(
                    self._asiento(prestamo, desc.capital, ConceptoContable.RETORNO_CAPITAL,
                                  TipoFondo.AHORRO, TipoOrigen.PAGO_PRESTAMO,
                                  "Retorno de capital"),
                    autor,
                )
                asiento_cap_id = cap.id
                asientos.append(cap)
            if desc.interes.es_positivo():
                inte = self._contabilidad.registrar_asiento(
                    self._asiento(prestamo, desc.interes, ConceptoContable.INTERES_PAGADO,
                                  TipoFondo.RENTABILIDAD, TipoOrigen.PAGO_PRESTAMO,
                                  "Interés pagado"),
                    autor,
                )
                asiento_int_id = inte.id
                asientos.append(inte)
            self._pagos.registrar(
                prestamo.id, hoy, monto.monto, desc.capital.monto, desc.interes.monto,
                asiento_cap_id, asiento_int_id,
            )
            self._prestamos.guardar(prestamo)
            self._uow.commit()
        return ResultadoPago(desc, prestamo, asientos)

    # --- RF-405 -------------------------------------------------------------
    def detectar_mora(self, natillera_uuid: str, hoy: date) -> int:
        with self._uow:
            self._consulta.exigir_operacion(natillera_uuid, "COBRAR_CARTERA")
            marcados = 0
            for prestamo in self._prestamos.en_pago():
                if self._esta_en_mora(prestamo, hoy):
                    prestamo.marcar_mora()
                    self._prestamos.guardar(prestamo)
                    marcados += 1
            self._uow.commit()
        return marcados

    # --- helpers ------------------------------------------------------------
    def _asiento(
        self,
        prestamo: Prestamo,
        monto: Dinero,
        concepto: ConceptoContable,
        fondo: TipoFondo,
        origen: TipoOrigen,
        descripcion: str,
    ) -> Asiento:
        assert prestamo.id is not None
        return Asiento(
            monto=monto,
            naturaleza=Naturaleza.CREDITO,
            concepto=concepto,
            fondo=fondo,
            referencia=ReferenciaOrigen(origen, prestamo.id),
            descripcion=descripcion,
            participante_id=prestamo.participante_id,
        )

    def _exigir_saldo_ahorro(self, capital: Dinero) -> None:
        if self._contabilidad.saldo(TipoFondo.AHORRO) < capital:
            raise SaldoInsuficiente(
                "El Fondo de Ahorro no tiene saldo suficiente para el préstamo.",
                {
                    "saldo_disponible": self._contabilidad.saldo(TipoFondo.AHORRO).como_str(),
                    "capital": capital.como_str(),
                },
            )

    @staticmethod
    def _esta_en_mora(prestamo: Prestamo, hoy: date) -> bool:
        if prestamo.fecha_desembolso is None or prestamo.saldo_capital.es_cero():
            return False
        # Vencimiento simple: fecha de desembolso + plazo (en meses ~30 días).
        vencimiento = prestamo.fecha_desembolso.toordinal() + prestamo.plazo_meses * 30
        return hoy.toordinal() > vencimiento
