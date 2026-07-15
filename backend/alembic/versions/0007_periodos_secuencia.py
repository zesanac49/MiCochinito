"""007 secuencia de sub-período (periodicidad quincenal/semanal)

Revision ID: 0007_periodos_secuencia
Revises: 0006_cuota_por_participante
Create Date: 2026-07-14

Agrega `periodos.secuencia` y cambia el índice único a
(natillera, anio, mes, secuencia), para permitir varios sub-períodos por mes
(quincenal=2, semanal=4). Los períodos existentes quedan con secuencia=1.
Usa batch_alter_table para ser compatible con MySQL y SQLite.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0007_periodos_secuencia'
down_revision: str | None = '0006_cuota_por_participante'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("periodos") as batch:
        batch.add_column(
            sa.Column("secuencia", sa.SmallInteger(), nullable=False, server_default="1")
        )
        batch.drop_constraint("uq_periodo", type_="unique")
        batch.create_unique_constraint(
            "uq_periodo", ["natillera_id", "anio", "mes", "secuencia"]
        )


def downgrade() -> None:
    with op.batch_alter_table("periodos") as batch:
        batch.drop_constraint("uq_periodo", type_="unique")
        batch.create_unique_constraint("uq_periodo", ["natillera_id", "anio", "mes"])
        batch.drop_column("secuencia")
