"""006 cuota por participante

Revision ID: 0006_cuota_por_participante
Revises: 0005_liquidacion
Create Date: 2026-07-14

Añade `participantes.valor_cuota` (cuota mensual propia, RF-301). Migración
aditiva y segura sobre datos existentes: la columna es NULL-able y NULL significa
"usar el valor por defecto de la configuración de la natillera".
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0006_cuota_por_participante'
down_revision: str | None = '0005_liquidacion'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "participantes",
        sa.Column("valor_cuota", sa.Numeric(precision=15, scale=2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("participantes", "valor_cuota")
