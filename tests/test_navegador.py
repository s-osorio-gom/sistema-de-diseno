"""El modo --navegador: abre la página en Chrome/Chromium sin interfaz. Se omite
si no hay navegador (o se le indica uno con AUDITOR_NAVEGADOR)."""
import subprocess
import sys
from pathlib import Path

import pytest

from adaptadores.html import auditar_html as A
from ejemplo import construir as E

RAIZ = Path(__file__).resolve().parents[1]
AUDITOR = RAIZ / "adaptadores" / "html" / "auditar_html.py"

pytestmark = pytest.mark.skipif(A.buscar_navegador() is None,
                                reason="no hay Chrome/Chromium (AUDITOR_NAVEGADOR)")


def navegador(ruta: Path) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(AUDITOR), str(ruta), "--navegador"],
                          capture_output=True, text=True, encoding="utf-8", check=False,
                          timeout=180)


def test_tablero_conforme_abre_sin_errores(tmp_path):
    r = navegador(E.tablero(tmp_path / "tablero.html"))
    assert r.returncode == 0, r.stdout
    assert "navegador: sin errores" in r.stdout


def test_error_de_javascript_se_reporta(tmp_path):
    roto = E.tablero(tmp_path / "roto.html")
    html = roto.read_text(encoding="utf-8")
    roto.write_text(html.replace(
        "</body>", "<script>document.getElementById('ya-no-existe').textContent = 1;"
                   "</script></body>"), encoding="utf-8")
    r = navegador(roto)
    assert r.returncode == 1
    assert "errores de JavaScript" in r.stdout


def test_pagina_casi_vacia_se_reporta():
    r = navegador(RAIZ / "ejemplo" / "tablero_con_defectos.html")
    assert r.returncode == 1
    assert "la página abre prácticamente vacía" in r.stdout
