"""Turn text into vectors with a local multilingual model (no API, no cost)."""
import json
import sys
from functools import lru_cache
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

MODEL_NAME = "intfloat/multilingual-e5-small"
PROCESSED = Path("data/processed")


@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_passages(texts: list[str]) -> np.ndarray:
    """E5 expects the 'passage: ' prefix on documents. Vectors come out with length 1."""
    return get_model().encode([f"passage: {t}" for t in texts], normalize_embeddings=True,
                              show_progress_bar=len(texts) > 50)


def embed_query(text: str) -> np.ndarray:
    """E5 expects the 'query: ' prefix on questions."""
    return get_model().encode(f"query: {text}", normalize_embeddings=True)


def build_index(strategy: str = "structural") -> np.ndarray:
    """Embed every chunk of a strategy and save the matrix next to the chunks (row i = chunk i)."""
    chunks = json.loads((PROCESSED / f"chunks_{strategy}.json").read_text(encoding="utf-8"))
    vectors = embed_passages([c["text"] for c in chunks])
    np.save(PROCESSED / f"vectors_{strategy}.npy", vectors)
    return vectors


def demo():
    sys.stdout.reconfigure(encoding="utf-8")
    textos = [
        "Está prohibido usar sistemas de IA para puntuar socialmente a las personas.",
        "Queda vetada la clasificación de ciudadanos según su comportamiento social.",
        "Los proveedores deben establecer un sistema de gestión de riesgos.",
        "La receta lleva dos huevos, harina y una pizca de sal.",
    ]
    v = embed_passages(textos)
    print(f"forma de la matriz: {v.shape}  (textos x dimensiones)")
    print(f"primeros 8 números del vector 0: {np.round(v[0][:8], 3)}")
    print(f"largo del vector (norma): {np.linalg.norm(v[0]):.3f}\n")
    sim = v @ v.T
    print("similitud coseno entre textos (1.0 = idénticos):")
    for i in range(len(textos)):
        print("  " + "  ".join(f"{sim[i][j]:.2f}" for j in range(len(textos))) + f"   <- {textos[i][:48]}...")
    q = embed_query("¿Se puede hacer un ranking social de ciudadanos con IA?")
    print("\npregunta: ¿Se puede hacer un ranking social de ciudadanos con IA?")
    for t, s in sorted(zip(textos, v @ q), key=lambda x: -x[1]):
        print(f"  {s:.2f}  {t[:60]}")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "build":
        for strat in ("structural", "fixed"):
            m = build_index(strat)
            print(f"{strat}: {m.shape} guardado en {PROCESSED}/vectors_{strat}.npy")
    else:
        demo()
