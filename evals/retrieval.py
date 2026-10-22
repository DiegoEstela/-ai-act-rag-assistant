"""Retrieval evals: does the right article show up, and how high? (hit@k and MRR)

Ranking is by article: several chunks of the same article count as one position, and a
question with several expected sources is a hit if ANY of them appears.
"""
import argparse
import sys

from evals.golden import load_golden
from src.search import Index

KS = (1, 3, 5, 10)
POOL = 50  # chunks fetched before collapsing them into a ranking of articles


def ranked_articles(index: Index, question: str) -> list[str]:
    """Unique sources in order of first appearance. A fixed-size chunk counts for every article it touches."""
    seen = []
    for chunk in index.search(question, POOL):
        for source in chunk.get("sources", [chunk["source"]]):
            if source not in seen:
                seen.append(source)
    return seen


def first_rank(ranking: list[str], expected: list[str]) -> int | None:
    """1-based position of the first expected source in the ranking, None if absent."""
    ranks = [ranking.index(s) + 1 for s in expected if s in ranking]
    return min(ranks) if ranks else None


def summarize(ranks: list[int | None], ks=KS) -> dict:
    n = len(ranks)
    out = {f"hit@{k}": sum(r is not None and r <= k for r in ranks) / n for k in ks}
    out["mrr"] = sum(1 / r for r in ranks if r) / n
    return out


def evaluate(strategy: str = "structural", index: Index | None = None) -> dict:
    index = index or Index(strategy)
    rows = []
    for q in load_golden():
        if not q["answerable"]:
            continue  # out-of-scope questions have no article to find
        ranking = ranked_articles(index, q["question"])
        rows.append({"id": q["id"], "question": q["question"], "expected": q["sources"],
                     "rank": first_rank(ranking, q["sources"]), "top3": ranking[:3]})
    return {"strategy": strategy, "n": len(rows), "metrics": summarize([r["rank"] for r in rows]), "rows": rows}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Retrieval evals (hit@k, MRR)")
    ap.add_argument("--strategy", choices=["structural", "fixed"], default="structural")
    ap.add_argument("--no-recitals", action="store_true", help="search only articles and annexes")
    args = ap.parse_args()
    index = Index(args.strategy, exclude_kinds=("considerando",) if args.no_recitals else ())
    res = evaluate(args.strategy, index)
    print(f"strategy: {res['strategy']}{' (no recitals)' if args.no_recitals else ''}  ({res['n']} answerable questions)\n")
    for r in res["rows"]:
        pos = r["rank"] if r["rank"] else "-"
        print(f"{r['id']}  rank={pos:<3} esperado={' / '.join(r['expected']):<28} top3={r['top3']}")
    print()
    for name, value in res["metrics"].items():
        print(f"{name:>7}: {value:.3f}")


if __name__ == "__main__":
    main()
