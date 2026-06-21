#!/usr/bin/env python3
"""Phase 6 CLI: ask the codebase a natural-language question.

Usage:
    python scripts/ask.py "what functions call validate_user?"

Requires a populated graph (ArcadeDB), a vector store (Chroma), and Ollama
running. Connection via the ARCADEDB_*, CHROMA_*, and OLLAMA_* env vars.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from graph_db import ArcadeDBClient  # noqa: E402
from llm import OllamaClient  # noqa: E402
from retrieval import QueryEngine  # noqa: E402
from vector_db import VectorStoreBuilder  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("question")
    ap.add_argument("--top-k", type=int, default=10)
    args = ap.parse_args()

    engine = QueryEngine(ArcadeDBClient(), VectorStoreBuilder(), OllamaClient())
    result = engine.answer(args.question, top_k=args.top_k)

    print(f"[strategy: {result['strategy']}]")
    if result.get("cypher"):
        print(f"[cypher: {result['cypher']}]")
    print(f"\n{result['answer']}\n")
    if result["sources"]:
        print("Sources:")
        for s in result["sources"]:
            print(f"  - {s}")


if __name__ == "__main__":
    main()
