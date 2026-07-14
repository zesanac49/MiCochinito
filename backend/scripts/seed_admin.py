"""Crea el usuario administrador inicial si no existe (idempotente).

En producción la app NO tiene auto-registro, así que se necesita al menos un
usuario para el primer ingreso. Este usuario no tiene natillera: al entrar, crea
la suya desde la interfaz y queda como ADMINISTRADOR (auto-membresía, RF-1002).

Variables de entorno:
  ADMIN_EMAIL     (por defecto: admin@natillera.co)
  ADMIN_PASSWORD  (obligatoria; si falta, no crea nada y avisa)

Uso:  DATABASE_URL=... PYTHONPATH=. python scripts/seed_admin.py
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.shared.infrastructure.todos_los_modelos  # noqa: F401  (puebla metadata)
from app.core.config import get_settings
from app.core.security import hashear_password
from app.shared.infrastructure.modelos_auth import UsuarioModel


def sembrar() -> None:
    email = os.environ.get("ADMIN_EMAIL", "admin@natillera.co").strip()
    password = os.environ.get("ADMIN_PASSWORD", "").strip()

    if not password:
        print("[seed-admin] ADMIN_PASSWORD no definido; no se crea el administrador.")
        return

    engine = create_engine(get_settings().database_url)
    with Session(engine) as session:
        if session.query(UsuarioModel).filter_by(email=email).first() is not None:
            print(f"[seed-admin] El usuario {email} ya existe; nada que hacer.")
            return
        session.add(
            UsuarioModel(
                email=email,
                hash_password=hashear_password(password),
                nombre="Administrador",
                activo=True,
            )
        )
        session.commit()
        print(f"[seed-admin] Administrador creado: {email}")


if __name__ == "__main__":
    sembrar()
