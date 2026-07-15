"""Casos límite de RBAC y aislamiento multi-tenant sobre endpoints reales.

Complementa `tests/api/test_rbac.py` y `tests/integration/test_rbac_supervisor.py`
con una batería exhaustiva y parametrizada (doc 05 §6, RF-1001/1002, TEC-02):

- **Matriz de permisos**: para endpoints representativos de cada módulo, verifica
  el código HTTP esperado por rol (sin token → 401; token válido sin membresía →
  403; CLIENTE/ SUPERVISOR / ADMINISTRADOR según el `require_rol` real del router).
  Los roles exactos se leyeron del código, no se asumieron.
- **Token**: encabezado ausente, esquema inválido, token basura y firma mala → 401.
- **Tenancy**: un ADMINISTRADOR del tenant A no puede ver ni operar recursos del
  tenant B (403 al cruzar de natillera, 404 al referenciar un uuid de otro tenant).
- **Gestión de usuarios (RF-1002)**: último administrador, CLIENTE↔participante,
  miembro duplicado y no-admin no gestiona.
- **Validación (422)**: cuerpos malformados / campos faltantes en varios POST/PUT.

SQLite en memoria (sin aritmética monetaria; permitido por doc 05 §9). La
autorización (`require_rol`) se evalúa como dependencia antes del cuerpo del
endpoint, por lo que basta con cuerpos válidos de esquema para que el 401/403
aflore aun cuando el recurso referenciado no exista.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.security import crear_access_token
from tests.conftest import (
    SETTINGS,
    bearer,
    crear_membresia,
    crear_natillera,
    crear_usuario,
)

# --- Cuerpos válidos de esquema (para que aflore la autorización, no un 422) ---

_PART = {
    "nombre": "Ana Pérez",
    "tipo_documento": "CC",
    "numero_documento": "1020304050",
    "fecha_ingreso": "2026-01-15",
}
_CONFIG = {
    "valor_cuota": "50000.00",
    "periodicidad_cuota": "MENSUAL",
    "dia_limite_pago": 5,
    "permite_aportes_extra": True,
    "tasa_interes_base": "2.0",
    "tasa_interes_min": "1.0",
    "tasa_interes_max": "3.0",
    "max_prestamos_activos": 2,
    "max_capital_vigente": "2000000.00",
    "estrategia_distribucion": "PROPORCIONAL_AHORRO",
}
_PRESTAMO = {"participante_uuid": "x", "capital": "100000", "tasa": "2", "plazo_meses": 6}
_MIEMBRO = {
    "nombre": "Nuevo Miembro",
    "email": "nuevo@natillera.co",
    "password": "clave12345",
    "rol": "SUPERVISOR",
}

# Clase de cada endpoint según el `require_rol` REAL del router (leído del código):
#   MIEMBRO   -> ADMINISTRADOR, SUPERVISOR, CLIENTE
#   ADMIN_SUP -> ADMINISTRADOR, SUPERVISOR
#   ADMIN     -> ADMINISTRADOR
# Formato: (clase, método, sufijo_bajo_/natilleras/{uuid}, cuerpo_json_o_None)
ENDPOINTS: list[tuple[str, str, str, dict | None]] = [
    # natilleras (obtener) + actividades de lectura => MIEMBRO
    ("MIEMBRO", "GET", "", None),
    ("MIEMBRO", "GET", "/actividades", None),
    # participantes
    ("ADMIN_SUP", "GET", "/participantes", None),
    ("ADMIN_SUP", "POST", "/participantes", _PART),
    # cuotas / aportes
    ("ADMIN_SUP", "POST", "/cuotas/pagos", {"participante_uuid": "x", "periodo_uuid": "y"}),
    ("ADMIN_SUP", "POST", "/aportes-extraordinarios", {"participante_uuid": "x", "monto": "1000"}),
    (
        "ADMIN_SUP",
        "POST",
        "/cuotas/pagos-lote",
        {"items": [{"participante_uuid": "x", "periodo_uuid": "y"}]},
    ),
    # préstamos
    ("ADMIN_SUP", "GET", "/prestamos", None),
    ("ADMIN_SUP", "POST", "/prestamos", _PRESTAMO),
    # multas
    ("ADMIN_SUP", "GET", "/multas", None),
    ("ADMIN_SUP", "POST", "/multas", {"participante_uuid": "x", "motivo": "Llegó tarde"}),
    ("ADMIN_SUP", "GET", "/catalogo-multas", None),
    ("ADMIN_SUP", "POST", "/catalogo-multas", {"nombre": "Mora", "tipo": "OTRA", "valor": "1000"}),
    # actividades (creación)
    ("ADMIN_SUP", "POST", "/actividades", {"tipo": "POLLA", "nombre": "P", "periodo_uuid": "x"}),
    # reportes / contabilidad
    ("ADMIN_SUP", "GET", "/asientos", None),
    ("ADMIN_SUP", "GET", "/fondos", None),
    ("ADMIN_SUP", "GET", "/dashboard", None),
    ("ADMIN_SUP", "GET", "/periodos", None),
    ("ADMIN_SUP", "POST", "/reconciliacion", None),
    # natillera config / transición
    ("ADMIN_SUP", "POST", "/transiciones", {"a": "ABIERTA"}),
    ("ADMIN_SUP", "PUT", "/configuracion", _CONFIG),
    ("ADMIN_SUP", "POST", "/periodos/regenerar", None),
    # liquidación (lectura ADMIN_SUP, operación ADMIN)
    ("ADMIN_SUP", "GET", "/liquidacion", None),
    ("ADMIN_SUP", "GET", "/liquidacion/acta", None),
    ("ADMIN", "POST", "/liquidacion", None),
    ("ADMIN", "POST", "/liquidacion/calculo", None),
    ("ADMIN", "POST", "/liquidacion/confirmacion", {"nombre_natillera": "Los Ahorradores"}),
    # gestión de usuarios (RF-1002)
    ("ADMIN_SUP", "GET", "/miembros", None),
    ("ADMIN", "POST", "/miembros", _MIEMBRO),
]

ACTORES = ("sin_token", "foraneo", "cliente", "supervisor", "admin")

_ALLOW = {
    "MIEMBRO": {"cliente", "supervisor", "admin"},
    "ADMIN_SUP": {"supervisor", "admin"},
    "ADMIN": {"admin"},
}


def _esperado(clase: str, actor: str) -> str:
    if actor == "sin_token":
        return "401"
    if actor == "foraneo":
        return "403"
    return "allow" if actor in _ALLOW[clase] else "403"


_CASOS = [
    (clase, metodo, sufijo, body, actor)
    for (clase, metodo, sufijo, body) in ENDPOINTS
    for actor in ACTORES
]
_IDS = [
    f"{clase}-{metodo}{sufijo or '/'}-{actor}"
    for (clase, metodo, sufijo, body, actor) in _CASOS
]


@pytest.fixture()
def entorno(client: TestClient, session: Session) -> tuple[str, dict[str, dict[str, str]]]:
    """Una natillera con un usuario por rol, más un foráneo sin membresía."""
    nat = crear_natillera(session)
    admin = crear_usuario(session, email="adm@natillera.co")
    sup = crear_usuario(session, email="sup@natillera.co")
    cli = crear_usuario(session, email="cli@natillera.co")
    foraneo = crear_usuario(session, email="foraneo@natillera.co")
    crear_membresia(session, admin.id, nat.id, rol="ADMINISTRADOR")
    crear_membresia(session, sup.id, nat.id, rol="SUPERVISOR")
    crear_membresia(session, cli.id, nat.id, rol="CLIENTE")
    session.commit()
    headers = {
        "sin_token": {},
        "foraneo": bearer(foraneo.uuid),
        "cliente": bearer(cli.uuid),
        "supervisor": bearer(sup.uuid),
        "admin": bearer(admin.uuid),
    }
    return nat.uuid, headers


# --- 1. Matriz de permisos -------------------------------------------------


@pytest.mark.parametrize("clase,metodo,sufijo,body,actor", _CASOS, ids=_IDS)
def test_matriz_permisos(
    entorno: tuple[str, dict[str, dict[str, str]]],
    client: TestClient,
    clase: str,
    metodo: str,
    sufijo: str,
    body: dict | None,
    actor: str,
) -> None:
    nat, headers = entorno
    url = f"/api/v1/natilleras/{nat}{sufijo}"
    resp = client.request(metodo, url, json=body, headers=headers[actor])
    esperado = _esperado(clase, actor)

    if esperado == "401":
        assert resp.status_code == 401, resp.text
        assert resp.json()["error"]["codigo"] == "NO_AUTENTICADO"
    elif esperado == "403":
        assert resp.status_code == 403, resp.text
        assert resp.json()["error"]["codigo"] in {"PROHIBIDO", "SIN_MEMBRESIA"}
    else:  # allow: la autorización pasó (el resultado de negocio no es 401/403)
        assert resp.status_code not in (401, 403), (url, actor, resp.status_code, resp.text)


# --- 2. Autenticación / token --------------------------------------------


def _url(nat: str) -> str:
    return f"/api/v1/natilleras/{nat}/participantes"


def test_sin_encabezado_authorization(client: TestClient, session: Session) -> None:
    nat = crear_natillera(session)
    session.commit()
    resp = client.get(_url(nat.uuid))
    assert resp.status_code == 401
    assert resp.json()["error"]["codigo"] == "NO_AUTENTICADO"


@pytest.mark.parametrize(
    "valor",
    [
        "Basic dXNlcjpwYXNz",  # esquema inválido (no Bearer)
        "Bearer esto-no-es-un-jwt",  # token basura
        "Bearer ",  # Bearer sin token
        "token-sin-esquema",  # sin esquema
    ],
    ids=["basic", "basura", "bearer_vacio", "sin_esquema"],
)
def test_authorization_invalido_es_401(client: TestClient, session: Session, valor: str) -> None:
    nat = crear_natillera(session)
    session.commit()
    resp = client.get(_url(nat.uuid), headers={"Authorization": valor})
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_token_firma_invalida_es_401(client: TestClient, session: Session) -> None:
    nat = crear_natillera(session)
    session.commit()
    otro = Settings(
        entorno="test",
        log_json=False,
        jwt_secret="OTRO-secreto-distinto-pero-igual-de-largo-0987654321",
    )
    token = crear_access_token(otro, "cualquier-uuid")  # firmado con la clave equivocada
    resp = client.get(_url(nat.uuid), headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["codigo"] == "NO_AUTENTICADO"


def test_token_expirado_es_401(client: TestClient, session: Session) -> None:
    nat = crear_natillera(session)
    usuario = crear_usuario(session)
    session.commit()

    def _hace_una_hora() -> datetime:
        return datetime.now(UTC) - timedelta(hours=1)

    token = crear_access_token(SETTINGS, usuario.uuid, ahora=_hace_una_hora)
    resp = client.get(_url(nat.uuid), headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 401, resp.text
    assert resp.json()["error"]["codigo"] in {"NO_AUTENTICADO", "TOKEN_EXPIRADO"}


# --- 3. Tenancy (aislamiento multi-tenant) --------------------------------


def _dos_tenants(session: Session) -> tuple[str, dict[str, str], str, dict[str, str]]:
    """Crea A y B con un administrador propio cada uno. Devuelve uuids y headers."""
    nat_a = crear_natillera(session, nombre="Natillera A")
    nat_b = crear_natillera(session, nombre="Natillera B")
    admin_a = crear_usuario(session, email="admin.a@natillera.co")
    admin_b = crear_usuario(session, email="admin.b@natillera.co")
    crear_membresia(session, admin_a.id, nat_a.id, rol="ADMINISTRADOR")
    crear_membresia(session, admin_b.id, nat_b.id, rol="ADMINISTRADOR")
    session.commit()
    return nat_a.uuid, bearer(admin_a.uuid), nat_b.uuid, bearer(admin_b.uuid)


@pytest.mark.parametrize(
    "metodo,sufijo,body",
    [
        ("GET", "", None),
        ("GET", "/participantes", None),
        ("POST", "/participantes", _PART),
        ("GET", "/prestamos", None),
        ("GET", "/multas", None),
        ("GET", "/asientos", None),
        ("POST", "/transiciones", {"a": "ABIERTA"}),
        ("POST", "/liquidacion", None),
        ("GET", "/miembros", None),
    ],
    ids=[
        "obtener",
        "listar_part",
        "crear_part",
        "listar_prest",
        "listar_multas",
        "asientos",
        "transicion",
        "liquidacion",
        "miembros",
    ],
)
def test_admin_de_A_no_opera_en_B(
    client: TestClient, session: Session, metodo: str, sufijo: str, body: dict | None
) -> None:
    """El ADMIN de A no tiene membresía en B => 403 al operar sobre el tenant B."""
    _nat_a, head_a, nat_b, _head_b = _dos_tenants(session)
    resp = client.request(metodo, f"/api/v1/natilleras/{nat_b}{sufijo}", json=body, headers=head_a)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["codigo"] in {"PROHIBIDO", "SIN_MEMBRESIA"}


def test_recurso_de_otro_tenant_no_es_visible(client: TestClient, session: Session) -> None:
    """Referenciar el uuid de un participante de B bajo la URL de A => 404 (repo por tenant)."""
    nat_a, head_a, nat_b, head_b = _dos_tenants(session)
    creado = client.post(f"/api/v1/natilleras/{nat_b}/participantes", json=_PART, headers=head_b)
    assert creado.status_code == 201, creado.text
    uuid_b = creado.json()["uuid"]

    # El admin de A pide, bajo su propia natillera, un participante que es de B.
    resp = client.get(
        f"/api/v1/natilleras/{nat_a}/participantes/{uuid_b}", headers=head_a
    )
    assert resp.status_code == 404, resp.text
    assert resp.json()["error"]["codigo"] == "NO_ENCONTRADO"


def test_admin_de_A_no_lee_recurso_por_uuid_de_B_en_su_natillera(
    client: TestClient, session: Session
) -> None:
    """Aun con membresía en A, un participante de A no existe con el uuid de B."""
    nat_a, head_a, nat_b, head_b = _dos_tenants(session)
    # A tiene su propio participante; B tiene el suyo.
    client.post(f"/api/v1/natilleras/{nat_a}/participantes", json=_PART, headers=head_a)
    otro = dict(_PART, numero_documento="9999999999")
    creado_b = client.post(f"/api/v1/natilleras/{nat_b}/participantes", json=otro, headers=head_b)
    uuid_b = creado_b.json()["uuid"]

    # Cruzar el uuid de B en la natillera A: no se encuentra (aislamiento por tenant).
    resp = client.get(f"/api/v1/natilleras/{nat_a}/participantes/{uuid_b}", headers=head_a)
    assert resp.status_code == 404, resp.text


# --- 4. Gestión de usuarios (RF-1002) -------------------------------------


def _admin_seed(session: Session) -> tuple[str, str, dict[str, str]]:
    usuario = crear_usuario(session, email="jefe@natillera.co")
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="ADMINISTRADOR")
    session.commit()
    return nat.uuid, usuario.uuid, bearer(usuario.uuid)


def test_no_quitar_ultimo_administrador(client: TestClient, session: Session) -> None:
    nat, admin_uuid, h = _admin_seed(session)
    resp = client.delete(f"/api/v1/natilleras/{nat}/miembros/{admin_uuid}", headers=h)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["codigo"] == "ULTIMO_ADMINISTRADOR"


def test_no_degradar_ultimo_administrador(client: TestClient, session: Session) -> None:
    nat, admin_uuid, h = _admin_seed(session)
    resp = client.patch(
        f"/api/v1/natilleras/{nat}/miembros/{admin_uuid}",
        json={"rol": "SUPERVISOR"},
        headers=h,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["codigo"] == "ULTIMO_ADMINISTRADOR"


def test_cliente_requiere_participante(client: TestClient, session: Session) -> None:
    nat, _admin_uuid, h = _admin_seed(session)
    resp = client.post(
        f"/api/v1/natilleras/{nat}/miembros",
        json={
            "nombre": "Cliente Suelto",
            "email": "suelto@natillera.co",
            "password": "clave12345",
            "rol": "CLIENTE",
        },
        headers=h,
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["codigo"] == "CLIENTE_REQUIERE_PARTICIPANTE"


def test_miembro_duplicado(client: TestClient, session: Session) -> None:
    nat, _admin_uuid, h = _admin_seed(session)
    cuerpo = {
        "nombre": "Repetido",
        "email": "rep@natillera.co",
        "password": "clave12345",
        "rol": "SUPERVISOR",
    }
    assert (
        client.post(f"/api/v1/natilleras/{nat}/miembros", json=cuerpo, headers=h).status_code == 201
    )
    resp = client.post(f"/api/v1/natilleras/{nat}/miembros", json=cuerpo, headers=h)
    assert resp.status_code == 409, resp.text
    assert resp.json()["error"]["codigo"] == "MIEMBRO_YA_EXISTE"


def test_supervisor_no_gestiona_usuarios(client: TestClient, session: Session) -> None:
    usuario = crear_usuario(session, email="sup2@natillera.co")
    nat = crear_natillera(session)
    crear_membresia(session, usuario.id, nat.id, rol="SUPERVISOR")
    session.commit()
    h = bearer(usuario.uuid)
    # Puede listar (ADMIN_SUP)...
    assert client.get(f"/api/v1/natilleras/{nat.uuid}/miembros", headers=h).status_code == 200
    # ...pero no agregar (solo ADMIN).
    resp = client.post(f"/api/v1/natilleras/{nat.uuid}/miembros", json=_MIEMBRO, headers=h)
    assert resp.status_code == 403, resp.text
    assert resp.json()["error"]["codigo"] == "PROHIBIDO"


def test_cliente_solo_ve_su_propia_cuenta(client: TestClient, session: Session) -> None:
    """RF-203: el CLIENTE puede ver su cuenta pero no la de otro participante."""
    from app.modules.participantes.infrastructure.modelos import ParticipanteModel
    from app.shared.infrastructure.modelos_auth import UsuarioNatilleraModel

    nat, _admin_uuid, h = _admin_seed(session)
    creado = client.post(f"/api/v1/natilleras/{nat}/participantes", json=_PART, headers=h)
    part_uuid = creado.json()["uuid"]
    part = session.query(ParticipanteModel).filter_by(uuid=part_uuid).one()

    # Cliente vinculado a ese participante (la membresía lleva participante_id).
    cli = crear_usuario(session, email="cliente.cuenta@natillera.co")
    membresia = crear_membresia(session, cli.id, part.natillera_id, rol="CLIENTE")
    assert isinstance(membresia, UsuarioNatilleraModel)
    membresia.participante_id = part.id
    session.commit()
    hc = bearer(cli.uuid)

    # Su propia cuenta: permitido.
    propia = client.get(
        f"/api/v1/natilleras/{nat}/participantes/{part_uuid}/cuenta", headers=hc
    )
    assert propia.status_code == 200, propia.text
    # La cuenta de otro uuid: prohibido (403).
    ajena = client.get(
        f"/api/v1/natilleras/{nat}/participantes/otro-uuid-cualquiera/cuenta", headers=hc
    )
    assert ajena.status_code == 403, ajena.text
    assert ajena.json()["error"]["codigo"] == "PROHIBIDO"


# --- 5. Validación (422) --------------------------------------------------


# Validación de dinero malformado (capital/tasa/monto/valor): el handler de
# RequestValidationError serializa los errores con jsonable_encoder, así que un
# field_validator que lanza ValueError responde 422 VALIDACION (no 500).
@pytest.mark.parametrize(
    "metodo,sufijo,body",
    [
        pytest.param(
            "POST", "/participantes", {"tipo_documento": "CC", "numero_documento": "1"},
            id="part_sin_nombre",
        ),
        pytest.param(
            "POST", "/participantes", dict(_PART, tipo_documento="XX"), id="part_tipo_doc"
        ),
        pytest.param(
            "POST", "/participantes", dict(_PART, fecha_ingreso="no-es-fecha"), id="part_fecha"
        ),
        pytest.param("POST", "/prestamos", dict(_PRESTAMO, plazo_meses=0), id="prest_plazo0"),
        pytest.param(
            "POST", "/prestamos", dict(_PRESTAMO, capital="-100"),
            id="prest_capital_neg",
        ),
        pytest.param(
            "POST", "/prestamos", dict(_PRESTAMO, tasa="abc"),
            id="prest_tasa",
        ),
        pytest.param(
            "POST", "/aportes-extraordinarios", {"participante_uuid": "x", "monto": "0"},
            id="aporte_monto0",
        ),
        pytest.param(
            "POST", "/multas", {"participante_uuid": "x", "motivo": ""}, id="multa_motivo_vacio"
        ),
        pytest.param(
            "POST", "/catalogo-multas", {"nombre": "M", "tipo": "OTRA", "valor": "0"},
            id="catalogo_valor0",
        ),
        pytest.param(
            "POST", "/actividades", {"tipo": "POLLA", "periodo_uuid": "x"}, id="act_sin_nombre"
        ),
        pytest.param(
            "POST", "/transiciones", {"a": "ESTADO_INEXISTENTE"}, id="transicion_enum"
        ),
        pytest.param("PUT", "/configuracion", {"valor_cuota": "1000"}, id="config_incompleta"),
        pytest.param("POST", "/cuotas/pagos", {"participante_uuid": "x"}, id="cuota_sin_periodo"),
        pytest.param("POST", "/cuotas/pagos-lote", {"items": []}, id="lote_vacio"),
        pytest.param(
            "POST", "/miembros", dict(_MIEMBRO, password="corta"), id="miembro_pass_corta"
        ),
        pytest.param(
            "POST", "/miembros", dict(_MIEMBRO, rol="ROL_RARO"), id="miembro_rol_invalido"
        ),
    ],
)
def test_cuerpos_malformados_devuelven_422(
    client: TestClient, session: Session, metodo: str, sufijo: str, body: dict
) -> None:
    nat, _admin_uuid, h = _admin_seed(session)
    resp = client.request(metodo, f"/api/v1/natilleras/{nat}{sufijo}", json=body, headers=h)
    assert resp.status_code == 422, resp.text
    assert resp.json()["error"]["codigo"] == "VALIDACION"
