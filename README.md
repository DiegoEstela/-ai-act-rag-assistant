# EU AI Act RAG Assistant

**English** · [Español](#español)

A small, transparent Retrieval-Augmented Generation (RAG) system that answers questions about
**Regulation (EU) 2024/1689 (the AI Act)** in Spanish, cites the exact article, and says so when the
text does not contain the answer. It is built with no RAG frameworks (no LangChain, no LlamaIndex) so
every piece is visible, and it ships with an evaluation suite and quality gates that fail when a
change makes it worse.

## Results

Measured on a golden set of 15 questions (12 answerable, 3 deliberately out of scope), with
`claude-haiku-4-5` generating and `claude-sonnet-5-5` as judge. Defaults: structural chunking,
articles and annexes only, `k=8`.

| Metric | Value |
|---|---|
| Retrieval hit@1 / hit@3 / hit@5 / hit@10 | 0.67 / 1.00 / 1.00 / 1.00 |
| Retrieval MRR | 0.79 |
| Answer cites the expected article | 100 % (12/12) |
| Correctness (LLM judge, 1-5) | 3.67 |
| Faithfulness to the context (LLM judge, 1-5) | 4.53 |
| Abstains on out-of-scope questions | 3/3 |
| Wrongly abstains on answerable questions | 0/12 |

What changed along the way (details in [`docs/EXPERIMENTO.md`](docs/EXPERIMENTO.md), in Spanish):

| Change | Retrieval MRR | Cites expected article |
|---|---|---|
| Fixed-size chunking (1000 chars) | 0.41 | not measured |
| Structural chunking, recitals included | 0.61 | 75 % |
| + recitals excluded from search | **0.79** | **100 %** |

Raising `k` from 5 to 8 improved correctness from 3.42 to 3.67; `k=10` added nothing.
With 12 answerable questions, one question moves hit@k by 8 points, so read these numbers as a
regression alarm, not as a precise measurement.

## How it works

```
INGEST (once)
 EUR-Lex HTML ──▶ chunks by article ──▶ embeddings ──▶ numpy matrix

QUERY (each question)
 question ──▶ embedding ──▶ top-k cosine similarity ──▶ prompt with fragments ──▶ Claude ──▶ answer + citation
```

| Stage | Module | What it does |
|---|---|---|
| Ingestion | `src/ingest.py` | Parses the official HTML into 755 structural chunks (180 recitals, 113 articles, 13 annexes). Long articles are split with overlap. A fixed-size strategy is also produced for comparison. |
| Embeddings | `src/embed.py` | Local multilingual model (`intfloat/multilingual-e5-small`, 384 dimensions, 512-token input). No API cost. |
| Retrieval | `src/search.py` | Cosine similarity over a numpy matrix, top-k with score and article. Recitals are excluded by default. |
| Generation | `src/generate.py`, `src/ask.py` | Builds a prompt with the labelled fragments and calls `claude-haiku-4-5`. Answers only from the context, cites the article, abstains otherwise. |
| Evaluation | `evals/` | Golden set, retrieval metrics (hit@k, MRR), LLM-as-judge generation metrics, thresholds. |

## Design decisions

- **Structural chunking, not fixed-size.** Legal text is organised in articles and answers must cite them. Each chunk carries its source label ("Artículo 5", "Anexo III"). Structural chunking beat fixed-size on every retrieval metric.
- **Plain numpy instead of a vector database.** At ~750 chunks, retrieval is one matrix product; it keeps the mechanism visible.
- **Grounded generation with abstention.** The model is instructed to use only the supplied fragments and to answer *"El reglamento no lo indica en los fragmentos consultados."* when they do not contain the answer.
- **Deterministic ingestion.** No LLM is used to split documents, so re-running it on a new version of the regulation gives a reproducible result.
- **Deterministic checks where possible.** Citation and abstention are checked with code; the LLM judge only scores faithfulness and correctness. The judge is a different, stronger model than the generator to limit self-preference bias, and it was validated by hand on 5 cases (see `evals/results/review_judge.md`).
- **Quality gates.** `evals/thresholds.json` holds minimum scores; `pytest` fails if a change drops below them.

### Why no frameworks (LangChain / LlamaIndex)?

LangChain (orchestration: chains, agents, tools, memory) and LlamaIndex (connecting your data to an LLM:
loaders, indexes, query engines) are libraries that ship these RAG pieces pre-built, with connectors for
PDFs, databases and dozens of vector stores. They are great for fast prototypes and wide integrations.

I deliberately did not use them here: the goal is to understand and be able to explain every stage
(chunking, embeddings, similarity search, prompt construction), and frameworks hide exactly those steps
behind a single call, which makes it harder to tell whether a bad answer comes from the chunking, the
retrieval or the prompt. For a production client project I would evaluate them for their connectors and
speed, knowing what they do underneath and how to debug them.

## Setup

Requires Python 3.11+.

```
python -m venv .venv
.\.venv\Scripts\activate          # Windows (use source .venv/bin/activate on Linux/macOS)
pip install -r requirements.txt
```

1. Save the official HTML from
   [EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1689)
   as `data/raw/ai_act_es.html` (EUR-Lex blocks automated downloads, so it is manual).
2. Create a `.env` file in the project root with your key. It is git-ignored; never commit it.
   ```
   ANTHROPIC_API_KEY=your-key-here
   ```
3. Build the index:
   ```
   python -m src.ingest
   python -m src.embed build
   ```

## Usage

```
python -m src.search "your question" -k 5          # retrieval only
python -m src.ask "your question" --show-context   # full RAG answer with citations
python -m src.ask "your question" --dry-run        # print the prompt, no API call
python -m src.ask "your question" --with-recitals  # also search the recitals

pytest -q                                     # tests + retrieval quality gate (free, no API)
pytest -q -m llm                              # generation quality gate (calls the API, ~1.5 min)
python -m evals.retrieval                     # hit@k and MRR on the golden set
python -m evals.generation                    # LLM-as-judge scores (calls the API)
```

Example:

```
$ python -m src.ask "¿Cuál es la multa máxima por incumplir las prácticas prohibidas?"
La multa máxima ... depende del tipo de entidad:
- Para empresas y otros operadores: hasta 35.000.000 EUR o, si es superior, hasta el 7% ... (Artículo 99)
- Para instituciones, órganos y organismos de la Unión: hasta 1.500.000 EUR. (Artículo 100)
```

## Known limitations

- Long articles are still only partly retrieved: for "which practices are prohibited?", the context holds 3 of the 14 parts of Article 5, so the answer is faithful but incomplete. Next steps would be retrieving the neighbouring parts of a matched article (parent-document retrieval) or adding a reranker.
- Similarity scores cannot detect out-of-scope questions (an unrelated query scored almost as high as a relevant one); abstention is left to the generation step.
- Recitals are excluded by default, so interpretive questions ("why is X regulated?") are better served with `--with-recitals`. The golden set does not cover them.
- The API did not allow setting `temperature=0` for this model, so answers and judge scores vary slightly between runs.
- The golden set is small (15 questions) and was drafted with LLM assistance, then reviewed by a person.
- The EUR-Lex HTML must be saved by hand, so tests that need the index are skipped on a fresh clone.
- Not legal advice. Answers must be checked against the cited article.

## Project layout

```
src/       ingestion, embeddings, search, generation, CLI
evals/     golden set, retrieval and generation evals, thresholds, saved results
tests/     pytest tests and quality gates
docs/      experiment write-ups (EXPERIMENTO.md, in Spanish)
data/      raw and processed data (git-ignored)
```

---

<a id="español"></a>

# Asistente RAG del Reglamento de IA de la UE

[English](#eu-ai-act-rag-assistant) · **Español**

Un sistema RAG (Retrieval-Augmented Generation) chico y transparente que responde preguntas sobre el
**Reglamento (UE) 2024/1689 (Ley de IA)**, cita el artículo exacto y avisa cuando el texto no contiene
la respuesta. Está hecho sin frameworks de RAG (sin LangChain ni LlamaIndex) para que cada pieza se vea,
e incluye evaluaciones y controles de calidad que fallan cuando un cambio lo empeora.

## Resultados

Medidos sobre un golden set de 15 preguntas (12 con respuesta y 3 fuera de alcance a propósito), con
`claude-haiku-4-5` generando y `claude-sonnet-5-5` como juez. Valores predeterminados: chunking
estructural, solo artículos y anexos, `k=8`.

| Métrica | Valor |
|---|---|
| Recuperación hit@1 / hit@3 / hit@5 / hit@10 | 0,67 / 1,00 / 1,00 / 1,00 |
| Recuperación MRR | 0,79 |
| La respuesta cita el artículo esperado | 100 % (12/12) |
| Correctitud (juez LLM, 1-5) | 3,67 |
| Fidelidad al contexto (juez LLM, 1-5) | 4,53 |
| Se abstiene en preguntas fuera de alcance | 3/3 |
| Se abstiene por error en preguntas respondibles | 0/12 |

Qué cambió en el camino (detalle en [`docs/EXPERIMENTO.md`](docs/EXPERIMENTO.md)):

| Cambio | MRR de recuperación | Cita el artículo esperado |
|---|---|---|
| Chunking de tamaño fijo (1000 caracteres) | 0,41 | no medido |
| Chunking estructural, con considerandos | 0,61 | 75 % |
| + considerandos excluidos de la búsqueda | **0,79** | **100 %** |

Subir `k` de 5 a 8 mejoró la correctitud de 3,42 a 3,67; `k=10` no aportó más. Con 12 preguntas
respondibles, un solo caso mueve hit@k 8 puntos: conviene leer estas cifras como una alarma de
regresión y no como una medición precisa.

## Cómo funciona

```
INGESTA (una vez)
 HTML de EUR-Lex ──▶ chunks por artículo ──▶ embeddings ──▶ matriz numpy

CONSULTA (cada pregunta)
 pregunta ──▶ embedding ──▶ top-k por similitud coseno ──▶ prompt con fragmentos ──▶ Claude ──▶ respuesta + cita
```

| Etapa | Módulo | Qué hace |
|---|---|---|
| Ingesta | `src/ingest.py` | Convierte el HTML oficial en 755 chunks estructurales (180 considerandos, 113 artículos, 13 anexos). Los artículos largos se subdividen con solape. También genera una estrategia de tamaño fijo para comparar. |
| Embeddings | `src/embed.py` | Modelo multilingüe local (`intfloat/multilingual-e5-small`, 384 dimensiones, entrada de 512 tokens). Sin costo de API. |
| Búsqueda | `src/search.py` | Similitud coseno sobre una matriz numpy, top-k con score y artículo. Los considerandos se excluyen por defecto. |
| Generación | `src/generate.py`, `src/ask.py` | Arma el prompt con los fragmentos etiquetados y llama a `claude-haiku-4-5`. Responde solo con el contexto, cita el artículo y se abstiene si no está. |
| Evaluación | `evals/` | Golden set, métricas de recuperación (hit@k, MRR), métricas de generación con juez LLM, umbrales. |

## Decisiones de diseño

- **Chunking estructural, no de tamaño fijo.** El texto legal se organiza en artículos y las respuestas deben citarlos. Cada chunk lleva su etiqueta ("Artículo 5", "Anexo III"). El chunking estructural superó al de tamaño fijo en todas las métricas de recuperación.
- **numpy simple en vez de base de datos vectorial.** Con ~750 chunks, la búsqueda es un producto de matrices; deja el mecanismo a la vista.
- **Generación anclada con abstención.** Se le indica al modelo usar solo los fragmentos y responder *"El reglamento no lo indica en los fragmentos consultados."* cuando no contienen la respuesta.
- **Ingesta determinista.** No se usa un LLM para dividir documentos, así que volver a correrla con una nueva versión del reglamento da un resultado reproducible.
- **Verificaciones deterministas cuando se puede.** La cita y la abstención se comprueban con código; el juez LLM solo puntúa fidelidad y correctitud. El juez es un modelo distinto y más fuerte que el generador para limitar el sesgo de autopreferencia, y se validó a mano en 5 casos (ver `evals/results/review_judge.md`).
- **Controles de calidad.** `evals/thresholds.json` guarda los puntajes mínimos; `pytest` falla si un cambio baja de ellos.

### ¿Por qué sin frameworks (LangChain / LlamaIndex)?

LangChain (orquestación: cadenas, agentes, herramientas, memoria) y LlamaIndex (conectar tus datos con un LLM:
cargadores, índices, motores de consulta) son librerías que traen estas piezas de RAG ya armadas, con
conectores para PDFs, bases de datos y decenas de bases vectoriales. Son ideales para prototipos rápidos
y para integrar muchas fuentes.

Acá elegí no usarlos a propósito: el objetivo es entender y poder explicar cada etapa (chunking,
embeddings, búsqueda por similitud, armado del prompt), y los frameworks esconden justo esos pasos detrás
de una sola llamada, lo que complica saber si una mala respuesta viene del chunking, de la búsqueda o del
prompt. En un proyecto real para un cliente los evaluaría por sus conectores y su velocidad, sabiendo qué
hacen por dentro y cómo depurarlos.

## Instalación

Requiere Python 3.11+.

```
python -m venv .venv
.\.venv\Scripts\activate          # Windows (en Linux/macOS: source .venv/bin/activate)
pip install -r requirements.txt
```

1. Guardá el HTML oficial de
   [EUR-Lex](https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1689)
   como `data/raw/ai_act_es.html` (EUR-Lex bloquea las descargas automáticas, por eso es manual).
2. Creá un archivo `.env` en la raíz con tu clave. Git lo ignora; nunca lo subas.
   ```
   ANTHROPIC_API_KEY=tu-clave
   ```
3. Construí el índice:
   ```
   python -m src.ingest
   python -m src.embed build
   ```

## Uso

```
python -m src.search "tu pregunta" -k 5            # solo búsqueda
python -m src.ask "tu pregunta" --show-context     # respuesta RAG completa con citas
python -m src.ask "tu pregunta" --dry-run          # muestra el prompt, sin llamar a la API
python -m src.ask "tu pregunta" --with-recitals    # busca también en los considerandos

pytest -q                                     # tests + control de calidad de la búsqueda (gratis, sin API)
pytest -q -m llm                              # control de calidad de la generación (usa la API, ~1,5 min)
python -m evals.retrieval                     # hit@k y MRR sobre el golden set
python -m evals.generation                    # puntajes del juez LLM (usa la API)
```

## Limitaciones conocidas

- Los artículos largos todavía se recuperan solo en parte: ante "¿qué prácticas están prohibidas?", el contexto tiene 3 de las 14 partes del Artículo 5, así que la respuesta es fiel pero incompleta. Los próximos pasos serían traer las partes vecinas de un artículo encontrado (parent-document retrieval) o sumar un reranker.
- El score de similitud no sirve para detectar preguntas fuera de alcance (una consulta no relacionada puntuó casi igual que una relevante); la abstención queda a cargo de la generación.
- Los considerandos se excluyen por defecto, así que las preguntas interpretativas ("¿por qué se regula X?") se atienden mejor con `--with-recitals`. El golden set no las cubre.
- La API no permitió fijar `temperature=0` con este modelo, así que las respuestas y los puntajes del juez varían un poco entre corridas.
- El golden set es chico (15 preguntas) y se redactó con ayuda de un LLM, luego revisado por una persona.
- El HTML de EUR-Lex hay que guardarlo a mano, por lo que los tests que necesitan el índice se saltean en un clon nuevo.
- No es asesoramiento legal. Las respuestas deben verificarse contra el artículo citado.

## Estructura del proyecto

```
src/       ingesta, embeddings, búsqueda, generación, CLI
evals/     golden set, evals de recuperación y generación, umbrales, resultados guardados
tests/     tests con pytest y controles de calidad
docs/      informes de experimentos (EXPERIMENTO.md)
data/      datos crudos y procesados (ignorados por git)
```
