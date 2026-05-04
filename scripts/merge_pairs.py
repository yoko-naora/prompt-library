#!/usr/bin/env python3
"""Merge image+video tweet pairs into single cards.
Matches by: same date + keyword overlap in title/text."""

import json, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"

# Manually verified pairs: (video_index, image_index, topic)
# Video entry gets image_prompt from the paired image entry
# Only confirmed pairs: video entry references a specific image entry by topic
PAIRS = [
    (45, 3, "街头花式足球"),       # Video: 花式足球 result → Image: 16步动作分解
    (46, 3, "花式足球 Seedance"),   # Video: Seedance prompt → same image
    (47, 4, "街头篮球1v1"),         # Video: 篮球 result → Image: 篮球分镜图
    (59, 4, "篮球 Seedance"),       # Video: Seedance prompt → same image
    (52, 7, "韩式性感劲舞"),        # Video: Seedance2.0 → Image: 16宫格韩式劲舞
    (51, 61, "香水广告"),           # Video: Step2 Seedance → Image: 广告大片
]


def main():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    merged = 0
    for vi, ii, topic in PAIRS:
        if vi >= len(data) or ii >= len(data):
            print(f"SKIP [{vi}]+[{ii}] ({topic}): index out of range")
            continue

        vp = data[vi]
        ip = data[ii]

        if vp.get("type") != "video":
            print(f"SKIP [{vi}] ({topic}): not video type, is {vp.get('type')}")
            continue

        # Copy image_prompt and images from image entry to video entry
        if not vp.get("image_prompt"):
            vp["image_prompt"] = ip.get("image_prompt", "")
            vp["image_prompt_ja"] = ip.get("image_prompt_ja", "")
            merged += 1
            print(f"MERGE [{vi}]<-[{ii}] ({topic}): image_prompt={len(vp['image_prompt'])} chars")

        # Also copy images if video entry has none but image entry has some
        if not vp.get("images") and ip.get("images"):
            vp["images"] = ip.get("images", [])
            print(f"  + copied {len(vp['images'])} images")

        # Keep video entry's own title if better
        # Use image entry's date as post date for image part
        if not vp.get("image_date"):
            vp["image_date"] = ip.get("date", "")

    # Save
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"\nMerged {merged} pairs. Data saved.")

    # Stats
    vid_with_ip = sum(1 for p in data if p.get("type") == "video" and p.get("image_prompt"))
    vid_total = sum(1 for p in data if p.get("type") == "video")
    print(f"Video entries with image_prompt: {vid_with_ip}/{vid_total}")


if __name__ == "__main__":
    main()
