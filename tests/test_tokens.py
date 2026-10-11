"""El núcleo: cada rol apunta a un color real y los pares de lectura contrastan."""
import re

import pytest

from nucleo import tokens as T

HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")


def luminancia(hx: str) -> float:
    canales = [int(hx[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in canales]
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contraste(a: str, b: str) -> float:
    claro, oscuro = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (claro + 0.05) / (oscuro + 0.05)


def test_cada_rol_apunta_a_un_color_de_la_paleta():
    t = T.tokens()
    for rol, nombre in t["roles"].items():
        assert nombre in t["paleta"], f"el rol {rol!r} apunta a {nombre!r}, que no existe"
        assert HEX.match(T.color(rol))


def test_series_son_hex_validos():
    for nombre, serie in T.tokens()["series"].items():
        for c in serie.values() if isinstance(serie, dict) else serie:
            assert HEX.match(c), f"{nombre}: {c!r}"


def test_rol_desconocido_falla_con_mensaje():
    with pytest.raises(KeyError, match="rol o color desconocido"):
        T.color("azul_cielo")


def test_paleta_hex_incluye_series_y_paleta():
    todos = T.paleta_hex()
    assert T.color("principal").upper() in todos
    assert all(c.upper() in todos for c in T.serie("secuencial"))


# Pares de texto/fondo que usan los adaptadores y el ejemplo. WCAG AA: 4,5:1 para
# texto normal; 3:1 para elementos gráficos (barras en neutro sobre el fondo).
PARES_TEXTO = [
    ("texto", "fondo"),
    ("texto_secundario", "fondo"),
    ("principal", "fondo"),            # la cifra del tablero
    ("principal_oscuro", "fondo"),     # el h1 del tablero
    ("#FFFFFF", "principal_oscuro"),   # encabezados de tabla y de Excel
    ("#FFFFFF", "bien"),               # pastilla y semáforo «En meta»
    ("#FFFFFF", "mal"),                # pastilla y semáforo «Crítico»
    ("texto", "acento"),               # pastilla «Alerta», celda destacada
    ("texto", "bien_claro"),
    ("texto", "mal_claro"),
    ("texto", "acento_claro"),
]


def _c(x: str) -> str:
    return x if x.startswith("#") else T.color(x)


@pytest.mark.parametrize(("frente", "fondo"), PARES_TEXTO)
def test_contraste_de_texto(frente, fondo):
    assert contraste(_c(frente), _c(fondo)) >= 4.5


def test_contraste_grafico_del_neutro():
    assert contraste(T.color("neutro"), T.color("fondo")) >= 3.0
