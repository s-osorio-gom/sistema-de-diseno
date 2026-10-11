#!/usr/bin/env python3
"""
tokens.py — la única fuente de verdad del sistema, legible desde Python.

    from nucleo import tokens as T
    T.color("principal")     # '#2F5DB8'
    T.serie("secuencial")    # ['#C6DBEF', …]
    T.pt("titulo")           # 32

Los adaptadores —HTML, Excel, gráficas, presentaciones— leen de aquí y de
ningún otro sitio. Un color escrito a mano en un adaptador es el principio de
que cada entregable se vea distinto.
"""
from __future__ import annotations

import json
from functools import cache
from pathlib import Path

NUCLEO = Path(__file__).resolve().parent


@cache
def _cargar(nombre: str) -> dict:
    return json.loads((NUCLEO / nombre).read_text(encoding="utf-8"))


def tokens() -> dict:
    return _cargar("tokens.json")


def reglas() -> dict:
    return _cargar("reglas.json")


def color(rol: str) -> str:
    """Color por ROL ('principal', 'acento', 'mal'), no por nombre de color.

    Pedir 'azul' amarra el código al color de hoy. Pedir 'principal' sobrevive
    a un cambio de marca: se edita tokens.json y todo lo demás sigue igual.
    """
    t = tokens()
    if rol in t["roles"]:
        return t["paleta"][t["roles"][rol]]
    if rol in t["paleta"]:
        return t["paleta"][rol]
    raise KeyError(f"rol o color desconocido: {rol!r}. "
                   f"Roles: {', '.join(sorted(t['roles']))}")


def serie(nombre: str = "categorica"):
    return tokens()["series"][nombre]


def pt(nivel: str) -> int:
    return tokens()["tipografia"]["escala"][nivel]["pt"]


def peso(nivel: str) -> int:
    return tokens()["tipografia"]["escala"][nivel]["peso"]


def familia(con_respaldo: bool = True) -> str:
    t = tokens()["tipografia"]
    return f"'{t['familia']}', {t['respaldo']}" if con_respaldo else t["familia"]


def paleta_hex() -> set[str]:
    """Todos los colores admitidos, en mayúscula. Lo que audita el verificador."""
    return {v.upper() for v in tokens()["paleta"].values()} | {
        c.upper() for s in tokens()["series"].values()
        for c in (s.values() if isinstance(s, dict) else s)}
