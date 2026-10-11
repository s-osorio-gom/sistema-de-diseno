"""El auditor: muerde el defectuoso, deja pasar el conforme y no confunde un
fallo propio con un hallazgo."""
import subprocess
import sys
from pathlib import Path

import pytest

from adaptadores.html import auditar_html as A

RAIZ = Path(__file__).resolve().parents[1]
AUDITOR = RAIZ / "adaptadores" / "html" / "auditar_html.py"
DEFECTUOSO = RAIZ / "ejemplo" / "tablero_con_defectos.html"


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


def test_rgb_de_la_paleta_no_se_reporta():
    A.revisar(DEFECTUOSO)
    assert not [d for r, d in A.hallazgos if r.startswith("rgb()")]


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
