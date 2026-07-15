"""008 interés acumulado del préstamo (interés simple por meses)

Revision ID: 0008_prestamo_interes
Revises: 0007_periodos_secuencia
Create Date: 2026-07-14

Agrega `prestamos.interes_acumulado` (interés devengado no pagado) y
`prestamos.fecha_ultimo_calculo` (fecha hasta la que se calculó el interés).
Aditiva; los préstamos existentes quedan con interés acumulado 0.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = '0008_prestamo_interes'
down_revision: str | None = '0007_periodos_secuencia'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "prestamos",
        sa.Column(
            "interes_acumulado",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "prestamos",
        sa.Column("fecha_ultimo_calculo", sa.Date(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("prestamos", "fecha_ultimo_calculo")
    op.drop_column("prestamos", "interes_acumulado")
