"""Load and validate the golden set. `python -m evals.golden` lists what is still pending."""
import json
import sys
from pathlib import Path

GOLDEN = Path("evals/golden_set.json")


def load_golden() -> list[dict]:
    return json.loads(GOLDEN.read_text(encoding="utf-8"))


def problems(golden: list[dict], known_sources: set[str]) -> list[str]:
    """Structural problems of the golden set (does not require the expected answers to be filled)."""
    out = []
    for q in golden:
        if q["answerable"] and not q["sources"]:
            out.append(f"{q['id']}: answerable question without sources")
        if not q["answerable"] and q["sources"]:
            out.append(f"{q['id']}: unanswerable question should have no sources")
        for s in q["sources"]:
            if s not in known_sources:
                out.append(f"{q['id']}: unknown source '{s}'")
    return out


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    golden = load_golden()
    pending = [q["id"] for q in golden if not q["expected_answer"].strip()]
    print(f"{len(golden)} questions, {sum(not q['answerable'] for q in golden)} out of scope")
    print("pending expected_answer:", ", ".join(pending) or "none")


if __name__ == "__main__":
    main()
