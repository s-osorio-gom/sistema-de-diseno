# Sistema de diseño para entregables

[![pruebas](https://github.com/s-osorio-gom/sistema-de-diseno/actions/workflows/pruebas.yml/badge.svg)](https://github.com/s-osorio-gom/sistema-de-diseno/actions/workflows/pruebas.yml)

Un solo núcleo de tokens, tres medios que lo consumen y **un auditor que
falla** cuando un entregable se sale de la línea.

No es una paleta en un PDF que nadie abre. Es un `tokens.json` del que leen el
HTML, el Excel y las gráficas, más una herramienta de línea de comandos que
revisa el resultado y devuelve código 1 si no cumple (y 2 si no pudo auditar:
archivo inexistente o ilegible, para que un auditor caído no pase por uno que
encontró defectos).

## Cómo está armado

```
nucleo/tokens.json + reglas.json        la única fuente: colores por ROL, tipografía, reglas
        │  nucleo/tokens.py             el cargador: T.color("principal"), T.css_variables()…
        ▼
adaptadores/  html · excel · graficas   producen entregables leyendo solo del núcleo
        │
        ▼
adaptadores/html/auditar_html.py        revisa el HTML entregado contra tokens + reglas
                                        0 conforme · 1 hallazgos · 2 no auditable
```

```
nucleo/
  tokens.json      paleta por ROL, escala tipográfica, series
  reglas.json      qué se audita: colores, tipografía, cifras, narrativa
  tokens.py        el cargador del que leen todos los adaptadores
adaptadores/
  html/            auditar_html.py — la pieza central
  excel/           encabezados, zebra, semáforos desde los tokens
  graficas/        matplotlib con el estilo de la casa
ejemplo/
  construir.py     el mismo dato en tablero HTML, Excel y gráfica
  tablero_con_defectos.html   once defectos a propósito
tests/             pruebas con pytest (html/validos y html/defectos: casos del auditor)
docs/
  narrativa.md     cómo se ordena un mensaje para que gane la decisión
  tableros.md      cómo se construye un tablero HTML que aguante
```

## Probarlo

Requiere Python 3.10 o posterior. Para el modo `--navegador`, además, Chrome o
Chromium (opcional).

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 ejemplo/construir.py
```

Los archivos generados quedan en `ejemplo/salida/` (ignorada por git):
`tablero.html`, `seguimiento.xlsx` y `grafica.png`.

Genera el mismo dato en tres medios —tablero HTML, Excel de seguimiento y
gráfica— sin que ninguno escriba un color a mano, audita el tablero, y después
audita **un tablero con defectos a propósito** para comprobar que el auditor
muerde. Termina así:

```
  tablero conforme         → pasa
  tablero con defectos     → detectado
  todo correcto
```

Un auditor que nunca falla no está auditando. Ese segundo archivo,
`ejemplo/tablero_con_defectos.html`, lleva once defectos marcados uno por uno;
si alguno deja de reportarse, o se reporta en otra línea, las pruebas fallan.

## Auditar su propio tablero

```bash
python3 adaptadores/html/auditar_html.py ruta/a/su_tablero.html
python3 adaptadores/html/auditar_html.py ruta/a/su_tablero.html --navegador
echo $?        # 0 conforme · 1 hallazgos · 2 no se pudo auditar
```

Salida real sobre el tablero defectuoso, con `--navegador` (recortada):

```
RESULTADO: 13 hallazgo(s).

  color fuera de la paleta  (3)
      · #333333  (línea 11)
      · #DDDDDD  (línea 15)
      · #EFEFEF  (línea 10)

  no se usa Inter  (1)
      · es la familia obligatoria  (línea 9)

  separador de miles equivocado  (1)
      · $1,240,000  ->  use «.»  (línea 21)

  título que nombra en vez de afirmar  (1)
      · Comparación de indicadores por región  (línea 19)

  se usa linear-gradient  (1)
      · la casa es de diseño plano (1 veces)  (línea 15)

  la página abre prácticamente vacía  (1)
      · solo 142 caracteres de texto
```

### Qué revisa

- **Paleta.** Ningún color fuera de `tokens.json` en las notaciones que lee:
  `#hex` de 3, 4, 6 u 8 dígitos (mayúsculas o minúsculas, con o sin alfa),
  `rgb()`/`rgba()` con números o %, `hsl()`/`hsla()` (en deg, turn, rad o grad)
  y colores con nombre (`red`, `darkslategray`). Mira los `<style>`, los
  `style=""` y los atributos `fill`/`stroke`/`color`/`bgcolor` de las etiquetas
  del cuerpo, con o sin comillas. No cuenta lo que está en comentarios, en
  `<script>`, en cadenas (`content:'#1'`) ni en el texto, ni confunde un selector
  `#bad` con un color. `oklch()`, `hwb()`, `lab()` y `color()` no los convierte:
  los avisa con su línea («no se pudo leer») para revisarlos a mano.
- **Tipografía.** Que alguna regla CSS pida la familia obligatoria (en
  `font-family`, `font` o una variable `--fuente`); que la palabra aparezca en el
  texto no basta. Opcionalmente, que esté empotrada.
- **Cifras.** Separadores de miles y decimales, el espacio antes del `%`, signo
  antes del símbolo, palabras vetadas (`COP`, `MM`).
- **Narrativa.** Títulos que nombran un tema en vez de afirmar una conclusión.
  **«Comparación de indicadores» obliga a leer la lámina para saber qué pasó;
  «El escenario 2 gana en los tres indicadores que importan» ya lo dijo.**
- **Diseño plano.** Sombras y degradados.
- **Navegador** (`--navegador`). La abre en Chrome o Chromium sin interfaz y
  reporta errores de JavaScript y páginas que quedan en blanco: un
  `getElementById` a un id que ya no existe no lo ve ninguna expresión regular.
  Si no encuentra el navegador, lo dice y omite esa prueba; para usar otro
  binario (un Chromium portátil, el de Playwright), `AUDITOR_NAVEGADOR=/ruta`;
  si esa ruta no existe, devuelve 2 (no se pudo auditar). Espera 90 s a que
  Chrome responda (`AUDITOR_NAVEGADOR_ESPERA` para otra cifra); agotar la espera
  es un hallazgo, no un «conforme». Cada auditoría usa un perfil de Chrome
  temporal propio.
  El sandbox de Chrome solo se desactiva si se corre como root.

Si la página empotra librerías de terceros, envuelva su propio CSS en
`<style id="casa">…</style>`: de los `<style>` se audita solo ese bloque.

## Colores por rol, no por nombre

```python
from nucleo import tokens as T
T.color("principal")    # no T.color("azul")
T.css_variables()       # ":root{ --texto:…; --principal:…; … }" para un <style>
```

Pedir *azul* amarra el código al color de hoy. Pedir *principal* sobrevive a un
cambio de marca: se edita `tokens.json` y los tres medios cambian a la vez.

## Adaptarlo a su marca

1. Reemplace los valores de `paleta` y `series` en `nucleo/tokens.json` por los
   suyos. **Conserve los nombres de rol**: es lo que hace que los adaptadores
   sigan funcionando. La paleta que trae es de demostración, no la de ninguna
   marca.
2. Ajuste `nucleo/reglas.json`: la familia obligatoria, si la tipografía debe ir
   empotrada, las palabras vetadas y la convención de cifras. Viene en
   convención española (`1.240.000` y `76,2 %`); para la inglesa, invierta los
   dos separadores.
3. Corra `python3 ejemplo/construir.py` y `pytest -q`. Si el tablero conforme
   pasa y el defectuoso se detecta, el sistema quedó bien montado.
   `tests/test_tokens.py` comprueba el contraste WCAG (4,5:1) de los pares de
   texto y fondo que usan los adaptadores: si su paleta no lo cumple, la prueba
   dice qué par falla.

Que esto funciona no es una promesa: `tests/test_adopcion.py` copia el
repositorio, cambia la paleta por otra y comprueba que `construir.py` pasa, que
el tablero y el Excel salen con los colores nuevos y que la suite entera sigue
en verde. Ninguna prueba ni guía lleva un color de la paleta de demostración
escrito a mano.

## Pruebas

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

Es lo mismo que corre `.github/workflows/pruebas.yml`, junto con
`ejemplo/construir.py`. `tests/test_navegador.py` se omite si no hay Chrome o
Chromium.

## Las dos guías

**[`docs/narrativa.md`](docs/narrativa.md)** — cómo se ordena un mensaje para
quien decide y no va a reconstruir su razonamiento. Top-down siempre; una lámina,
un mensaje; cerrar pidiendo una decisión, no resumiendo. Incluye **la prueba del
hilo**: lea solo los títulos, en orden, sin ver las láminas. Si eso ya cuenta la
historia y lleva a la decisión, el documento está bien armado.

**[`docs/tableros.md`](docs/tableros.md)** — cómo se construye un tablero HTML
autocontenido que abra sin internet, con quince trampas documentadas. Entre
ellas, dos que cuestan una tarde cada una: PowerShell corrompe el UTF-8 de un
HTML al reescribirlo, y una tipografía de marca puede traer un juego de glifos
incompleto —sin `—` ni `•` ni `→`—, así que el navegador cae a otra fuente en
esas palabras y nadie entiende por qué.

## Qué NO hace

- **No verifica que los números estén bien.** Audita la forma. Una página puede
  pasar entera y mostrar datos equivocados; eso lo tiene que atrapar un control
  que los recalcule desde la fuente por otro camino.
- **No lee todas las notaciones de color.** `oklch()`, `oklab()`, `lab()`,
  `lch()`, `hwb()` y `color(srgb …)` se avisan pero no se comparan con la
  paleta: el resultado dice «conforme, salvo N color(es) que no se pudieron
  leer». Los escapes de CSS (`\23 123456`) no se decodifican y pasan sin
  hallazgo.
- **No mira dentro de `url(…)`.** Un SVG empotrado como data URI en el CSS
  (`url("data:image/svg+xml,<svg fill='#…'/>")`) no se audita.
- **La familia obligatoria se busca en cualquier regla.** Un `@font-face` que
  declara Inter cuenta, aunque el `body` use Arial.
- **Con `<style id="casa">`, los demás `<style>` no se auditan**, aunque sean
  suyos.
- **No ve los colores que pone JavaScript.** Un color dentro de la
  configuración de una librería de gráficas (en un `<script>`) no se audita; solo
  el HTML y el CSS del archivo. `--navegador` detecta errores, no colores.
- **Audita los SVG en línea, también los ajenos.** Un logo o icono de terceros
  pegado como `<svg fill="…">` se reporta si su color no es de la paleta.
- **Las cifras se leen con expresiones regulares.** El separador de miles se
  revisa en importes con `$`; un `1,240` suelto es ambiguo (¿mil o uno coma
  dos?) y no se marca.
- **No trae tipografías ni logos.** Las fuentes de marca tienen licencia y no se
  redistribuyen. `tokens.json` nombra la familia; usted la instala (sin ella,
  las gráficas caen a DejaVu Sans).
- **No genera presentaciones.** El mismo patrón se extiende a `python-pptx`
  añadiendo un adaptador, pero aquí no está.
- El tablero de ejemplo cabe sin desplazamiento lateral desde 360 px de ancho;
  a 320 px sobran unos 13 px.

---

### In English

A design system built around one token core and an **auditor that fails the
build**: HTML, Excel and chart adapters all read `nucleo/tokens.json`, and a CLI
tool checks a delivered HTML against the house rules — palette (hex, rgb, hsl,
named colors, inline styles and SVG), typography, number conventions, flat
design, and headings that *name* a topic instead of *asserting* a conclusion —
reporting the line of each finding. Exit codes: 0 compliant, 1 findings, 2 could
not audit. Ships a deliberately broken dashboard to prove the auditor bites, and
a test that swaps the whole palette to prove a rebrand only touches
`tokens.json`. Requires Python 3.10+. Docs in Spanish.

## Licencia

MIT — ver [LICENSE](LICENSE).
