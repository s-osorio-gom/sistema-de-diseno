#!/usr/bin/env python3
"""
auditar_html.py — audita un entregable HTML contra las reglas de la casa.

    python3 adaptadores/html/auditar_html.py tablero.html
    python3 adaptadores/html/auditar_html.py tablero.html --navegador

CÓDIGO DE SALIDA
    0  conforme · 1  hay hallazgos · 2  no se pudo auditar (archivo
    inexistente, ilegible o error interno). El 2 existe para que un auditor que
    se cae no se confunda con uno que encontró defectos.

QUÉ REVISA
    paleta       ningún color fuera de los definidos en nucleo/tokens.json: #hex
                 (3, 4, 6 y 8 dígitos), rgb()/rgba(), hsl()/hsla() y colores con
                 nombre, en <style>, en style="" y en fill/stroke de SVG.
                 Comentarios y <script> no se auditan.
    tipografía   la familia obligatoria, y que esté empotrada si así se exige
    cifras       separadores, sufijos, el espacio antes del %, palabras vetadas
    narrativa    títulos que NOMBRAN un tema en vez de AFIRMAR una conclusión
    diseño       sombras y degradados, si la casa es de diseño plano
    navegador    que la página abra, pinte y no lance errores de JavaScript
                 (Chrome/Chromium; otro binario con AUDITOR_NAVEGADOR=/ruta)

    Cada hallazgo dice su línea en el archivo.

QUÉ NO REVISA
    Si los NÚMEROS están bien. Eso exige un control que los recalcule desde la
    fuente por otro camino. Esta herramienta audita la FORMA: una página puede
    pasarla entera y mostrar datos equivocados.

⚠️ MARQUE SU CSS. Si la página empotra librerías (Leaflet, un tema de terceros),
   su CSS trae colores que no son suyos. Envuelva el propio en
   <style id="casa">…</style> y se auditará solo ese. Sin la marca se audita
   todo y se reportan violaciones ajenas: son ruido, y hacen que nadie vuelva a
   mirar el reporte.
   Los style="" y los atributos de color de SVG del cuerpo se auditan siempre.
"""
from __future__ import annotations

import argparse
import colorsys
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from nucleo import tokens as T  # noqa: E402


class Hallazgo(tuple):
    """El par (regla, detalle) de siempre, más `.lineas`: dónde está en el archivo."""

    def __new__(cls, regla: str, detalle: str, lineas=()):
        h = super().__new__(cls, (regla, detalle))
        h.lineas = sorted(set(lineas))
        return h


hallazgos: list[Hallazgo] = []
sin_leer: list[str] = []          # colores que el auditor no sabe convertir


def falla(regla: str, detalle: str, patron: str | None = None, en: str = "",
          flags=re.I):
    """Registra un hallazgo. `patron` (regex) se busca en `en` —un texto con los
    mismos saltos de línea que el archivo— para decir en qué líneas está."""
    lineas = ([en.count("\n", 0, m.start()) + 1 for m in re.finditer(patron, en, flags)]
              if patron else [])
    hallazgos.append(Hallazgo(regla, detalle, lineas))


def _donde(lineas: list[int]) -> str:
    if not lineas:
        return ""
    txt = ", ".join(map(str, lineas[:5])) + ("…" if len(lineas) > 5 else "")
    return f"  (línea{'s' if len(lineas) > 1 else ''} {txt})"


def _vaciar(patron: str, texto: str) -> str:
    """Quita lo que casa con `patron` pero conserva sus saltos de línea, para que
    los números de línea de los hallazgos sigan apuntando al archivo original."""
    return re.sub(patron, lambda m: " " + "\n" * m.group(0).count("\n"), texto,
                  flags=re.S | re.I)


def sin_comentarios(doc: str) -> str:
    """Un comentario no se ve. `/* antes era #333333 */` no es un color en uso."""
    return _vaciar(r"<!--.*?-->", doc)


def bloque_auditable(doc: str) -> tuple[str, bool]:
    doc = sin_comentarios(doc)
    m = re.search(r'<style[^>]*id=["\']casa["\'][^>]*>(.*?)</style>', doc, re.S | re.I)
    if m:
        css, marcado = m.group(1), True
    else:
        css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", doc, re.S | re.I))
        marcado = False
    return _vaciar(r"/\*.*?\*/", css), marcado


def declaraciones(css: str) -> list[tuple[str, str]]:
    """Pares (propiedad, valor) de las declaraciones (`color: #1B2430`). En un
    selector, `#bad` o `#add` son ids, no colores: por eso solo se miran valores."""
    return [(m.group(1).lower(), m.group(2)) for m in re.finditer(
        r"(?<![\w-])(-*[a-zA-Z][\w-]*)\s*:\s*([^;{}]*)(?=[;}]|\Z)", css)]


def valores(css: str) -> str:
    # url(#fade) es una referencia a un id, y content:'Ref #ABC' es texto: ninguno
    # es un color.
    return "\n".join(re.sub(r"url\([^)]*\)|\"(?:\\.|[^\"\\])*\"|'(?:\\.|[^'\\])*'", " ", v)
                     for _, v in declaraciones(css))


def css_en_linea(doc: str) -> str:
    """Lo que se pinta desde el HTML: style="" y los atributos de color de SVG
    (fill, stroke…) y del HTML antiguo (color, bgcolor), como reglas CSS.

    Solo atributos de etiquetas del cuerpo: el texto visible no (un párrafo que
    explique «color="#FF0000"» no pinta nada), ni <head>, <link> o <meta>
    (`<link rel="mask-icon" color="…">` es el icono del navegador)."""
    cuerpo = _vaciar(r"<head\b.*?</head\s*>", sin_codigo(doc))
    reglas = []
    for etiqueta in re.finditer(r"<([a-zA-Z][\w:-]*)(\s[^<>]*)>", cuerpo):
        if etiqueta.group(1).lower() in ("link", "meta"):
            continue
        for m in re.finditer(
                r"\s(style|fill|stroke|stop-color|flood-color|color|bgcolor)\s*=\s*"
                r"(?:([\"'])(.*?)\2|([^\s\"'>]+))", etiqueta.group(2), re.S | re.I):
            valor = m.group(3) if m.group(2) else m.group(4)    # con o sin comillas
            reglas.append(valor if m.group(1).lower() == "style" else f"{m.group(1)}:{valor}")
    return "\n".join("{" + r + "}" for r in reglas)


# Propiedades donde una palabra suelta puede ser un color con nombre («red»).
PROP_DE_COLOR = re.compile(
    r"^(--.*|.*color|background(-image)?|border(-[a-z-]+)?|outline|fill|stroke|"
    r"text-decoration|column-rule|box-shadow|text-shadow|filter|backdrop-filter)$")


def colores_con_nombre() -> dict[str, str]:
    """Los 148 colores con nombre de CSS -> hex. Se toman de matplotlib, que ya
    es dependencia, en vez de copiar la tabla aquí."""
    from matplotlib.colors import CSS4_COLORS
    return {k.lower(): v.upper() for k, v in CSS4_COLORS.items()}


def a_rgb(funcion: str, args: str) -> tuple[int, int, int] | None:
    """rgb()/rgba() con números o %, y hsl()/hsla() con o sin `deg`, a (r, g, b).
    None si no se puede leer (p. ej. lleva var())."""
    partes = [x for x in re.split(r"[\s,/]+", args.strip()) if x][:3]
    if len(partes) < 3 or "var" in args:
        return None
    try:
        if funcion.startswith("rgb"):
            return tuple(round(float(x[:-1]) * 2.55) if x.endswith("%") else round(float(x))
                         for x in partes)
        h, sat, luz = partes
        por_unidad = {"turn": 360, "grad": 0.9, "rad": 180 / math.pi, "deg": 1}
        unidad = next((u for u in por_unidad if h.endswith(u)), "")
        h = float(h.removesuffix(unidad)) * por_unidad.get(unidad, 1)
        r, g, b = colorsys.hls_to_rgb((h % 360) / 360, float(luz.rstrip("%")) / 100,
                                      float(sat.rstrip("%")) / 100)
        return round(r * 255), round(g * 255), round(b * 255)
    except ValueError:
        return None


def usa_familia(doc: str, familia: str) -> bool:
    """¿Alguna regla CSS pide la familia? Se mira en font-family, font y en las
    propiedades personalizadas (`--fuente: 'Inter', …` usada con var()). Que la
    palabra aparezca en el texto («Internet») no cuenta, y en CSS los nombres de
    familia no distinguen mayúsculas."""
    limpio = sin_comentarios(doc)
    css = "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", limpio, re.S | re.I))
    css = _vaciar(r"/\*.*?\*/", css)
    css += "\n" + "\n".join(m.group(2) for m in re.finditer(
        r"\sstyle\s*=\s*([\"'])(.*?)\1", sin_codigo(doc), re.S | re.I))
    nombre = re.compile(rf"(?<![\w-]){re.escape(familia)}(?![\w-])", re.I)
    return any(nombre.search(m.group(1)) for m in re.finditer(
        r"(?<![\w-])(?:font-family|font|--[\w-]+)\s*:\s*([^;{}]*)", css, re.I))


def sin_codigo(doc: str) -> str:
    """El HTML que se pinta: sin comentarios, <script> ni <style>. Un `'<h2>…'`
    dentro de un script es código, no un título."""
    return _vaciar(r"<(script|style)\b[^>]*>.*?</\1\s*>", sin_comentarios(doc))


def texto_visible(doc: str) -> str:
    return re.sub(r"<[^>]+>", " ", sin_codigo(doc))


def revisar(ruta: Path) -> int:
    hallazgos.clear()
    sin_leer.clear()
    R = T.reglas()
    doc = ruta.read_text(encoding="utf-8", errors="replace")

    # Un <style> sin cerrar hace que las expresiones de abajo no vean ningún CSS
    # y la paleta salga «limpia» sin haberse revisado.
    abiertos = len(re.findall(r"<style\b", doc, re.I))
    cerrados = len(re.findall(r"</style\s*>", doc, re.I))
    if abiertos != cerrados:
        falla("HTML malformado",
              f"{abiertos} <style> abiertos y {cerrados} cerrados: el CSS no se puede auditar")

    css, marcado = bloque_auditable(doc)
    # Para ubicar hallazgos: el archivo sin comentarios (mismas líneas).
    fuente = _vaciar(r"/\*.*?\*/", sin_comentarios(doc))
    html = sin_codigo(doc)
    css += "\n" + css_en_linea(doc)
    if not marcado:
        print('   nota: no hay <style id="casa">; se audita TODO el CSS de la página.')

    # ── paleta ──────────────────────────────────────────────────────────────
    if R["colores"]["solo_de_la_paleta"]:
        permitidos = T.paleta_hex() | {c.upper() for c in R["colores"]["permitidos_extra"]}
        en_uso = valores(css)
        for hx in sorted(set(re.findall(r"#[0-9a-fA-F]{3,8}\b", en_uso))):
            h = hx.upper()
            if len(h) in (4, 5):                  # #ABC y #ABCD -> #AABBCC(DD)
                h = "#" + "".join(c * 2 for c in h[1:])
            if len(h) == 9:                       # #RRGGBBAA: se compara sin alfa
                h = h[:7]
            if h not in permitidos:
                falla("color fuera de la paleta", hx,
                      rf"{re.escape(hx)}(?![\w-])(?![^{{}}<>]*\{{)", fuente)

        def rgb_de(h: str) -> tuple[int, ...]:
            return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))

        validos = {rgb_de(h) for h in permitidos if len(h) == 7}

        def en_paleta(trio) -> bool:
            # ±1 por canal: hsl() y los % no caen exacto en un entero al convertir.
            return any(all(abs(a - b) <= 1 for a, b in zip(trio, v, strict=True))
                       for v in validos)

        def no_se_pudo_leer(texto: str):
            # No es un hallazgo (puede ser de la paleta), pero tampoco puede pasar
            # en silencio: se avisa con su línea para revisarlo a mano.
            lineas = [fuente.count("\n", 0, m.start()) + 1
                      for m in re.finditer(re.escape(texto), fuente, re.I)]
            sin_leer.append(texto)
            print(f"   nota: no se pudo leer el color {texto}{_donde(lineas)}:"
                  " revíselo a mano")

        for funcion, args in sorted(set(re.findall(
                r"\b(oklch|oklab|lch|lab|hwb|color)\(([^)]*)\)", en_uso, re.I))):
            no_se_pudo_leer(f"{funcion}({args})")

        for funcion, args in sorted(set(re.findall(r"\b(rgba?|hsla?)\(([^)]*)\)", en_uso, re.I))):
            trio = a_rgb(funcion.lower(), args)
            if trio is None:
                if "var" not in args:        # con var() el valor sale de otra regla
                    no_se_pudo_leer(f"{funcion}({args})")
                continue
            if en_paleta(trio):
                continue
            if funcion.lower().startswith("rgb"):
                falla("rgb() fuera de la paleta", f"rgb{trio}",
                      rf"\b{funcion}\({re.escape(args)}\)", fuente)
            else:
                hx = "#" + "".join(f"{c:02X}" for c in trio)
                falla("hsl() fuera de la paleta", f"{funcion}({args.strip()}) = {hx}",
                      rf"\b{funcion}\({re.escape(args)}\)", fuente)

        nombres = set()
        for prop, valor in declaraciones(css):
            if PROP_DE_COLOR.match(prop):
                valor = re.sub(r"url\([^)]*\)|([\"']).*?\1|var\([^)]*\)", " ", valor)
                nombres |= {w.lower() for w in re.findall(r"(?<![\w#-])[a-zA-Z]+(?![\w(-])", valor)}
        if nombres:
            try:
                tabla = colores_con_nombre()
            except ImportError:
                tabla = {}
                print("   nota: sin matplotlib no se revisan los colores con nombre (red, gray…)")
            for nombre in sorted(nombres & tabla.keys()):
                if tabla[nombre] not in permitidos:
                    # Cada aparición como VALOR (tras «:» de una declaración o
                    # «=» de un atributo), aunque el valor siga en otra línea.
                    lineas = [fuente.count("\n", 0, m.start()) + 1 for m in re.finditer(
                        rf"(?<![\w#-]){nombre}(?![\w(-])", fuente, re.I)
                        if re.search(r"(:[^;{}<>\"']*|=\s*[\"']?)$",
                                     fuente[max(0, m.start() - 300):m.start()])]
                    hallazgos.append(Hallazgo("color con nombre fuera de la paleta",
                                              nombre, lineas))

    # ── tipografía ──────────────────────────────────────────────────────────
    fam = R["tipografia"]["familia_obligatoria"]
    if fam and not usa_familia(doc, fam):
        falla(f"no se usa {fam}", "es la familia obligatoria",
              r"(?<![\w-])font(-family)?\s*:", fuente)
    elif R["tipografia"].get("debe_ir_empotrada"):
        if "@font-face" not in doc:
            falla(f"{fam} no está empotrada",
                  "sin @font-face solo se ve en equipos que la tengan instalada")
        elif "base64" not in doc.split("@font-face", 1)[1][:4000]:
            falla("la fuente se enlaza en vez de empotrarse",
                  "el entregable debe abrir sin internet ni archivos vecinos")

    # ── cifras ──────────────────────────────────────────────────────────────
    C, texto = R["cifras"], texto_visible(doc)
    for palabra in C["palabras_prohibidas"]:
        if re.search(rf"\b{re.escape(palabra)}\b", texto):
            falla(f"aparece «{palabra}»",
                  f"el sufijo de millones es {C['sufijo_millones']}",
                  rf"\b{re.escape(palabra)}\b(?![^<]*>)", html, 0)
    otro_miles = "." if C["separador_miles"] == "," else ","
    for m in set(re.findall(rf"\$\s?\d{{1,3}}(?:\{otro_miles}\d{{3}})+", texto)):
        falla("separador de miles equivocado",
              f"{m}  ->  use «{C['separador_miles']}»", re.escape(m), html)
    otro_dec = "." if C["separador_decimal"] == "," else ","
    for m in set(re.findall(rf"\d+\{otro_dec}\d+\s?%", texto)):
        falla("separador decimal equivocado en un porcentaje",
              f"{m}  ->  use «{C['separador_decimal']}»", re.escape(m), html)
    if C["espacio_antes_del_porcentaje"]:
        for m in set(re.findall(r"\d+(?:[.,]\d+)?%", texto)):
            falla("falta el espacio antes del %", m, rf"(?<![\d.,]){re.escape(m)}", html)
    if C["signo_antes_del_simbolo"] and re.search(r"\$\s?[-−]\d", texto):
        falla("el signo va después del símbolo",
              f"en negativos va antes: −$73{C['separador_decimal']}9 {C['sufijo_millones']}")

    # ── narrativa ───────────────────────────────────────────────────────────
    if R["narrativa"]["titulos_deben_afirmar"]:
        vagos = tuple(R["narrativa"]["inicios_vagos"])
        for tag in ("h1", "h2", "h3"):
            for m in re.finditer(rf"<{tag}\b[^>]*>(.*?)</{tag}>", html, re.S | re.I):
                limpio = re.sub(r"<[^>]+>", "", m.group(1)).strip()
                if limpio and limpio.lower().startswith(vagos):
                    hallazgos.append(Hallazgo("título que nombra en vez de afirmar",
                                              limpio[:70], [html.count("\n", 0, m.start()) + 1]))

    # ── diseño plano ────────────────────────────────────────────────────────
    if R["diseno"]["plano"]:
        for prop in R["diseno"]["propiedades_prohibidas"]:
            if prop.endswith("-gradient"):
                patron = rf"{re.escape(prop)}\s*\("
                # Un degradado es una FUNCIÓN dentro de otra propiedad
                # (`background: linear-gradient(...)`), no una propiedad. Buscarlo
                # como `linear-gradient:` no encuentra nunca nada, y el auditor
                # daba por limpia una página llena de degradados.
                usos = re.findall(rf"{re.escape(prop)}\s*\(", css)
            else:
                patron = rf"(?<![\w-]){re.escape(prop)}\s*:(?!\s*none)"
                # 'none' es lo contrario: quitar una sombra heredada.
                usos = [x for x in re.findall(rf"{re.escape(prop)}\s*:\s*([^;}}]+)", css)
                        if "none" not in x.lower()]
            if usos:
                falla(f"se usa {prop}", f"la casa es de diseño plano ({len(usos)} veces)",
                      patron, fuente)

    return len(doc)


def buscar_navegador() -> Path | None:
    """Chrome o Chromium. AUDITOR_NAVEGADOR=/ruta/al/binario manda sobre todo
    (sirve para un Chromium portátil, el de Playwright, Edge, Brave…)."""
    propio = os.environ.get("AUDITOR_NAVEGADOR")
    if propio:
        if Path(propio).is_file():
            return Path(propio)
        print(f"   AUDITOR_NAVEGADOR apunta a algo que no existe: {propio}")
        return None
    fijo = next((Path(p) for p in (
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Chromium.app/Contents/MacOS/Chromium",
        "/usr/bin/google-chrome", "/usr/bin/chromium",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    ) if Path(p).exists()), None)
    if fijo:
        return fijo
    encontrado = next(filter(None, (shutil.which(n) for n in (
        "google-chrome", "google-chrome-stable", "chromium", "chromium-browser"))), None)
    return Path(encontrado) if encontrado else None


def en_navegador(ruta: Path):
    """Abrirla de verdad. Un `getElementById` a un id que ya no existe deja la
    página en blanco, y ninguna expresión regular ve eso."""
    chrome = buscar_navegador()
    if not chrome:
        print("   (no se encontró Chrome: se omite la prueba en navegador;"
              " indíquelo con AUDITOR_NAVEGADOR=/ruta/al/binario)")
        return

    arnes = """
<script>
(function(){ var e=[]; window.addEventListener('error',x=>e.push(x.message));
  document.addEventListener('DOMContentLoaded',()=>setTimeout(()=>{
    var t=(document.body.innerText||'').trim().length;
    document.title='CHK::'+(e.length?e.slice(0,3).join(' | '):'sin errores')+'::'+t;
  },2000)); })();
</script>
"""
    doc = ruta.read_text(encoding="utf-8", errors="replace")
    # El arnés va LO MÁS ARRIBA POSIBLE. Al final solo vería los errores de los
    # scripts posteriores: uno roto en mitad del documento pasaría de largo y la
    # auditoría diría "sin errores" sobre una página que no arranca.
    m = re.search(r"<head[^>]*>", doc, re.I)
    inyectado = (doc[:m.end()] + arnes + doc[m.end():]) if m else arnes + doc
    with tempfile.TemporaryDirectory() as carpeta:
        tmp = Path(carpeta) / "chk.html"
        tmp.write_text(inyectado, encoding="utf-8")
        try:
            # El sandbox aísla el JS de la página (puede traer librerías de
            # terceros). Solo se quita como root, donde Chrome no arranca con él.
            sin_sandbox = ["--no-sandbox"] if getattr(os, "geteuid", lambda: 1)() == 0 else []
            r = subprocess.run([str(chrome), "--headless=new", "--disable-gpu", *sin_sandbox,
                                "--virtual-time-budget=15000", "--window-size=1680,1200",
                                "--dump-dom", tmp.as_uri()],
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", timeout=90, check=False)
        except subprocess.TimeoutExpired:
            falla("la página no respondió en el navegador", "se agotó el tiempo")
            return
    m = re.search(r"<title>CHK::(.*?)::(\d+)</title>", r.stdout, re.S)
    if not m:
        falla("la página no respondió en el navegador",
              "no llegó a ejecutar el arnés: puede estar rota de entrada")
        return
    err, largo = m.group(1).strip(), int(m.group(2))
    if err != "sin errores":
        falla("errores de JavaScript", err[:90])
    if largo < 200:
        falla("la página abre prácticamente vacía", f"solo {largo} caracteres de texto")
    if err == "sin errores" and largo >= 200:
        print(f"   navegador: sin errores · {largo:,} caracteres de texto")


def main() -> int:
    ap = argparse.ArgumentParser(description="Audita un HTML contra las reglas de la casa.")
    ap.add_argument("archivo")
    ap.add_argument("--navegador", action="store_true",
                    help="además, abrirlo en Chrome y buscar errores de JavaScript")
    a = ap.parse_args()

    ruta = Path(a.archivo).expanduser().resolve()
    if not ruta.is_file():
        print(f"No existe o no es un archivo: {ruta}", file=sys.stderr)
        return 2

    propio = os.environ.get("AUDITOR_NAVEGADOR")
    if a.navegador and propio and not Path(propio).is_file():
        # Se pidió el navegador y se indicó cuál, pero no está: no se pudo auditar.
        # (Sin AUDITOR_NAVEGADOR y sin Chrome, se avisa y se omite, como siempre.)
        print(f"AUDITOR_NAVEGADOR apunta a algo que no existe: {propio}", file=sys.stderr)
        return 2

    print("=" * 68)
    print(f"AUDITORÍA · {ruta.name}")
    print("=" * 68)
    try:
        n = revisar(ruta)
    except (OSError, KeyError, ValueError) as e:
        # KeyError/ValueError: reglas.json o tokens.json incompletos o inválidos.
        print(f"No se pudo auditar: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    print(f"   {n/1e3:,.0f} KB de HTML revisados")
    if a.navegador:
        en_navegador(ruta)

    print()
    if not hallazgos:
        if sin_leer:
            print(f"RESULTADO: conforme, salvo {len(sin_leer)} color(es) que no se pudieron"
                  " leer (vea las notas).")
        else:
            print("RESULTADO: conforme. Paleta, tipografía, cifras y narrativa cumplen.")
        print("Ojo: esto NO verifica que los números estén bien.")
        return 0

    print(f"RESULTADO: {len(hallazgos)} hallazgo(s).")
    por_regla: dict[str, list[str]] = {}
    for h in hallazgos:
        por_regla.setdefault(h[0], []).append(h[1] + _donde(h.lineas))
    for regla, dets in por_regla.items():
        print(f"\n  {regla}  ({len(dets)})")
        for d in dets[:8]:
            print(f"      · {d}")
        if len(dets) > 8:
            print(f"      … y {len(dets)-8} más")
    return 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:      # noqa: BLE001 — un fallo interno no es un hallazgo
        print(f"Error interno del auditor: {type(e).__name__}: {e}", file=sys.stderr)
        sys.exit(2)
