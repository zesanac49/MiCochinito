"""Repositorio y mappers de natilleras (doc 05 §2/§4).

Mapeo explícito entre el agregado `Natillera` (+ `Configuracion`) y sus modelos
ORM. La natillera es el tenant: este repo no filtra por natillera_id (opera a
nivel de plataforma), pero las membresías del usuario acotan qué ve la API.
"""

from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.natilleras.application.puertos import RepositorioNatilleras
from app.modules.natilleras.domain.configuracion import (
    Configuracion,
    EstrategiaDistribucion,
    Periodicidad,
)
from app.modules.natilleras.domain.estados import EstadoNatillera
from app.modules.natilleras.domain.natillera import Natillera
from app.modules.natilleras.infrastructure.modelos import (
    ConfiguracionHistorialModel,
    ConfiguracionModel,
    NatilleraModel,
)
from app.shared.domain.dinero import Dinero
from app.shared.infrastructure.modelos_auth import UsuarioNatilleraModel


def _config_a_modelo(cfg: Configuracion, modelo: ConfiguracionModel) -> None:
    modelo.valor_cuota = cfg.valor_cuota.monto
    modelo.periodicidad_cuota = cfg.periodicidad_cuota.value
    modelo.dia_limite_pago = cfg.dia_limite_pago
    modelo.permite_aportes_extra = cfg.permite_aportes_extra
    modelo.tasa_interes_base = cfg.tasa_interes_base
    modelo.tasa_interes_min = cfg.tasa_interes_min
    modelo.tasa_interes_max = cfg.tasa_interes_max
    modelo.max_prestamos_activos = cfg.max_prestamos_activos
    modelo.max_capital_vigente = cfg.max_capital_vigente.monto
    modelo.estrategia_distribucion = cfg.estrategia_distribucion.value


def _modelo_a_config(modelo: ConfiguracionModel) -> Configuracion:
    return Configuracion(
        valor_cuota=Dinero(modelo.valor_cuota),
        periodicidad_cuota=Periodicidad(modelo.periodicidad_cuota),
        dia_limite_pago=modelo.dia_limite_pago,
        permite_aportes_extra=modelo.permite_aportes_extra,
        tasa_interes_base=Decimal(modelo.tasa_interes_base),
        tasa_interes_min=Decimal(modelo.tasa_interes_min),
        tasa_interes_max=Decimal(modelo.tasa_interes_max),
        max_prestamos_activos=modelo.max_prestamos_activos,
        max_capital_vigente=Dinero(modelo.max_capital_vigente),
        estrategia_distribucion=EstrategiaDistribucion(modelo.estrategia_distribucion),
    )


class RepositorioNatillerasSQLAlchemy(RepositorioNatilleras):
    def __init__(self, session: Session) -> None:
        self._session = session

    def agregar(self, natillera: Natillera) -> Natillera:
        modelo = NatilleraModel(
            nombre=natillera.nombre,
            estado=natillera.estado.value,
            ciclo_inicio=natillera.ciclo_inicio,
            ciclo_fin=natillera.ciclo_fin,
        )
        self._session.add(modelo)
        self._session.flush()  # asigna id y uuid
        natillera._asignar_id(modelo.id)
        natillera.uuid = modelo.uuid
        if natillera.configuracion is not None:
            cfg_modelo = ConfiguracionModel(natillera_id=modelo.id)
            _config_a_modelo(natillera.configuracion, cfg_modelo)
            cfg_modelo.estrategia_congelada = natillera.estrategia_congelada
            self._session.add(cfg_modelo)
        return natillera

    def obtener_por_uuid(self, uuid: str) -> Natillera | None:
        modelo = self._session.scalar(
            select(NatilleraModel).where(NatilleraModel.uuid == uuid)
        )
        if modelo is None:
            return None
        return self._a_dominio(modelo)

    def guardar(self, natillera: Natillera) -> None:
        modelo = self._session.get(NatilleraModel, natillera.id)
        if modelo is None:
            raise ValueError("No se puede guardar una natillera inexistente.")
        modelo.estado = natillera.estado.value
        if natillera.configuracion is not None:
            cfg_modelo = self._session.scalar(
                select(ConfiguracionModel).where(
                    ConfiguracionModel.natillera_id == natillera.id
                )
            )
            if cfg_modelo is None:
                cfg_modelo = ConfiguracionModel(natillera_id=natillera.id)
                self._session.add(cfg_modelo)
            _config_a_modelo(natillera.configuracion, cfg_modelo)
            cfg_modelo.estrategia_congelada = natillera.estrategia_congelada

    def registrar_historial(
        self, natillera_id: int, snapshot: dict[str, object], autor_id: int
    ) -> None:
        self._session.add(
            ConfiguracionHistorialModel(
                natillera_id=natillera_id, snapshot=snapshot, autor_id=autor_id
            )
        )

    def listar(self) -> list[Natillera]:
        modelos = self._session.scalars(select(NatilleraModel)).all()
        return [self._a_dominio(m) for m in modelos]

    def listar_de_usuario(self, usuario_id: int) -> list[Natillera]:
        modelos = self._session.scalars(
            select(NatilleraModel)
            .join(
                UsuarioNatilleraModel,
                UsuarioNatilleraModel.natillera_id == NatilleraModel.id,
            )
            .where(UsuarioNatilleraModel.usuario_id == usuario_id)
        ).all()
        return [self._a_dominio(m) for m in modelos]

    def _a_dominio(self, modelo: NatilleraModel) -> Natillera:
        cfg_modelo = self._session.scalar(
            select(ConfiguracionModel).where(ConfiguracionModel.natillera_id == modelo.id)
        )
        configuracion = _modelo_a_config(cfg_modelo) if cfg_modelo is not None else None
        congelada = cfg_modelo.estrategia_congelada if cfg_modelo is not None else False
        return Natillera(
            nombre=modelo.nombre,
            ciclo_inicio=modelo.ciclo_inicio,
            ciclo_fin=modelo.ciclo_fin,
            estado=EstadoNatillera(modelo.estado),
            configuracion=configuracion,
            estrategia_congelada=congelada,
            id=modelo.id,
            uuid=modelo.uuid,
        )
