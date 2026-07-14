"""Importa todos los modelos ORM para poblar `ModeloBase.metadata`.

Alembic (autogenerate) y las pruebas que hacen `create_all` importan este módulo
para garantizar que todas las tablas estén registradas. A medida que cada sprint
agrega modelos, se añaden aquí.
"""

from __future__ import annotations

from app.modules.actividades.infrastructure import modelos as _actividades
from app.modules.contabilidad.infrastructure import modelos as _contabilidad
from app.modules.cuotas.infrastructure import modelos as _cuotas
from app.modules.liquidacion.infrastructure import modelos as _liquidacion
from app.modules.multas.infrastructure import modelos as _multas
from app.modules.natilleras.infrastructure import modelos as _natilleras
from app.modules.participantes.infrastructure import modelos as _participantes
from app.modules.prestamos.infrastructure import modelos as _prestamos
from app.shared.infrastructure import modelos_auditoria as _auditoria
from app.shared.infrastructure import modelos_auth as _auth
from app.shared.infrastructure import modelos_idempotencia as _idempotencia

__all__ = [
    "_actividades",
    "_auditoria",
    "_auth",
    "_contabilidad",
    "_cuotas",
    "_idempotencia",
    "_liquidacion",
    "_multas",
    "_natilleras",
    "_participantes",
    "_prestamos",
]
