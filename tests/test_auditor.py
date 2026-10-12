"""El auditor: muerde el defectuoso, deja pasar el conforme y no confunde un
fallo propio con un hallazgo."""
import colorsys
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from adaptadores.html import auditar_html as A
from nucleo import tokens as T

RAIZ = Path(__file__).resolve().parents[1]
AUDITOR = RAIZ / "adaptadores" / "html" / "auditar_html.py"
DEFECTUOSO = RAIZ / "ejemplo" / "tablero_con_defectos.html"


def con_tokens(html: str) -> str:
    """Sustituye {{rol}} por el color del rol en tokens.json, en la notación
    pedida: {{rol}} #RRGGBB · :min minúsculas · :alfa #RRGGBB80 · :rgb rgb(r g b)
    · :rgbc rgb(r, g, b) · :rgba rgba(r,g,b,.5) · :hsl hsl(h s% l%)."""
    def uno(m):
        hx = T.color(m.group(1))
        r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
        h, luz, sat = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)
        return {None: hx, "min": hx.lower(), "alfa": hx + "80",
                "rgb": f"rgb({r} {g} {b})", "rgba": f"rgba({r},{g},{b},.5)",
                "rgbc": f"rgb({r}, {g}, {b})",
                "hsl": f"hsl({h * 360:.1f}deg {sat * 100:.1f}% {luz * 100:.1f}%)",
                }[m.group(2)]
    return re.sub(r"\{\{(\w+)(?::(\w+))?\}\}", uno, html)


def correr(*args) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(AUDITOR), *map(str, args)],
                          capture_output=True, text=True, encoding="utf-8", check=False)


def reglas_de(ruta: Path) -> set[str]:
    A.revisar(ruta)
    return {regla for regla, _ in A.hallazgos}


def test_defectuoso_devuelve_1():
    assert correr(DEFECTUOSO).returncode == 1


def test_los_once_defectos_marcados_se_reportan():
    hallados = reglas_de(DEFECTUOSO)
    esperados = {
        "no se usa Inter",                                   # 1
        "color fuera de la paleta",                          # 2, 3
        "se usa box-shadow",                                 # 4
        "se usa linear-gradient",                            # 5
        "título que nombra en vez de afirmar",               # 6
        "separador de miles equivocado",                     # 7
        "aparece «COP»",                                     # 8
        "separador decimal equivocado en un porcentaje",     # 9
        "falta el espacio antes del %",                      # 10
        "aparece «MM»",                                      # 11
    }
    assert esperados <= hallados, esperados - hallados
    colores = {d for r, d in A.hallazgos if r == "color fuera de la paleta"}
    assert {"#EFEFEF", "#333333"} <= colores


def test_el_detalle_muestra_la_cifra_completa():
    A.revisar(DEFECTUOSO)
    detalles = [d for r, d in A.hallazgos if "%" in r or "porcentaje" in r]
    assert any(d.startswith("76.2%") for d in detalles), detalles


def test_rgb_de_la_paleta_no_se_reporta(tmp_path):
    # El color sale de los tokens: con otra marca la prueba sigue midiendo lo
    # mismo (antes leía un rgb fijo del ejemplo y fallaba al cambiar la paleta).
    f = tmp_path / "x.html"
    f.write_text(con_tokens("<style id='casa'>body{font-family:Inter}"
                            "h1{color:{{principal:rgb}}} p{color:{{texto:rgba}}}"
                            "h2{color:{{principal_oscuro:rgbc}}}"
                            ".caja{border-color:rgba(0,0,0,.2)}</style>"
                            "<h1>Norte supera la meta</h1>"), encoding="utf-8")
    assert reglas_de(f) == set()
    assert A.sin_leer == []          # se leyeron, no se dejaron pasar sin leer


def test_revisar_dos_veces_no_acumula():
    A.revisar(DEFECTUOSO)
    n = len(A.hallazgos)
    A.revisar(DEFECTUOSO)
    assert len(A.hallazgos) == n


def test_archivo_inexistente_devuelve_2(tmp_path):
    r = correr(tmp_path / "no_existe.html")
    assert r.returncode == 2
    assert "No existe" in r.stderr


def test_directorio_devuelve_2(tmp_path):
    assert correr(tmp_path).returncode == 2


def test_style_sin_cerrar_se_reporta(tmp_path):
    roto = tmp_path / "roto.html"
    roto.write_text("<html><head><style id='casa'>body{color:#123456}"
                    "</head><body><h1>Oriente cae</h1></body></html>", encoding="utf-8")
    assert "HTML malformado" in reglas_de(roto)
    assert correr(roto).returncode == 1


def test_bytes_no_utf8_no_tumban_el_auditor(tmp_path):
    raro = tmp_path / "latin1.html"
    raro.write_bytes("<h1>Región Norte supera la meta</h1>".encode("latin-1"))
    assert correr(raro).returncode in (0, 1)


@pytest.mark.parametrize(("css", "regla"), [
    ("background: radial-gradient(#FFFFFF, #000000);", "se usa radial-gradient"),
    ("text-shadow: 1px 1px #000000;", "se usa text-shadow"),
    ("color: rgb(1, 2, 3);", "rgb() fuera de la paleta"),
])
def test_reglas_de_diseno_y_color(tmp_path, css, regla):
    f = tmp_path / "x.html"
    f.write_text(f"<style id='casa'>body{{font-family:Inter; {css}}}</style>"
                 "<h1>Norte supera la meta</h1>", encoding="utf-8")
    assert regla in reglas_de(f)


def test_sombra_none_no_es_hallazgo(tmp_path):
    f = tmp_path / "x.html"
    f.write_text("<style id='casa'>body{font-family:Inter; box-shadow:none}</style>"
                 "<h1>Norte supera la meta</h1>", encoding="utf-8")
    assert reglas_de(f) == set()


# HTML válido escrito de formas distintas a como lo escribe el ejemplo: ninguno
# puede producir hallazgos. Un falso positivo enseña a ignorar el reporte.
VALIDOS = sorted((RAIZ / "tests" / "html" / "validos").glob("*.html"))


@pytest.mark.parametrize("ruta", VALIDOS, ids=[r.stem for r in VALIDOS])
def test_html_valido_no_da_hallazgos(ruta, tmp_path):
    # Los colores van como {{rol}} para que la prueba valga con cualquier marca.
    f = tmp_path / ruta.name
    f.write_text(con_tokens(ruta.read_text(encoding="utf-8")), encoding="utf-8")
    A.revisar(f)
    assert A.hallazgos == []
    assert correr(f).returncode == 0


# Cada archivo de tests/html/defectos lleva defectos que el ejemplo no tiene.
# archivo -> {regla: detalles que deben aparecer (vacío = basta la regla)}
DEFECTOS = {
    "color_en_hover_y_media": {"color fuera de la paleta": {"#123456", "#ABCDEF"}},
    "hex_invalido": {"color fuera de la paleta": {"#1B243"}},
    "familia_solo_en_el_texto": {"no se usa Inter": set()},
    "color_con_nombre": {"color con nombre fuera de la paleta": {"darkslategray",
                                                                "lightyellow"}},
    "hsl": {"hsl() fuera de la paleta": set()},
    "rgb_en_porcentaje": {"rgb() fuera de la paleta": {"rgb(255, 0, 0)"}},
    "estilo_en_linea_y_svg": {"color fuera de la paleta": {"#FF00FF", "#123456", "#00FF00"}},
    "atributos_sin_comillas": {"color fuera de la paleta": {"#FF0000", "#00FF00"}},
    "hsl_en_radianes": {"hsl() fuera de la paleta": set()},
    "nombre_en_filter_y_background_image": {
        "color con nombre fuera de la paleta": {"red", "tomato", "olive"}},
}


@pytest.mark.parametrize(("nombre", "esperado"), DEFECTOS.items(), ids=list(DEFECTOS))
def test_html_con_defectos_se_detecta(nombre, esperado):
    ruta = RAIZ / "tests" / "html" / "defectos" / f"{nombre}.html"
    A.revisar(ruta)
    for regla, detalles in esperado.items():
        hallados = {d for r, d in A.hallazgos if r == regla}
        assert hallados, f"{regla!r} no se reportó: {A.hallazgos}"
        assert detalles <= hallados, detalles - hallados
    assert correr(ruta).returncode == 1


def test_cada_archivo_de_defectos_tiene_su_expectativa():
    archivos = {r.stem for r in (RAIZ / "tests" / "html" / "defectos").glob("*.html")}
    assert archivos == set(DEFECTOS)


def test_cada_defecto_del_ejemplo_dice_su_linea():
    # La línea de cada defecto es la que lleva su marca «N.» en el archivo.
    lineas = DEFECTUOSO.read_text(encoding="utf-8").splitlines()
    marca = {n: i for i, t in enumerate(lineas, 1) for n in range(1, 12)
             if re.search(rf"(/\*|<!--|y) {n}\. ", t)}
    A.revisar(DEFECTUOSO)
    donde = {(r, d): h.lineas for h in A.hallazgos for r, d in [h]}
    esperado = {
        ("no se usa Inter", "es la familia obligatoria"): 1,
        ("color fuera de la paleta", "#EFEFEF"): 2,
        ("color fuera de la paleta", "#333333"): 3,
        ("título que nombra en vez de afirmar", "Comparación de indicadores por región"): 6,
        ("separador de miles equivocado", "$1,240,000  ->  use «.»"): 7,
        ("separador decimal equivocado en un porcentaje", "76.2%  ->  use «,»"): 9,
        ("falta el espacio antes del %", "76.2%"): 10,
    }
    for clave, n in esperado.items():
        assert donde[clave] == [marca[n]], (clave, donde[clave], marca[n])
    assert [h.lineas for h in A.hallazgos if h[0] == "se usa box-shadow"] == [[marca[4]]]
    assert [h.lineas for h in A.hallazgos if h[0] == "se usa linear-gradient"] == [[marca[5]]]
    assert [h.lineas for h in A.hallazgos if h[0] == "aparece «MM»"] == [[marca[11]]]
    assert [h.lineas for h in A.hallazgos if h[0] == "aparece «COP»"] == [[marca[8]]]


def test_el_reporte_imprime_la_linea():
    assert "#333333  (línea 11)" in correr(DEFECTUOSO).stdout


def test_color_que_no_sabe_leer_se_avisa(tmp_path):
    # oklch(), hwb(), color()… no se convierten: no pueden pasar en silencio.
    f = tmp_path / "x.html"
    f.write_text("<style id='casa'>body{font-family:Inter}\n.a{color:oklch(60% 0.2 30)}"
                 ".b{color:hwb(120 0% 0%)}\n.c{color:color(srgb 1 0 0)}</style>"
                 "<h1>Norte supera la meta</h1>", encoding="utf-8")
    salida = correr(f).stdout
    assert "no se pudo leer" in salida
    assert "conforme, salvo 3 color(es) que no se pudieron leer" in salida
    for c in ("oklch(60% 0.2 30)", "hwb(120 0% 0%)", "color(srgb 1 0 0)"):
        assert c in salida, salida


def test_color_con_nombre_dice_todas_sus_lineas(tmp_path):
    f = tmp_path / "x.html"
    f.write_text("<style id='casa'>body{font-family:Inter}</style>\n"   # 1
                 "<h1>Norte supera la meta</h1>\n"                     # 2
                 "<p><font color=\"red\">x</font></p>\n"              # 3
                 "<div style=\"color:red\">x</div>\n"                  # 4
                 "<div style=\"color:\n"                               # 5
                 " red\">x</div>\n", encoding="utf-8")                 # 6
    A.revisar(f)
    (h,) = [h for h in A.hallazgos if h[0] == "color con nombre fuera de la paleta"]
    assert h.lineas == [3, 4, 6]


def test_navegador_indicado_que_no_existe_devuelve_2(tmp_path):
    # Se pidió auditar en navegador y no se pudo: no es «conforme».
    f = tmp_path / "x.html"
    f.write_text("<style id='casa'>body{font-family:Inter}</style>"
                 "<h1>Norte supera la meta</h1>", encoding="utf-8")
    r = subprocess.run([sys.executable, str(AUDITOR), str(f), "--navegador"],
                       capture_output=True, text=True, encoding="utf-8", check=False,
                       env={**os.environ, "AUDITOR_NAVEGADOR": str(tmp_path / "no_existe")})
    assert r.returncode == 2, r.stdout
    assert "AUDITOR_NAVEGADOR" in r.stdout + r.stderr
