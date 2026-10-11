#!/usr/bin/env python3
"""
graficas.py — matplotlib con los tokens de la casa.

    from adaptadores.graficas import graficas as G
    G.aplicar_estilo()
    fig, ax = G.figura("El escenario 2 gana en los tres indicadores")

El estilo se aplica una vez y todas las gráficas salen iguales. Lo que este
módulo quita es tan importante como lo que pone: el marco de la caja, la
rejilla vertical y los decimales de más son ruido que compite con el dato.
"""
from __future__ import annotations

import sys
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from nucleo import tokens as T  # noqa: E402


def aplicar_estilo():
    t = T.tokens()["tipografia"]
    mpl.rcParams.update({
        "font.family": "sans-serif",
        "font.sans-serif": [t["familia"], "DejaVu Sans", "Helvetica", "Arial"],
        "axes.prop_cycle": mpl.cycler(color=T.serie("categorica")),
        "figure.facecolor": T.color("fondo"),
        "axes.facecolor": T.color("fondo"),
        "axes.edgecolor": T.color("borde"),
        "axes.labelcolor": T.color("texto_secundario"),
        "axes.titlecolor": T.color("texto"),
        "axes.titlesize": 13, "axes.titleweight": "bold", "axes.titlelocation": "left",
        "axes.labelsize": 10, "axes.linewidth": 0.8,
        "axes.spines.top": False, "axes.spines.right": False,
        "axes.grid": True, "grid.color": T.color("borde"),
        "grid.linewidth": 0.7, "grid.alpha": 1.0,
        "xtick.color": T.color("texto_secundario"),
        "ytick.color": T.color("texto_secundario"),
        "xtick.labelsize": 9, "ytick.labelsize": 9,
        "legend.frameon": False, "legend.fontsize": 9,
        "figure.dpi": 130, "savefig.dpi": 200, "savefig.bbox": "tight",
    })


def figura(titulo: str = "", subtitulo: str = "", figsize=(7.2, 4.0)):
    """Una figura con el título como AFIRMACIÓN, no como nombre de la categoría.

    'Ventas por región' obliga a leer la gráfica para saber qué pasó.
    'Antioquia concentra el 42 % y crece' ya lo dijo.
    """
    aplicar_estilo()
    fig, ax = plt.subplots(figsize=figsize)
    # El título va arriba del todo y el subtítulo debajo, cada uno en su altura.
    # Con `set_title(pad=...)` más un texto en y=1.02 los dos caen en el mismo
    # sitio y se pisan: se ve en la imagen, no en el código.
    if titulo:
        ax.text(0, 1.13, titulo, transform=ax.transAxes,
                fontsize=13, fontweight="bold", color=T.color("texto"), va="bottom")
    if subtitulo:
        ax.text(0, 1.04, subtitulo, transform=ax.transAxes, fontsize=9.5,
                color=T.color("texto_secundario"), va="bottom")
    ax.grid(axis="x", visible=False)     # solo rejilla horizontal
    ax.set_axisbelow(True)               # la rejilla DEBAJO de las barras
    return fig, ax


def referencia(ax, y: float, etiqueta: str = "meta"):
    """Línea de referencia con el rótulo fuera del área de las barras.

    Puesto sobre la línea, el rótulo aterriza encima del valor de la última
    barra. Va al margen izquierdo, donde no compite con ningún dato.
    """
    ax.axhline(y, color=T.color("texto_secundario"), lw=0.9, ls=(0, (5, 4)), zorder=1)
    # Sobre la línea y pegado al borde derecho: a la izquierda se monta encima
    # de la etiqueta del eje, y centrado sobre la línea tapa una barra.
    ax.annotate(etiqueta, xy=(1, y), xycoords=("axes fraction", "data"),
                xytext=(0, 3), textcoords="offset points",
                ha="right", va="bottom", fontsize=8.5,
                color=T.color("texto_secundario"))
    return ax


def etiquetas_barras(ax, barras, valores, formato="{:.1f}", sufijo=" %",
                     decimal=",", separacion=3):
    """El valor encima de cada barra, con un halo del color del fondo.

    Sin el halo, cualquier línea de referencia que pase por detrás cruza el
    texto y lo vuelve ilegible justo en las barras que están cerca de la meta,
    que son las que interesan.
    """
    for b, v in zip(barras, valores, strict=True):
        ax.text(b.get_x() + b.get_width() / 2, v + separacion,
                (formato.format(v) + sufijo).replace(".", decimal),
                ha="center", va="bottom", fontsize=9, color=T.color("texto"), zorder=3,
                bbox=dict(boxstyle="round,pad=0.15", facecolor=T.color("fondo"),
                          edgecolor="none"))
    return ax


def resaltar(barras, indice: int, color: str | None = None):
    """Una barra en color de acento y el resto en neutro.

    Es la forma de que una gráfica tenga un mensaje: si todas las barras pesan
    lo mismo visualmente, el lector tiene que elegir solo qué mirar.
    """
    for i, b in enumerate(barras):
        b.set_color(color or T.color("acento") if i == indice else T.color("neutro"))
    return barras


def semaforo(valor: float, bien: float, mal: float) -> str:
    s = T.serie("semaforo")
    return s["bien"] if valor >= bien else (s["mal"] if valor <= mal else s["alerta"])
