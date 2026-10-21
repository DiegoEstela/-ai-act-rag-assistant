# RAG compliance assistant (EU AI Act)

Small RAG project with evals, built step by step. See `docs/` for details.

## Setup

```
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
```

Put `ANTHROPIC_API_KEY=...` in a local `.env` file (git-ignored) or in your environment. Never commit keys.

## Usage

```
python -m src.ingest                 # parse data/raw/ai_act_es.html into chunks
python -m src.embed build            # compute vectors
python -m src.search "question"      # retrieval only
python -m src.ask "question" --show-context   # full RAG answer with citations
python -m src.ask "question" --dry-run        # print the prompt, no API call
```

The EUR-Lex HTML must be saved manually as `data/raw/ai_act_es.html`
(source: https://eur-lex.europa.eu/legal-content/ES/TXT/HTML/?uri=CELEX:32024R1689).
