"""Guarda anti-float en el dominio (doc 08 §3, TEC-01).

Falla (exit 1) si encuentra una llamada real a `float(...)` en cualquier paquete
`domain/`. El dinero es `Decimal` de punta a punta; convertir a float en el
dominio es un defecto por definición.

Usa `tokenize` para analizar tokens reales: NO detecta la palabra "float" dentro
de strings o comentarios (p. ej. los mensajes de error de `Dinero` que
mencionan float para rechazarlo), ni `isinstance(x, float)` (eso no es una
llamada `float(`).

Uso:  python scripts/guard_anti_float.py
"""

from __future__ import annotations

import io
import sys
import token
import tokenize
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent / "app"


def _llamadas_float(codigo: str) -> list[int]:
    """Líneas con una llamada real `float(` (NAME 'float' seguido de OP '(')."""
    lineas: list[int] = []
    tokens = list(tokenize.generate_tokens(io.StringIO(codigo).readline))
    for i, tok in enumerate(tokens[:-1]):
        siguiente = tokens[i + 1]
        if (
            tok.type == token.NAME
            and tok.string == "float"
            and siguiente.type == token.OP
            and siguiente.string == "("
        ):
            lineas.append(tok.start[0])
    return lineas


def main() -> int:
    hallazgos: list[str] = []
    for archivo in RAIZ.rglob("*.py"):
        if "domain" not in archivo.parts:
            continue
        codigo = archivo.read_text(encoding="utf-8")
        for n in _llamadas_float(codigo):
            rel = archivo.relative_to(RAIZ.parent)
            hallazgos.append(f"{rel}:{n}")

    if hallazgos:
        print("GUARDA ANTI-FLOAT: llamada a float() en el dominio (TEC-01):")
        for h in hallazgos:
            print("  " + h)
        return 1
    print("Guarda anti-float: OK (sin float() en dominio).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
