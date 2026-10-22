# Experimento: excluir los considerandos de la búsqueda

## Hipótesis

En la evaluación de recuperación (paso 7) los considerandos (la exposición de motivos del reglamento) desplazaban a los artículos normativos del top de resultados: en q03, q04 y q12 los tres primeros puestos eran considerandos. Los considerandos explican *por qué* existe una norma, con un lenguaje muy parecido al de las preguntas, pero el asistente tiene que citar el texto normativo.

**Hipótesis:** si la búsqueda se limita a artículos y anexos, mejora la recuperación y la cita del artículo correcto.

## Qué se cambió (un solo parámetro)

`Index(strategy, exclude_kinds=("considerando",))` descarta los 180 considerandos del índice antes de buscar. Nada más cambia: mismo modelo de embeddings, mismo chunking, mismo `k=5`, mismo prompt, mismo juez (Claude Sonnet 5.5) y mismo golden set.

```
python -m evals.retrieval --no-recitals
python -m evals.generation --no-recitals
```

## Resultados

### Recuperación (12 preguntas con respuesta, gratis y determinista)

| Métrica | Tamaño fijo | Estructural (línea base) | Estructural sin considerandos |
|---|---|---|---|
| hit@1 | 0.333 | 0.500 | **0.667** |
| hit@3 | 0.333 | 0.583 | **1.000** |
| hit@5 | 0.500 | 0.833 | **1.000** |
| hit@10 | 0.667 | 0.917 | **1.000** |
| MRR | 0.409 | 0.614 | **0.792** |

### Generación (15 preguntas, k=5, juez Claude Sonnet 5.5)

| Métrica | Línea base (con considerandos) | Sin considerandos |
|---|---|---|
| Cita el artículo esperado | 0.750 | **1.000** |
| Correctitud media (de 5) | 3.33 | 3.42 |
| Fidelidad media (de 5) | 4.73 | 4.53 |
| Abstención en preguntas fuera de alcance | 1.000 | 1.000 |
| Falsas abstenciones | 0.000 | 0.000 |

## Interpretación

- **La hipótesis se confirma en la recuperación:** el artículo correcto entra siempre en el top 3 (antes en poco más de la mitad de los casos) y el MRR sube de 0.61 a 0.79. Es la mejora más grande de todo el proyecto, con un solo cambio.
- **La mejora llega a la respuesta final en lo que se puede verificar:** la cita pasa de 9 de 12 a 12 de 12.
- **La correctitud casi no cambia (3.33 → 3.42) y la fidelidad baja un poco (4.73 → 4.53).** Con 15 preguntas, un juez que no es determinista y una sola corrida por configuración, esas diferencias están dentro del ruido: no se puede afirmar que mejoraron ni que empeoraron.
- **Por qué la correctitud no sube:** ahora llega el artículo correcto, pero las respuestas siguen incompletas. Con `k=5`, el Art. 5 (14 partes) o el Anexo III (9 partes) no entran completos en el contexto. En q01 y q04 el juez sigue dando 2 porque falta la mayor parte de la lista. El cuello de botella pasó de "encontrar el artículo" a "traer suficientes partes de él".

## Limitaciones del experimento

- El golden set espera artículos y anexos como fuente, así que por construcción un considerando nunca cuenta como acierto. Los considerandos pueden ser útiles para preguntas interpretativas ("¿por qué se regula X?"), que este conjunto de preguntas no cubre.
- 12 preguntas respondibles: un solo caso mueve hit@k 8 puntos.
- Una sola corrida de generación por configuración, sin repetir, y sin `temperature=0`.
- El golden set fue redactado con ayuda de Claude y revisado por una persona, y el juez es de la misma familia de modelos que el generador.

## Próximo experimento sugerido

Con los considerandos fuera, subir `k` (por ejemplo 8 o 10) para que entren más partes de los artículos largos, y comparar la correctitud. Es el siguiente cuello de botella que muestran los datos.
