#!/usr/bin/env python3
"""Migrate data.json: split text into image_prompt/video_prompt, add date field."""

import json
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"


def fmt_date(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace('Z', '+00:00'))
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, AttributeError):
        return ''


def classify(p):
    import re
    cat = (p.get("cat", "")).lower()
    txt = (p.get("text", "") + " " + p.get("text_ja", "")).lower()
    if "seedance" in cat or "视频制作" in cat:
        return "video"
    if re.search(r'seedance', txt):
        return "video"
    if re.search(r'16.*宫格.*编舞|生成.*舞|生成.*短片|生成.*广告片', txt):
        return "video"
    if re.search(r'用.*seedance', txt, re.IGNORECASE):
        return "video"
    return "image"


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    for p in data:
        # Generate human-readable date from title (which is ISO timestamp for most)
        iso_title = p.get("title", "")
        p["date"] = fmt_date(iso_title) if iso_title and 'T' in iso_title else ''

        # Classify type if not set
        if "type" not in p:
            p["type"] = classify(p)
        ptype = p.get("type", "image")

        # Migrate text to image_prompt or video_prompt
        if "image_prompt" not in p:
            p["image_prompt"] = p.get("text", "") if ptype == "image" else ""
        if "image_prompt_ja" not in p:
            p["image_prompt_ja"] = p.get("text_ja", "") if ptype == "image" else ""
        if "video_prompt" not in p:
            p["video_prompt"] = p.get("text", "") if ptype == "video" else ""
        if "video_prompt_ja" not in p:
            p["video_prompt_ja"] = p.get("text_ja", "") if ptype == "video" else ""

        # Ensure images/video fields exist
        if "images" not in p:
            p["images"] = []
        if "video" not in p:
            p["video"] = ""

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Migrated {len(data)} prompts in {DATA_FILE}")

    # Show stats
    with_image = sum(1 for p in data if p.get("image_prompt"))
    with_video_prompt = sum(1 for p in data if p.get("video_prompt"))
    print(f"  With image_prompt: {with_image}")
    print(f"  With video_prompt: {with_video_prompt}")
    print(f"  With date: {sum(1 for p in data if p.get('date'))}")


if __name__ == "__main__":
    main()
