# Narrativa y diseño — cómo se construye un entregable que gana la decisión

> Esto no es decoración. Es tan obligatorio como la paleta.
> **Todo entra por los ojos**, y un mensaje bien ordenado gana decisiones.

## La audiencia manda: senior management y vicepresidencias

Todo lo que sigue está calibrado para ese público. Tienen poco tiempo, deciden, y
no van a reconstruir tu razonamiento. Tres consecuencias:

1. **Top-down, siempre.** La conclusión primero. Después el soporte.
2. **Una lámina = un mensaje.** Si no puedes decir de qué trata en una frase, va partida.
3. **Cerrar con una decisión**, no con un resumen. Qué necesitas de ellos.

---

## 1. Top-down: la regla que no se negocia

El orden natural de quien analiza es *datos → análisis → conclusión*. Para un VP se
invierte: **conclusión → razón → evidencia**.

| ❌ Bottom-up (cómo lo pensaste) | ✅ Top-down (cómo se presenta) |
|---|---|
| "Revisamos 14 distribuidores, medimos cobertura, tamaño de pedido y frecuencia…" | "La región pierde 938 M al año por el modelo actual de atención." |
| …"y por eso proponemos cambiar el modelo" | …"porque la cobertura está 22 pts bajo el potencial. Aquí el detalle." |

**Aplicado al título de cada lámina:** el título dice la conclusión, no la categoría.

- ❌ "Comparación de indicadores"
- ✅ "El escenario 2 gana en los tres indicadores que importan"

Ese solo cambio es la diferencia entre una lámina que se lee y una que se explica.

### La prueba del hilo
Lee **solo los títulos**, en orden, sin ver las láminas. Si eso ya cuenta la historia
completa y lleva a la decisión, el deck está bien armado. Si no, el hilo está roto.

---

## 2. La estructura que ya usas

Este arco funciona y conviene mantenerlo:

```
Contexto  →  Situación actual  →  Tensión  →  Aspiración  →  Opciones  →  Números  →  Riesgos  →  Decisión
```

| Bloque | Qué hace | Cómo se titula |
|---|---|---|
| Contexto | Encuadra el territorio | "Contexto", "Historia de la Operación" |
| Situación actual | Dónde estamos, con datos | "¿Cómo estamos hoy?" |
| Tensión | Por qué no se puede seguir igual | "Contras", "Punto de Quiebre" |
| Aspiración | A dónde queremos llegar | "¿Qué nos soñamos?" |
| Opciones | Escenarios comparables | "Escenarios Revisados" |
| Números | El caso financiero | "Costo de servir", "Evaluación financiera" |
| Riesgos | Qué puede salir mal | "Riesgos asociados a la decisión" |
| Decisión | Qué necesitas del comité | "938 M", cierre |

**Dos recursos que funcionan y conviene conservar:**

- **Preguntas como título de sección** — "¿Cómo estamos hoy?", "¿Qué nos soñamos?",
  "¿Por qué estamos revisando el modelo?". Crean expectativa y ordenan el hilo.
- **La lámina de una sola cifra** — "938 M", "2026". Es el remate emocional. Funciona
  porque no compite con nada más en la lámina.

**Ajuste top-down sobre esa estructura:** añada una lámina de **resumen ejecutivo justo
después de la portada**, con la conclusión y la petición. El comité debe poder decidir
solo con esa. Todo lo demás es el soporte para quien pregunte.

---

## 3. Densidad: el problema que sí se puede medir

Medido sobre tres presentaciones reales de un área de analítica (anonimizadas):

| Deck | Formas por lámina (mediana) | Máximo |
|---|---|---|
| Deck A | 21 | **86** |
| Deck B | 47 | 62 |
| Deck C | 18 | 59 |

Una lámina con 86 objetos no se lee: se descifra. **Techo sugerido: 25 formas.**
Si se pasa, casi siempre es que hay dos mensajes peleando — pártala.

Regla práctica por lámina:
- 1 título que afirma
- máximo 3–5 bloques de contenido
- 1 remate: la frase de "y por lo tanto…"

---

## 4. Jerarquía visual

El ojo debe recorrer la lámina en un orden que tú decides. Se logra con **tamaño y peso**,
no con color:

| Nivel | Tamaño | Peso | Para qué |
|---|---|---|---|
| Cifra / portada | 40 pt | ExtraBold | El número que se recuerda |
| Título de lámina | 32 pt | ExtraBold | La conclusión |
| Subtítulo | 24 pt | Semibold | Matiz del título |
| Destacado | 18 pt | Semibold | Frase clave, remate |
| Cuerpo | 14 pt | Regular | El texto normal |
| Apoyo | 12 pt | Regular | Detalle secundario |
| Caption | 10 pt | Light | Fuente del dato, notas |

**Saltos de al menos 4 pt entre niveles.** Si dos textos miden 14 y 15 pt, el ojo no
distingue jerarquía: lee ruido.

El color **no** crea jerarquía, crea significado: ámbar = esto es lo importante;
verde/rojo = señal; el color principal = todo lo demás.

---

## 5. Los errores que más se repiten

Encontrados auditando presentaciones reales:

| Problema | Dónde | Corrección |
|---|---|---|
| **Arial** en vez de la familia de la casa | Deck A (373 usos), Deck C (133) | El manual la exige sin excepción |
| Colores por defecto de Office: `#002060`, `#595959`, `#00B050`, `#00B0F0` | Deck A, Deck C | Nada fuera de la paleta |
| Paleta inventada sobre la marcha | Deck B | Regenerar desde los tokens |
| Títulos que nombran la categoría, no la conclusión | "Comparación de indicadores" | Título = afirmación |
| 86 formas en una lámina | Deck A | Partir en dos |

---

## 6. Checklist antes de entregar

**Narrativa**
- [ ] Leyendo solo los títulos, ¿se entiende la historia y la decisión?
- [ ] ¿Hay resumen ejecutivo en la lámina 2?
- [ ] ¿Cada título afirma algo, en vez de nombrar un tema?
- [ ] ¿La última lámina pide una decisión concreta?

**Diseño**
- [ ] ¿Ninguna lámina pasa de ~25 formas?
- [ ] ¿Todo en la familia de la casa, sin Arial ni Calibri?
- [ ] ¿Todos los colores salen de `nucleo/tokens.json`?
- [ ] ¿La jerarquía de tamaños tiene saltos claros?
- [ ] ¿Márgenes respetados y nada se desborda ni se solapa?

**Marca**
- [ ] ¿El logo contrasta con su fondo y va en un color de marca admitido?
- [ ] ¿Se respetan las reglas de su propio manual de marca (área de reserva, versiones
      del logo, elementos gráficos)?

---

## 7. Esto aplica a todo, no solo a PPTX

Un Excel de seguimiento también se lee con los ojos y también cuenta una historia:

- La hoja de **resumen va primera**, no última. Es el top-down del Excel.
- Encabezados en el principal oscuro con texto blanco, zebra en el fondo, la familia de la casa.
- La celda que importa se resalta en ámbar, igual que en un deck.
- Nada de rojo/verde por defecto de Excel: los del semáforo de `tokens.json`.

Mismo criterio para HTML, gráficas y cualquier entregable.
