#!/usr/bin/env python3
"""Rebuild index.html with updated data.json embedded."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
HTML_FILE = ROOT / "index.html"

START_MARKER = "const PROMPTS = "
END_MARKER = ";\n\n// ===== AUTO CLASSIFY"


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    json_str = json.dumps(data, ensure_ascii=False)

    with open(HTML_FILE, "r", encoding="utf-8") as f:
        html = f.read()

    # Find the PROMPTS array bounds
    start = html.find(START_MARKER)
    if start == -1:
        print("ERROR: START_MARKER not found in HTML")
        return

    # Start of JSON array content
    content_start = start + len(START_MARKER) + 1  # +1 for '['
    end_marker_pos = html.find(END_MARKER, content_start)
    if end_marker_pos == -1:
        # Fallback: find the closing ];
        end = html.find("\n];", content_start)
        if end == -1:
            print("ERROR: Cannot find end of PROMPTS array")
            return
    else:
        # Find the last ]; before END_MARKER
        end = html.rfind("];", content_start, end_marker_pos)
        if end == -1:
            print("ERROR: Cannot find ]; before END_MARKER")
            return

    # Reconstruct HTML
    new_html = html[:content_start] + json_str + html[end:]

    with open(HTML_FILE, "w", encoding="utf-8") as f:
        f.write(new_html)

    # Verify
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        verify_data = json.load(f)
    img_c = sum(1 for p in verify_data if p.get("type") == "image")
    vid_c = sum(1 for p in verify_data if p.get("type") == "video")
    print(f"Updated {HTML_FILE} with {len(verify_data)} prompts ({img_c} image, {vid_c} video)")


if __name__ == "__main__":
    main()
