#!/usr/bin/env python3
"""
construir.py — el mismo dato en tres medios, desde un solo núcleo de tokens.

    python3 ejemplo/construir.py

Produce un tablero HTML, un Excel de seguimiento y una gráfica PNG. Ninguno
escribe un color a mano: los tres leen de `nucleo/tokens.json`. Cambie un valor
ahí y los tres cambian.

Al final se audita el HTML contra las reglas de la casa, y además se audita un
tablero con defectos a propósito para comprobar que el auditor muerde.
"""
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from adaptadores.excel import excel as X  # noqa: E402
from adaptadores.graficas import graficas as G  # noqa: E402
from nucleo import tokens as T  # noqa: E402

SALIDA = RAIZ / "ejemplo" / "salida"
AUDITOR = RAIZ / "adaptadores" / "html" / "auditar_html.py"

# Dato de ejemplo: cumplimiento por región.
REGIONES = [("Norte", 103.4, 1240), ("Centro", 97.1, 2180), ("Occidente", 88.6, 1560),
            ("Oriente", 76.2, 740), ("Caribe", 94.8, 980)]


def grafica(ruta: Path):
    import matplotlib
    matplotlib.use("Agg")
    fig, ax = G.figura("Oriente es la única región por debajo del 80 %",
                       "Cumplimiento de meta · cierre del mes")
    nombres = [r[0] for r in REGIONES]
    valores = [r[1] for r in REGIONES]
    barras = ax.bar(nombres, valores, width=0.62)
    G.resaltar(barras, indice=valores.index(min(valores)), color=T.color("mal"))
    G.referencia(ax, 100, "meta")
    ax.set_ylabel("% de cumplimiento")
    ax.set_ylim(0, 122)
    G.etiquetas_barras(ax, barras, valores)
    fig.savefig(ruta)
    return ruta


def entero(n: int) -> str:
    """Entero con el separador de miles de `reglas.json` (1.240 en español)."""
    return f"{n:,}".replace(",", T.reglas()["cifras"]["separador_miles"])


def porcentaje(v: float) -> str:
    """Un decimal, el separador decimal de `reglas.json` y espacio antes del %."""
    return f"{v:.1f}".replace(".", T.reglas()["cifras"]["separador_decimal"]) + " %"


def estado(v: float) -> str:
    return "En meta" if v >= 95 else ("Alerta" if v >= 80 else "Crítico")


def excel(ruta: Path):
    from openpyxl import Workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Resumen"          # la hoja de resumen va PRIMERA
    ws.append(["Región", "Cumplimiento %", "Clientes", "Estado"])
    for nombre, cump, clientes in REGIONES:
        ws.append([nombre, cump, clientes, estado(cump)])
    X.encabezado(ws, "A1:D1")
    X.zebra(ws, 2, len(REGIONES) + 1, 4)
    X.semaforo(ws, f"B2:B{len(REGIONES)+1}", bien=95, mal=80)
    X.bordes_suaves(ws, f"A1:D{len(REGIONES)+1}")
    X.ancho(ws, {1: 16, 2: 18, 3: 12, 4: 14})
    X.destacar(ws["B5"])          # la fila que exige decisión
    wb.save(ruta)
    return ruta


def tablero(ruta: Path):
    c = T.color
    # El ámbar de «Alerta» es claro: el texto blanco no se lee sobre él (2,1:1).
    tinta_pill = {"Alerta": c("texto")}
    filas = "".join(
        f"<tr><td>{n}</td>"
        f"<td class='num'>{porcentaje(v)}</td>"
        f"<td class='num'>{entero(cl)}</td>"
        f"<td><span class='pill' style='background:{G.semaforo(v, 95, 80)};"
        f"color:{tinta_pill.get(estado(v), '#FFFFFF')}'>{estado(v)}</span></td></tr>"
        for n, v, cl in REGIONES)
    total = sum(r[2] for r in REGIONES)

    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Cumplimiento por región</title>
<style id="casa">
  body {{ margin:0; padding:28px; background:{c('fondo')}; color:{c('texto')};
         font-family:{T.familia()}; }}
  h1 {{ font-size:{T.pt('titulo')*0.6:.0f}px; font-weight:{T.peso('titulo')};
        margin:0 0 4px; color:{c('principal_oscuro')}; }}
  .sub {{ color:{c('texto_secundario')}; font-size:{T.pt('cuerpo')}px; margin-bottom:22px; }}
  .cifra {{ font-size:{T.pt('cifra')}px; font-weight:{T.peso('cifra')};
            color:{c('principal')}; line-height:1; }}
  .rotulo {{ font-size:{T.pt('apoyo')}px; color:{c('texto_secundario')}; }}
  table {{ border-collapse:collapse; margin-top:22px; font-size:{T.pt('cuerpo')}px; }}
  th {{ background:{c('principal_oscuro')}; color:#FFFFFF; text-align:left;
        padding:8px 14px; font-size:{T.pt('apoyo')}px; font-weight:600; }}
  td {{ padding:7px 14px; border-bottom:1px solid {c('borde')}; }}
  tr:nth-child(even) td {{ background:{c('fondo')}; }}
  .num {{ text-align:right; font-variant-numeric:tabular-nums; }}
  .pill {{ display:inline-block; padding:2px 10px; border-radius:10px;
           font-size:{T.pt('nota')+1}px; font-weight:600; }}
  .nota {{ margin-top:20px; font-size:{T.pt('nota')}px; color:{c('texto_secundario')}; }}
</style></head>
<body>
  <h1>Oriente es la única región por debajo del 80 %</h1>
  <div class="sub">Cumplimiento de meta · cierre del mes · datos de ejemplo</div>
  <div class="cifra">{entero(total)}</div>
  <div class="rotulo">clientes atendidos en el periodo</div>
  <table>
    <tr><th>Región</th><th>Cumplimiento</th><th>Clientes</th><th>Estado</th></tr>
    {filas}
  </table>
  <div class="nota">Generado desde nucleo/tokens.json. Ningún color escrito a mano.</div>
</body></html>"""
    ruta.write_text(html, encoding="utf-8")
    return ruta


def auditar(ruta: Path) -> int:
    return subprocess.run([sys.executable, str(AUDITOR), str(ruta)], check=False).returncode


def _lectura(codigo: int, si_cero: str, si_uno: str) -> str:
    # 2 = el auditor no pudo correr. No es «detectado»: es que no se auditó.
    return {0: si_cero, 1: si_uno}.get(codigo, f"ERROR DEL AUDITOR (código {codigo})")


def main() -> int:
    # Sin esto, al redirigir la salida los print quedan en búfer y aparecen
    # después de los reportes del auditor, que corre en otro proceso.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True)
    SALIDA.mkdir(parents=True, exist_ok=True)
    print("\n  Generando el mismo dato en tres medios…")
    print(f"    gráfica  {grafica(SALIDA / 'grafica.png').name}")
    print(f"    excel    {excel(SALIDA / 'seguimiento.xlsx').name}")
    bueno = tablero(SALIDA / "tablero.html")
    print(f"    tablero  {bueno.name}")

    print("\n" + "─" * 68)
    conforme = auditar(bueno)

    malo = SALIDA / "tablero_con_defectos.html"
    malo.write_text((RAIZ / "ejemplo" / "tablero_con_defectos.html")
                    .read_text(encoding="utf-8"), encoding="utf-8")
    print("\n" + "─" * 68)
    print("  Ahora el mismo tablero con defectos a propósito.")
    print("  Si el auditor no los encuentra, el auditor no sirve.\n")
    detecta = auditar(malo)

    print("\n" + "═" * 68)
    ok = conforme == 0 and detecta == 1
    print(f"  tablero conforme         → {_lectura(conforme, 'pasa', 'FALLA')}")
    print(f"  tablero con defectos     → {_lectura(detecta, 'NO DETECTADO', 'detectado')}")
    print(f"  {'todo correcto' if ok else 'REVISAR'}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
