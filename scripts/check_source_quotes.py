#!/usr/bin/env python3
"""Check that quotations in the explainer-guide references can be found locally.

Every “…” quotation in skills/explainer-guide/references/*.md is looked up in
the local source excerpts (skills/explainer-guide/sources/*.md) and in the
worked example. Quotes found nowhere are listed with their file and line, so a
person can sort them into example sentences written by the guide itself and
real citations that are missing from the excerpts.

The original conversations in work/explainer-feedback/examples/ and the
excerpts in skills/explainer-guide/sources/ are local maintainer inputs.
Conversation matches are listed as "project only". A public checkout has
the worked example, but lacks those local inputs, so it reports more misses.

Usage:
    python3 -I scripts/check_source_quotes.py            # list quotes not found
    python3 -I scripts/check_source_quotes.py --all      # list every quote and where it was found
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SKILL = PROJECT_ROOT / "skills" / "explainer-guide"
PROJECT_EXAMPLES = PROJECT_ROOT / "work" / "explainer-feedback" / "examples"
QUOTE_RE = re.compile(r"“([^“”]{4,}?)”")
STRIP_RE = re.compile(r"[\s“”‘’「」『』\"'`*]")


def norm(text: str) -> str:
    return STRIP_RE.sub("", text).lower()


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--all", action="store_true", help="also list quotes that were found")
    args = parser.parse_args()

    corpus = {}
    for path in sorted((SKILL / "sources").glob("*.md")):
        if path.name == "README.md":
            continue
        corpus[f"sources/{path.name}"] = norm(path.read_text(encoding="utf-8"))
    corpus["references/worked-example.md"] = norm((SKILL / "references" / "worked-example.md").read_text(encoding="utf-8"))
    for path in sorted(PROJECT_EXAMPLES.glob("*.md")):
        corpus[f"project only: {path.name}"] = norm(path.read_text(encoding="utf-8"))

    missing = 0
    total = 0
    for ref in sorted((SKILL / "references").glob("*.md")):
        if ref.name == "worked-example.md":
            continue
        for number, line in enumerate(ref.read_text(encoding="utf-8").splitlines(), 1):
            for quote in QUOTE_RE.findall(line):
                total += 1
                key = norm(quote)
                hits = [name for name, text in corpus.items() if key in text]
                if hits and args.all:
                    print(f"found    {ref.name}:{number}  “{quote}”  ->  {', '.join(hits)}")
                if not hits:
                    missing += 1
                    print(f"MISSING  {ref.name}:{number}  “{quote}”")
    print(f"\n{total} quotes checked, {missing} not found in sources or the worked example")


if __name__ == "__main__":
    main()
