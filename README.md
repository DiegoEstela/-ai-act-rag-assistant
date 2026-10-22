# EU AI Act RAG Assistant

**English** · [Español](#español)

A small, transparent Retrieval-Augmented Generation (RAG) system that answers questions about
**Regulation (EU) 2024/1689 (the AI Act)** in Spanish, cites the exact article, and says so when
the text does not contain the answer. Built with no RAG frameworks (no LangChain, no LlamaIndex)
so every piece is visible, and with an evaluation suite to measure it.

> Status: work in progress. Ingestion, embeddings, retrieval and grounded generation are done.
> The evaluation suite (retrieval metrics, LLM-as-judge, CI thresholds) is being built; results
> will be added here once measured.

## How it works

```
INGEST (once)
 EUR-Lex HTML ──▶ chunks by article ──▶ embeddings ──▶ numpy matrix

QUERY (each question)
 question ──▶ embedding ──▶ top-k cosine similarity ──▶ prompt with fragments ──▶ Claude ──▶ answer + citation
```

| Stage | Module | What it does |
|---|---|---|
| Ingestion | `src/ingest.py` | Parses the official HTML into 755 structural chunks (recitals, articles, annexes). Long articles are split with overlap. A fixed-size strategy is also produced for comparison. |
| Embeddings | `src/embed.py` | Local multilingual model (`intfloat/multilingual-e5-small`, 384 dimensions). No API cost. |
| Retrieval | `src/search.py` | Cosine similarity over a numpy matrix, top-k with score and article. |
| Generation | `src/generate.py`, `src/ask.py` | Builds a prompt with the labelled fragments and calls `claude-haiku-4-5`. Answers only from the context, cites the article, abstains otherwise. |
| Evaluation | `evals/` | Golden set of 15 questions (3 deliberately out of scope). Metrics coming next. |

## Design decisions

- **Structural chunking, not fixed-size.** Legal text is organised in articles, and answers must cite them. Each chunk carries its source label ("Artículo 5", "Anexo III").
- **Plain numpy instead of a vector database.** At ~750 chunks, retrieval is one matrix product; it keeps the mechanism visible.
- **Grounded generation with abstention.** The model is instructed to use only the supplied fragments and to answer *"El reglamento no lo indica en los fragmentos consultados."* when they do not contain the answer.
- **Deterministic ingestion.** No LLM is used to split documents, so re-running it on a new version of the regulation gives a reproducible result.

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

## Usage

```
python -m src.ingest                          # parse the HTML into chunks
python -m src.embed build                     # compute vectors
python -m src.search "your question" -k 5     # retrieval only
python -m src.ask "your question" --show-context   # full RAG answer with citations
python -m src.ask "your question" --dry-run        # print the prompt, no API call
pytest -q                                     # tests + retrieval quality gate (free, no API)
pytest -q -m llm                              # generation quality gate (calls the API, ~1.5 min)
python -m evals.retrieval                     # hit@k and MRR on the golden set
python -m evals.generation                    # LLM-as-judge scores (calls the API)
```

Quality thresholds live in `evals/thresholds.json`; `pytest` fails if a metric drops below them.

Example:

```
$ python -m src.ask "¿Cuál es la multa máxima por incumplir las prácticas prohibidas?"
La multa máxima ... depende del tipo de entidad:
- Para empresas y otros operadores: hasta 35.000.000 EUR o, si es superior, hasta el 7% ... (Artículo 99)
- Para instituciones, órganos y organismos de la Unión: hasta 1.500.000 EUR. (Artículo 100)
```

## Known limitations

- Retrieval can miss relevant parts of long articles: for "which practices are prohibited?", only 3 of the 14 parts of Article 5 were retrieved, so the answer was faithful but incomplete.
- Similarity scores cannot detect out-of-scope questions (an unrelated query scored almost as high as a relevant one); abstention is left to the generation step.
- The API did not allow setting `temperature=0` for this model, so answers may vary between runs.
- Not legal advice. Answers must be checked against the cited article.

## Project layout

```
src/       ingestion, embeddings, search, generation, CLI
evals/     golden set and evaluation code
tests/     pytest tests
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
y con evaluaciones para medirlo.

> Estado: en desarrollo. Ya están la ingesta, los embeddings, la búsqueda y la generación anclada.
> Se está construyendo la suite de evaluación (métricas de recuperación, LLM como juez, umbrales en CI);
> los resultados se agregarán acá cuando estén medidos.

## Cómo funciona

```
INGESTA (una vez)
 HTML de EUR-Lex ──▶ chunks por artículo ──▶ embeddings ──▶ matriz numpy

CONSULTA (cada pregunta)
 pregunta ──▶ embedding ──▶ top-k por similitud coseno ──▶ prompt con fragmentos ──▶ Claude ──▶ respuesta + cita
```

| Etapa | Módulo | Qué hace |
|---|---|---|
| Ingesta | `src/ingest.py` | Convierte el HTML oficial en 755 chunks estructurales (considerandos, artículos, anexos). Los artículos largos se subdividen con solape. También genera una estrategia de tamaño fijo para comparar. |
| Embeddings | `src/embed.py` | Modelo multilingüe local (`intfloat/multilingual-e5-small`, 384 dimensiones). Sin costo de API. |
| Búsqueda | `src/search.py` | Similitud coseno sobre una matriz numpy, top-k con score y artículo. |
| Generación | `src/generate.py`, `src/ask.py` | Arma el prompt con los fragmentos etiquetados y llama a `claude-haiku-4-5`. Responde solo con el contexto, cita el artículo y se abstiene si no está. |
| Evaluación | `evals/` | Golden set de 15 preguntas (3 fuera de alcance a propósito). Las métricas vienen después. |

## Decisiones de diseño

- **Chunking estructural, no de tamaño fijo.** El texto legal se organiza en artículos y las respuestas deben citarlos. Cada chunk lleva su etiqueta ("Artículo 5", "Anexo III").
- **numpy simple en vez de base de datos vectorial.** Con ~750 chunks, la búsqueda es un producto de matrices; deja el mecanismo a la vista.
- **Generación anclada con abstención.** Se le indica al modelo usar solo los fragmentos y responder *"El reglamento no lo indica en los fragmentos consultados."* cuando no contienen la respuesta.
- **Ingesta determinista.** No se usa un LLM para dividir documentos, así que volver a correrla con una nueva versión del reglamento da un resultado reproducible.

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

## Uso

```
python -m src.ingest                          # convierte el HTML en chunks
python -m src.embed build                     # calcula los vectores
python -m src.search "tu pregunta" -k 5       # solo búsqueda
python -m src.ask "tu pregunta" --show-context     # respuesta RAG completa con citas
python -m src.ask "tu pregunta" --dry-run          # muestra el prompt, sin llamar a la API
pytest -q                                     # tests + control de calidad de la búsqueda (gratis, sin API)
pytest -q -m llm                              # control de calidad de la generación (usa la API, ~1,5 min)
python -m evals.retrieval                     # hit@k y MRR sobre el golden set
python -m evals.generation                    # puntajes del juez LLM (usa la API)
```

Los umbrales de calidad están en `evals/thresholds.json`; `pytest` falla si una métrica baja de ellos.

## Limitaciones conocidas

- La búsqueda puede dejar afuera partes relevantes de artículos largos: ante "¿qué prácticas están prohibidas?", solo recuperó 3 de las 14 partes del Artículo 5, y la respuesta fue fiel pero incompleta.
- El score de similitud no sirve para detectar preguntas fuera de alcance (una consulta no relacionada puntuó casi igual que una relevante); la abstención queda a cargo de la generación.
- La API no permitió fijar `temperature=0` con este modelo, así que las respuestas pueden variar entre corridas.
- No es asesoramiento legal. Las respuestas deben verificarse contra el artículo citado.

## Estructura del proyecto

```
src/       ingesta, embeddings, búsqueda, generación, CLI
evals/     golden set y código de evaluación
tests/     tests con pytest
docs/      informes de experimentos (EXPERIMENTO.md)
data/      datos crudos y procesados (ignorados por git)
```
