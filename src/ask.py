"""CLI: python -m src.ask "your question" """
import argparse
import sys

from src.generate import SYSTEM, answer, build_user_message
from src.search import DEFAULT_EXCLUDE, Index


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Ask the AI Act (RAG)")
    ap.add_argument("question")
    ap.add_argument("-k", type=int, default=5, help="fragments to retrieve")
    ap.add_argument("--strategy", choices=["structural", "fixed"], default="structural")
    ap.add_argument("--show-context", action="store_true", help="print the retrieved fragments")
    ap.add_argument("--dry-run", action="store_true", help="print the prompt, do not call the API")
    ap.add_argument("--with-recitals", action="store_true", help="also search the recitals (considerandos)")
    args = ap.parse_args()

    index = Index(args.strategy, () if args.with_recitals else DEFAULT_EXCLUDE)
    if args.dry_run:
        chunks = index.search(args.question, args.k)
        print("=== SYSTEM ===\n" + SYSTEM + "\n\n=== USER ===\n" + build_user_message(args.question, chunks))
        return

    result = answer(args.question, index, args.k)
    if args.show_context:
        print("Fragmentos usados:")
        for c in result["chunks"]:
            print(f"  {c['score']:.3f}  {c['id']}")
        print()
    print(result["answer"])
    print(f"\n[tokens: {result['usage']['input']} in / {result['usage']['output']} out]")


if __name__ == "__main__":
    main()
