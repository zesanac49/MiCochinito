"""009 valor de mora en la configuración (mora de cuotas de ahorro)

Revision ID: 0009_config_valor_mora
Revises: 0008_prestamo_interes
Create Date: 2026-07-14

Agrega `configuraciones.valor_mora` (mora fija por semana de atraso de una cuota
de ahorro). Aditiva; las configuraciones existentes quedan con 0 (sin mora).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0009_config_valor_mora'
down_revision: str | None = '0008_prestamo_interes'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "configuraciones",
        sa.Column(
            "valor_mora",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("configuraciones", "valor_mora")
