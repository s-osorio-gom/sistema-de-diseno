# Tableros HTML — cómo se construye uno que aguante

Guía para producir un **seguimiento interactivo en HTML** con la identidad de la casa.
Destilada de un tablero real en producción (seguimiento financiero de 34 operaciones,
7 pestañas, mapa, 2,8 MB, 60 pruebas automáticas).

Léela completa antes de escribir la primera línea. Casi todo lo que dice es una
**cicatriz**: algo que ya falló y costó horas encontrar.

---

## 1 · Qué es un tablero de estos

**Un solo archivo `.html`, autocontenido, que abre sin internet y sin servidor.**

Esa es la restricción que define todo lo demás. El destinatario es un VP o un gerente
que va a recibir el archivo por correo, abrirlo con doble clic y mirarlo cinco minutos.
No va a levantar un servidor, no va a instalar nada, y si algo pide internet y la red
corporativa lo bloquea, para él el tablero está roto.

Consecuencias, todas obligatorias:

- Fuentes **empotradas en base64**, no enlazadas
- Librerías (ECharts, Leaflet) **pegadas dentro del archivo**, no por CDN
- Datos **serializados dentro del HTML**, no cargados por `fetch`
- Imágenes y logos en **`data:` URI**

El archivo pesa 2-3 MB. Es el precio, y es barato.

> **Nunca se edita el HTML a mano.** Es 100 % salida de un script. Si alguien lo edita,
> el siguiente `build` borra el cambio y nadie entiende por qué. El HTML es un artefacto,
> no un documento.

---

## 2 · La arquitectura: separar extraer, procesar, construir y verificar

Cuatro responsabilidades, cuatro scripts. Mezclarlas es la causa raíz de casi todos los
problemas difíciles.

```
01_extraer      fuentes -> data/raw_*.json        NO transforma nada
02_procesar     raw     -> data/tablero.json      reglas de negocio, aquí y solo aquí
03_construir    tablero.json -> el HTML           diseño, cero cálculo
04_verificar    recalcula por OTRO camino + audita la paleta
05_probar       abre el HTML en Chrome y ejercita la interfaz
```

**Por qué separar extraer de procesar:** poder reprocesar cien veces sin volver a pegarle
a la fuente. Si cada prueba cuesta una descarga de tres minutos, dejas de probar.

**Por qué el HTML no calcula:** si el número lo calcula el navegador y el control lo
calcula Python, cada uno puede tener razón y aun así no coincidir. Un solo sitio calcula
—`02`— y todos los demás muestran.

**Por qué `04` recalcula por otro camino:** un control que repite el mismo cálculo no
verifica nada, solo confirma. `04` debe llegar al mismo número por una ruta distinta.

> ⚠️ **La independencia de `04` está en el CÁLCULO, no en las REGLAS.** Si `04`
> implementa reglas de negocio distintas de `02`, reporta descuadres que no existen y
> nadie vuelve a creerle. Misma regla, distinto camino.

> ⚠️ **`04` y `02` beben del mismo crudo, así que un crudo malo pasa los dos.** La red de
> seguridad contra fallas de extracción es que **el paso de extracción se caiga**, no que
> el de verificación lo note. Ver §7.

---

## 3 · Formato de cifras — reglas duras

No son preferencias. Un tablero que las incumple no es de la casa.

Vienen en convención española, la misma que audita `nucleo/reglas.json`
(`cifras`). Si su casa usa otra, cámbiela allí y aquí a la vez.

| Regla | Bien | Mal |
|---|---|---|
| Dinero: punto de miles, sufijo M de millones | `$1.000 M` | `$1.000.000.000`, `1000 MM`, `COP 1.000` |
| **Nunca la palabra COP** | `$706.472 M` | `COP 706.472` |
| Bajo 100 M, un decimal | `$87,4 M` | `$87 M` |
| Negativos: el signo **antes** del `$` | `−$73,9 M` | `$−73,9 M` |
| Menos tipográfico `−` (U+2212), no guion | `−$73,9 M` | `-$73,9 M` |
| Porcentajes: coma decimal, espacio antes del `%` | `104,2 %` | `104.2%` |
| Diferencias entre porcentajes: **p.p.** | `+1,17 p.p.` | `+5,6 %`, `×1,05` |
| Sin dato | `—` | `0`, `N/A`, vacío |

```js
// Sin depender del locale del navegador: los separadores se fijan a mano.
function num(v, d=0){            // −1234,5 -> '−1.234,5'
  const [ent, dec] = Math.abs(v).toFixed(d).split('.');
  return (v<0?'−':'') + ent.replace(/\B(?=(\d{3})+(?!\d))/g, '.') + (dec ? ',' + dec : '');
}
function money(v){
  if(v==null) return '—';
  const a = Math.abs(v)/1e6;
  return (v<0?'−':'') + '$' + num(a, a<100 ? 1 : 0) + ' M';
}
function pct(v,d=1){ return v==null ? '—' : num(v*100, d)+' %'; }
function pp(v){ return v==null ? '—' : (v>=0?'+':'') + num(v*100, 2) + ' p.p.'; }
```

**Por qué p.p. y no un cociente:** dividir 1,82 % entre 0,66 % da «2,7 veces», que suena
espectacular y no significa nada. La diferencia entre dos porcentajes son **puntos
porcentuales**. Y cuando el denominador puede ser negativo —una utilidad aprobada bajo
cero— el cociente además **invierte la lectura**: muestra verde donde hay que alarmarse.
Compara en **pesos** y en **p.p.**, nunca en ratio de porcentajes.

---

## 4 · Diseño

Los tokens salen de `nucleo/tokens.py` (que lee `nucleo/tokens.json`). Sobre eso, lo
específico de un tablero:

### Paleta
Solo los de `nucleo/tokens.json`, pedidos por **rol**. En un tablero se usan pocos:

```python
from nucleo import tokens as T
css = T.css_variables(["texto", "texto_secundario", "principal", "principal_claro",
                       "principal_oscuro", "borde", "acento", "bien", "mal"])
# :root{ --texto:…; --texto-secundario:…; --principal:…; … }  va dentro del <style>
```

Para qué sirve cada uno: `texto` (texto, encabezados, dominante), `principal` (cifra
principal, serie principal), `principal_claro` (series secundarias), `principal_oscuro`
(encabezados de tabla), `borde` (paneles, barra de filtros), `texto_secundario` (texto de
apoyo), `acento` (acento cálido, marcar lo destacado), `bien` y `mal` (texto positivo y
negativo).

El bloque se **genera** desde los tokens, no se copia: copiado, se queda con la paleta
vieja el día que cambie la marca. Por eso aquí no aparece ningún valor hexadecimal.

Verde y rojo **de texto** van en los tonos `bien` y `mal`, no en los `_claro`: esos son
fondos, y sobre papel no llegan al contraste mínimo de lectura.

### Densidad y jerarquía
- Diseño **plano**: sin sombras, sin degradados, sin bordes gruesos
- Una tarjeta = una idea. La tarjeta que abre la página lleva **acento ámbar** arriba
- Escala tipográfica con saltos claros; el número del KPI manda sobre su etiqueta
- Tablas: zebra en el fondo, encabezado en tinta, cifras con `font-variant-numeric: tabular-nums`
  (sin eso, las columnas de números bailan)

### Títulos que afirman
Igual que en un deck: **el título de cada bloque afirma una conclusión**.

❌ «Comparación de indicadores» · ✅ «Los agentes comerciales superan el caso de negocio»

En un tablero hay un matiz: **un título fijo miente en cuanto alguien filtra.** Si el
titular de cabecera afirma algo, tiene que **recalcularse con la selección activa**:

```js
function titular(a){
  const sobre = a.cump>=1, mejor = a.dif>=0;
  document.getElementById('hd-titulo').textContent =
      sobre && mejor  ? `${quien} superan el caso de negocio en venta y en utilidad`
    : sobre && !mejor ? `${quien} cumplen la venta, pero no la utilidad aprobada`
    : ...;
}
```

Y `quien` también se recalcula. Cuidado con la concordancia: «Antioquia superan» descuadra
el número del verbo — usa «Los agentes comerciales de Antioquia».

**Prosa: la mínima.** Un párrafo explicativo bajo cada gráfica se siente útil al
escribirlo y estorba al leerlo. Deja el titular y las notas de «cómo leer»; lo demás,
fuera.

### El orden de las cosas no es cosmético
Si el tablero refleja un archivo que el usuario conoce —un P&G, un balance—, **respeta el
orden de ese archivo**, no ordenes por valor. Quien conoce el original busca cada cuenta
donde siempre ha estado; un ranking la mueve de sitio cada mes.

En un comparador de dos lados importa doble: con cada lado ordenado por su propio ranking,
la fila 3 de la izquierda no es la misma cuenta que la fila 3 de la derecha, y compararlas
de un vistazo deja de funcionar.

---

## 5 · Patrones de interacción que ya funcionan

**Filtros en cascada.** Región → Gerente → Jefe → Coordinador → Entidad. Cada lista se
reacota con lo elegido arriba, y una selección que deja de ser válida **se limpia sola**.
Al construir la lista de un nivel, ese nivel **se excluye de su propio filtro** o el
`<select>` se queda con una sola opción y no puedes cambiar de valor sin volver a «Todos».

**Selector múltiple de periodos.** Botón con resumen («Todos los meses (7)», «Ene, Jun»)
que abre un popover de casillas. Nunca se queda sin ninguno seleccionado.

**Pestañas.** Un `<nav>` con `role="tablist"`. Al cambiar de pestaña hay que **redimensionar
las gráficas**: las que nacieron ocultas midieron cero.

**Comparador de dos lados.** Dos selecciones independientes y **un solo filtro de periodo
arriba que manda sobre los dos** — comparar enero contra julio no es una comparación.
Marca en rojo suave el lado que pesa más y en verde el que pesa menos, solo si difieren
de verdad (tolerancia, o pintarás ruido).

**Encabezados ordenables.** Clic ordena; segundo clic invierte. **Los nulos van siempre al
final**, en los dos sentidos: si «sin dato» sube al primer puesto al ordenar ascendente,
la tabla miente.

**Filas desplegables.** Cuenta → subcuentas. Al agregar, **las unidades suman y el unitario
se recalcula** como total ÷ unidades; nunca se promedia el unitario, o el número que se ve
no reproduce el total. Y a nivel de agregado, **no muestres unitario**: sumar vehículos con
personas da un «por unidad» sin significado.

---

## 6 · Verificación: dos redes distintas

### Red 1 — estática (`04_verificar.py`)
Recalcula los números desde el crudo por otro camino y **audita el diseño**: ningún hex
fuera de los colores de la paleta, ningún `rgba()` que no sea tinte de un color de la paleta, la palabra `COP`
en ninguna parte, el formato de cifras, los títulos que no afirman.

> ⚠️ **Marca tu CSS.** Si empotras Leaflet o cualquier librería, su CSS trae colores que no
> son tuyos y la auditoría los reporta como violaciones. Envuelve el propio en
> `<style id="casa">…</style>` y audita **solo ese**.

### Red 2 — funcional (`05_probar_navegador.py`)
**Un tablero puede pasar todos los controles de datos y de paleta y estar roto.** Si un
filtro no responde o una gráfica no pinta, no sirve — y eso no se ve con expresiones
regulares.

Chrome headless, un arnés inyectado que ejercita la interfaz por código y devuelve el
resultado por `document.title`:

```python
doc = HTML.read_text(encoding="utf-8")
cabeza, _, cola = doc.rpartition("</body>")      # rpartition, ver §7
prueba.write_text(cabeza + ARNES + "</body>" + cola, encoding="utf-8")
r = subprocess.run([CHROME, "--headless=new", "--disable-gpu",
                    "--virtual-time-budget=25000", "--window-size=1680,1200",
                    "--dump-dom", prueba.as_uri()], capture_output=True, text=True)
m = re.search(r"<title>TESTS::(.*?)</title>", r.stdout, re.S)
```

> ⚠️ **Fija `--window-size`.** Sin fijarlo Chrome cae a 800×600 y **todo lo responsive se
> prueba en su versión angosta**: la de escritorio, que es la que se usa, queda sin probar.

Qué probar como mínimo: que no haya errores de JavaScript · que cada gráfica exista y tenga
serie · que los filtros en cascada reacoten · que el selector de periodo recalcule · que
las cifras de la cabecera cuadren con la suma de la tabla · que cada pestaña pinte.

Y **capturas de cada pestaña**: el diseño hay que mirarlo, no solo medirlo.

---

## 7 · Las trampas

Cada una costó horas.

1. **El bundle de ECharts contiene `</body>` y `<script>` dentro de su propio código.**
   Un `.replace("</body>", …)` engancha en ESA aparición y parte el bundle. Usa
   `rpartition`. Y si lo extraes de otro archivo, anclarte a `rindex("<script>")` lo corta
   por la mitad: el archivo pesa casi igual, termina bien, y no define `window.echarts`.

2. **Un `getElementById` a un id inexistente tumba TODO el render.** Al quitar una sección
   hay que quitar también el código que la poblaba. Ningún control estático lo ve; solo la
   prueba funcional.

3. **Los formatters de tooltip revientan en el elemento extra.** Un waterfall dibuja N+1
   barras (la de total) sobre un arreglo de N pasos: `pasos[i]` es `undefined` en la
   última, el formatter lanza, y el tooltip **se queda pegado en pantalla**. Se ve como
   «la gráfica se traba después de unos usos».

4. **Un valor de error NO es un cero.** `#REF!`, `#N/A`, `Import Range internal error`
   significan «no sé». Leídos como dato hacen que un registro no pase los filtros de
   completitud y **desaparezca del resultado sin que nadie lo pida**.

5. **Una lectura fallida borra datos en silencio.** Nada de `try/except` que registre y
   siga. Reintenta, y si persiste **cae sin escribir**: un archivo viejo pero completo vale
   más que uno nuevo incompleto, porque el viejo se nota y el incompleto se publica.

6. **No fijes rangos a mano.** Un extractor topado en `A1:U445` perdió 48 filas —cuatro
   entidades completas— cuando la fuente creció. Sin avisar. Pide rango holgado y corta
   por el dato.

7. **Toda lista escrita a mano se desactualiza.** Agrupaciones, equivalencias, universos:
   derívalas de un archivo inventario. Una regla de fusión cableada olvidó dos casos y el
   tablero mostró 36 entidades donde había 34.

8. **Índices en vez de códigos.** Codificar filas como `[índice_entidad, …]` ahorra mucho
   peso, pero si luego **filtras la lista de entidades, esos índices se corren** y el dato
   se le atribuye a otra — en silencio, porque el total sigue cuadrando. Reindexa y
   compruébalo.

9. **`groupby` de pandas borra las claves nulas.** Va con `dropna=False`.

10. **Redondeo acumulado.** Si guardas cada periodo redondeado a entero, sumar N periodos
    arrastra hasta medio peso por periodo. La tolerancia del control es `0.5 × N`, no cero.

11. **Un mapa que nace en una pestaña oculta sale cortado.** Leaflet mide el contenedor al
    crearlo; hay que reavisarle (`invalidateSize()`) al mostrar la pestaña, y volver a
    fijar la vista, porque el encuadre se calculó sobre una medida de cero.

12. **Un punto lejano arruina el encuadre automático.** Con una sede en San Andrés,
    `fitBounds` deja el resto del país del tamaño de una moneda. Centro y zoom fijos.

13. **Fichas emergentes más altas que su contenedor.** Una ficha de doce filas en una
    columna angosta crece más que el mapa y se sale por debajo. Ponla **ancha y baja**
    (métricas en paralelo) y dale `max-height` con scroll interno como seguro.

14. **PowerShell corrompe HTML.** `Get-Content -Raw` + `Out-File` deja mojibake (`regiÃ³n`)
    y la página abre en blanco. Para manipular estos archivos, **Python con
    `encoding="utf-8"`**.

15. **Una tipografía de marca puede traer un juego de glifos incompleto.** Es común
    que a una fuente corporativa le falten `—` `–` `•` `…` `→` `✓`.
    En HTML el navegador cae a la fuente siguiente y no revienta, pero esa palabra se
    ve en otra tipografía —y una vez que se sabe, no se puede dejar de ver—. Cuente los
    glifos de su fuente antes de confiar en ella, y sustituya los que falten o acepte
    el salto a conciencia.

---

## 8 · Checklist antes de entregar

**Funciona** — ¿abre con doble clic, sin internet? ¿cero errores de JavaScript? ¿todas las
pestañas pintan? ¿los filtros reacotan y se limpian solos? ¿probado a ancho de escritorio?

**Cuadra** — ¿un control recalculó los números por otro camino? ¿el universo de entidades
es el esperado, y si cambió el tablero dice quién entró o salió y por qué? ¿los excluidos
quedan registrados con su motivo?

**Se ve de la casa** — ¿todos los colores salen de la paleta? ¿La tipografía empotrada?
¿plano, sin sombras? ¿tablas con `tabular-nums`?

**Se lee** — ¿el titular afirma y se recalcula al filtrar? ¿los bloques tienen títulos que
afirman? ¿el dinero va como `$1.000 M` y las diferencias en p.p.? ¿aparece «COP» en algún
sitio? (no debe) ¿los sin-dato salen como `—` y no como cero?

**Aguanta** — ¿si mañana falla una fuente, el proceso se cae en vez de publicar a medias?
¿el nombre del archivo dice la verdad sobre el periodo que contiene?
