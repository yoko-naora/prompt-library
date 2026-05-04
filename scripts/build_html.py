#!/usr/bin/env python3
"""Rebuild index.html with updated data.json embedded."""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
HTML_FILE = ROOT / "index.html"


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_str = json.dumps(data, ensure_ascii=False)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Replace the PROMPTS array in the HTML
    # Pattern: const PROMPTS = [...];  (first occurrence, all the way to matching ];)
    new_html = re.sub(
        r'const PROMPTS = \[.*?\n\];',
        f'const PROMPTS = {json_str};',
        html,
        flags=re.DOTALL
    )

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    print(f"Updated {HTML_FILE} with {len(data)} prompts from {DATA_FILE}")


if __name__ == "__main__":
    main()
