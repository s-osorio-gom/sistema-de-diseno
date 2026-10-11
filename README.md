# Sistema de diseño para entregables

Un solo núcleo de tokens, tres medios que lo consumen y **un auditor que
falla** cuando un entregable se sale de la línea.

No es una paleta en un PDF que nadie abre. Es un `tokens.json` del que leen el
HTML, el Excel y las gráficas, más una herramienta de línea de comandos que
revisa el resultado y devuelve código 1 si no cumple (y 2 si no pudo auditar:
archivo inexistente o ilegible, para que un auditor caído no pase por uno que
encontró defectos).

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
tests/             pruebas con pytest
docs/
  narrativa.md     cómo se ordena un mensaje para que gane la decisión
  tableros.md      cómo se construye un tablero HTML que aguante
```

## Probarlo

Requiere Python 3.10 o posterior.

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python3 ejemplo/construir.py
```

Los archivos generados quedan en `ejemplo/salida/` (ignorada por git).

Genera el mismo dato en tres medios —tablero HTML, Excel de seguimiento y
gráfica— sin que ninguno escriba un color a mano, audita el tablero, y después
audita **un tablero con defectos a propósito** para comprobar que el auditor
muerde:

```
  tablero conforme         → pasa
  tablero con defectos     → detectado
```

Un auditor que nunca falla no está auditando. Ese segundo archivo,
`ejemplo/tablero_con_defectos.html`, lleva once defectos marcados uno por uno;
si alguno deja de reportarse, la herramienta se rompió. Las pruebas lo
comprueban defecto por defecto:

```bash
pip install -r requirements-dev.txt
pytest -q
ruff check .
```

Es lo mismo que corre `.github/workflows/pruebas.yml`, junto con
`ejemplo/construir.py`.

## Qué encuentra el auditor

```bash
python3 adaptadores/html/auditar_html.py ejemplo/tablero_con_defectos.html --navegador
```

Extracto del reporte:

```
  color fuera de la paleta  (3)
      · #333333
      · #DDDDDD
      · #EFEFEF
  no se usa Inter  (1)
  separador de miles equivocado  (1)
      · $1,240,000  ->  use «.»
  falta el espacio antes del %  (1)
  título que nombra en vez de afirmar  (1)
      · Comparación de indicadores por región
  se usa linear-gradient  (1)
```

De todos, el del título es el que más cambia un entregable. **«Comparación de
indicadores» obliga a leer la lámina para saber qué pasó; «El escenario 2 gana
en los tres indicadores que importan» ya lo dijo.** El auditor marca los títulos
que nombran un tema en vez de afirmar una conclusión.

Con `--navegador` además la abre en Chrome o Chromium sin interfaz y reporta
errores de JavaScript y páginas que quedan en blanco: un `getElementById` a un
id que ya no existe no lo ve ninguna expresión regular. Si no encuentra el
navegador, lo dice y omite esa prueba.

Si la página empotra librerías de terceros, envuelva su propio CSS en
`<style id="casa">…</style>`: se audita solo ese bloque.

## Colores por rol, no por nombre

```python
from nucleo import tokens as T
T.color("principal")    # no T.color("azul")
```

Pedir *azul* amarra el código al color de hoy. Pedir *principal* sobrevive a un
cambio de marca: se edita `tokens.json` y los tres medios cambian a la vez.

## Adaptarlo a su marca

1. Reemplace los valores de `nucleo/tokens.json` por los suyos. **Conserve los
   nombres de rol**: es lo que hace que los adaptadores sigan funcionando. La
   paleta que trae es de demostración, no la de ninguna marca. `tests/test_tokens.py`
   comprueba el contraste de los pares de texto y fondo que usan los adaptadores;
   si su paleta no lo cumple, la prueba lo dice.
2. Ajuste `nucleo/reglas.json`: la familia obligatoria, si la tipografía debe ir
   empotrada, y la convención de cifras. Viene en convención española
   (`1.240.000` y `76,2 %`); para la inglesa, invierta los dos separadores.
3. Corra `python3 ejemplo/construir.py` y `pytest -q`. Si el tablero conforme
   pasa y el defectuoso se detecta, el sistema quedó bien montado. Si cambia un
   color que el ejemplo defectuoso usa como válido (`rgb(...)` del `h1`),
   actualícelo también allí.

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
- **No trae tipografías ni logos.** Las fuentes de marca tienen licencia y no se
  redistribuyen. `tokens.json` nombra la familia; usted la instala.
- **No genera presentaciones.** El mismo patrón se extiende a `python-pptx`
  añadiendo un adaptador, pero aquí no está.

---

### In English

A design system built around one token core and an **auditor that fails the
build**: HTML, Excel and chart adapters all read `nucleo/tokens.json`, and a CLI
tool checks a delivered HTML against the house rules — palette, typography,
number conventions, flat design, and headings that *name* a topic instead of
*asserting* a conclusion. Exit codes: 0 compliant, 1 findings, 2 could not
audit. Ships a deliberately broken dashboard to prove the auditor bites, plus a
pytest suite. Requires Python 3.10+. Docs in Spanish.

## Licencia

MIT — ver [LICENSE](LICENSE).
