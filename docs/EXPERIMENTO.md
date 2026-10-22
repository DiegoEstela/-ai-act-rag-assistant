# Experimentos de recuperación y generación

Dos experimentos, uno a la vez, cambiando un solo parámetro y manteniendo todo lo demás igual: mismo modelo de embeddings, mismo chunking estructural, mismo prompt, mismo juez (Claude Sonnet 5.5) y mismo golden set de 15 preguntas (12 con respuesta y 3 fuera de alcance).

---

## Experimento 1: excluir los considerandos de la búsqueda

### Hipótesis

En la evaluación de recuperación los considerandos (la exposición de motivos del reglamento) desplazaban a los artículos normativos: en q03, q04 y q12 los tres primeros puestos eran considerandos. Explican *por qué* existe una norma con un lenguaje muy parecido al de las preguntas, pero el asistente tiene que citar el texto normativo. **Si la búsqueda se limita a artículos y anexos, debería mejorar la recuperación y la cita.**

### Qué se cambió

`Index(strategy, exclude_kinds=("considerando",))` descarta los 180 considerandos antes de buscar. Se midió con `k=5`.

### Resultados

**Recuperación** (12 preguntas con respuesta, determinista):

| Métrica | Tamaño fijo | Estructural, con considerandos | Estructural, sin considerandos |
|---|---|---|---|
| hit@1 | 0.333 | 0.500 | **0.667** |
| hit@3 | 0.333 | 0.583 | **1.000** |
| hit@5 | 0.500 | 0.833 | **1.000** |
| hit@10 | 0.667 | 0.917 | **1.000** |
| MRR | 0.409 | 0.614 | **0.792** |

**Generación** (15 preguntas, k=5):

| Métrica | Con considerandos | Sin considerandos |
|---|---|---|
| Cita el artículo esperado | 0.750 | **1.000** |
| Correctitud media (de 5) | 3.33 | 3.42 |
| Fidelidad media (de 5) | 4.73 | 4.53 |
| Abstención en preguntas fuera de alcance | 1.000 | 1.000 |
| Falsas abstenciones | 0.000 | 0.000 |

### Interpretación

- La hipótesis **se confirma en la recuperación**: el artículo correcto entra siempre en el top 3 y el MRR sube de 0.61 a 0.79. Es la mayor mejora del proyecto con un solo cambio.
- Llega a la respuesta final en lo verificable: la cita pasa de 9 de 12 a 12 de 12.
- La correctitud (3.33 → 3.42) y la fidelidad (4.73 → 4.53) cambian dentro del ruido: 15 preguntas, una corrida y un juez no determinista.
- **Decisión: adoptado como comportamiento predeterminado** (`--with-recitals` para volver a incluirlos).

---

## Experimento 2: cuántos fragmentos se le pasan a Claude (k)

### Hipótesis

Tras el experimento 1, el artículo correcto llega, pero las respuestas siguen incompletas porque con `k=5` no entran todas las partes de los artículos largos (el Art. 5 tiene 14 partes). **Si se sube k, debería subir la correctitud.**

### Qué se cambió

Solo `k` (5, 8, 10), con los considerandos ya excluidos.

### Resultados (generación, juez Sonnet 5.5)

| Métrica | k=5 | k=8 | k=10 |
|---|---|---|---|
| Correctitud media (de 5) | 3.42 | **3.67** | 3.67 |
| Fidelidad media (de 5) | 4.53 | 4.53 | 4.53 |
| Cita el artículo esperado | 1.000 | 1.000 | 1.000 |
| Abstención fuera de alcance | 1.000 | 1.000 | 1.000 |
| Falsas abstenciones | 0.000 | 0.000 | 0.000 |

Pregunta por pregunta, de k=5 a k=8 la correctitud sube en tres casos (q01: 2→3, q06: 3→4, q09: 3→4) y no baja en ninguno. De k=8 a k=10 no hay mejora promedio, y la fidelidad de algunas preguntas es más inestable (por ejemplo q10 baja de 5 a 3 en k=10). Los promedios de k=8 y k=10 coinciden por casualidad: las respuestas son distintas en 14 de las 15 preguntas. (El archivo de resultados de k=10 no se conservó; las cifras de esa columna son las de la corrida.)

### Interpretación

- **La hipótesis se confirma en parte:** k=8 mejora la correctitud en +0.25 sin empeorar nada, y k=10 no aporta más.
- **Decisión: `k=8` como valor predeterminado.** Pasar más fragmentos cuesta más tokens, así que no se justifica subir sin ganancia.
- **El problema de fondo sigue abierto:** q01 sigue en 3/5. Con k=8 el contexto incluye solo 3 de las 14 partes del Art. 5, junto con artículos poco relevantes (Art. 100, 89, 2 y 56). Las partes de un artículo largo se parecen poco, una por una, a la pregunta general. Una solución natural es **traer el artículo completo o sus partes vecinas** una vez que una parte aparece entre los resultados (en la industria, *small-to-big retrieval* o *parent-document retrieval*), o sumar un reranker.

---

## Estado final de las métricas (valores predeterminados: sin considerandos, k=8)

| Métrica | Valor |
|---|---|
| hit@1 / hit@3 / hit@5 / hit@10 (recuperación) | 0.667 / 1.000 / 1.000 / 1.000 |
| MRR | 0.792 |
| Cita el artículo esperado | 1.000 |
| Correctitud media (juez, de 5) | 3.67 |
| Fidelidad media (juez, de 5) | 4.53 |
| Abstención en preguntas fuera de alcance | 3 de 3 |
| Falsas abstenciones | 0 de 12 |

Los umbrales de `evals/thresholds.json` se fijaron un caso por debajo de estos valores, y los dos gates (`pytest` y `pytest -m llm`) pasan.

## Limitaciones comunes a ambos experimentos

- El golden set espera artículos y anexos como fuente, así que por construcción un considerando nunca cuenta como acierto. Los considerandos pueden servir para preguntas interpretativas ("¿por qué se regula X?"), que este conjunto no cubre.
- 12 preguntas respondibles: un solo caso mueve hit@k 8 puntos.
- Una sola corrida de generación por configuración y sin `temperature=0` (la API lo rechaza con este modelo): las diferencias de ±0.2 en los promedios del juez no son concluyentes.
- El golden set fue redactado con ayuda de Claude y revisado por una persona. El juez tiene sesgo de indulgencia en fidelidad (en una revisión manual de 5 casos coincidió en correctitud 5 de 5 veces y en fidelidad 3 de 5, con 1 punto más generoso en los otros dos; ver `evals/results/review_judge.md`).
