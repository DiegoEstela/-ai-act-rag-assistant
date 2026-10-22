"""Semantic search: embed the question and rank chunks by cosine similarity."""
import argparse
import json
import sys

import numpy as np

from src.embed import PROCESSED, embed_query


class Index:
    def __init__(self, strategy: str = "structural", exclude_kinds: tuple[str, ...] = ()):
        chunks = json.loads((PROCESSED / f"chunks_{strategy}.json").read_text(encoding="utf-8"))
        vectors = np.load(PROCESSED / f"vectors_{strategy}.npy")  # row i <-> chunks[i]
        assert len(chunks) == len(vectors), "rebuild with: python -m src.embed build"
        keep = [i for i, c in enumerate(chunks) if c["kind"] not in exclude_kinds]
        self.chunks = [chunks[i] for i in keep]
        self.vectors = vectors[keep]

    def search(self, question: str, k: int = 5) -> list[dict]:
        scores = self.vectors @ embed_query(question)  # unit vectors: dot product = cosine
        top = np.argsort(scores)[::-1][:k]
        return [{**self.chunks[i], "score": float(scores[i])} for i in top]


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Search the AI Act")
    ap.add_argument("question")
    ap.add_argument("-k", type=int, default=5)
    ap.add_argument("--strategy", choices=["structural", "fixed"], default="structural")
    args = ap.parse_args()
    for r in Index(args.strategy).search(args.question, args.k):
        label = r["source"] if r["kind"] != "fixed" else " / ".join(r["sources"])
        print(f"{r['score']:.3f}  {label}  [{r['id']}]")
        print("       " + r["text"].replace("\n", " ")[:160] + "...")


if __name__ == "__main__":
    main()
