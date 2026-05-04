#!/usr/bin/env python3
"""Batch add tweets from a URL list file. One URL per line.
Lines starting with # are comments. Add --cat after URL to set category.

Usage: python scripts/batch_add.py urls.txt
"""

import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"
TMP_DIR = ROOT / ".dl_tmp"

# Default category
DEFAULT_CAT = "其他"


def extract_tweet(url):
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    cmd = ["gallery-dl", "--no-download", "--write-info-json", "-d", str(TMP_DIR), url]
    subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    dl_cmd = ["gallery-dl", "-d", str(TMP_DIR), url]
    subprocess.run(dl_cmd, capture_output=True, text=True, timeout=180)

    json_files = list(TMP_DIR.rglob("*.json"))
    if not json_files:
        return None

    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = json.load(f)

    media_files = [f for f in TMP_DIR.rglob("*") if f.is_file() and f.suffix.lower() in
                   {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}]
    return meta, media_files


def classify_tweet(text, meta):
    txt = text.lower()
    if "seedance" in txt:
        return "video"
    if re.search(r'16.*宫格.*编舞|生成.*舞|生成.*短片|生成.*广告片|生成.*视频', txt):
        return "video"
    if "gpt.image" in txt or "image2" in txt or "image prompt" in txt[:100].lower():
        return "image"
    return "image"


def add_one(url, cat):
    print(f"  {url[:80]}...")
    result = extract_tweet(url)
    if not result:
        print(f"  FAILED: could not fetch tweet")
        return False

    meta, media_files = result
    author_name = meta.get("author", {}).get("name", "unknown")
    date = meta.get("date", "")
    content = meta.get("content", "")

    ptype = classify_tweet(content, meta)
    has_img_kw = bool(re.search(r'gpt.image|image2|image prompt', content, re.IGNORECASE))
    has_vid_kw = bool(re.search(r'seedance|video prompt', content, re.IGNORECASE))

    if ptype == "video":
        video_content = content
        image_content = ""
        if has_img_kw:
            m = re.search(r'(?is)(?:image\s*prompt|gpt\s*image)\s*[:：]\s*\n?(.+)', content)
            if m:
                image_content = m.group(1).strip()
    else:
        image_content = content
        video_content = ""

    # Move media
    IMAGES_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)
    images = []
    video_path = None
    for mf in media_files:
        ext = mf.suffix.lower()
        dest_name = f"{author_name}_{mf.name}"
        if ext in ('.mp4', '.webm', '.mov'):
            dest = VIDEOS_DIR / dest_name
            shutil.move(str(mf), str(dest))
            if not video_path:
                video_path = f"videos/{dest_name}"
        elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            dest = IMAGES_DIR / dest_name
            shutil.move(str(mf), str(dest))
            images.append(f"images/{dest_name}")

    # Load data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    new_entry = {
        "cat": cat,
        "title": date,
        "text": content,
        "link": url,
        "title_ja": date,
        "text_ja": "",
        "type": ptype,
        "date": date,
        "author": f"@{author_name}",
        "image_prompt": image_content,
        "image_prompt_ja": "",
        "video_prompt": video_content,
        "video_prompt_ja": "",
        "images": images,
        "video": video_path or "",
    }

    data.append(new_entry)
    print(f"  OK: #{len(data)-1} ({ptype}) @{author_name} | {len(images)}imgs {'+1vid' if video_path else ''}")

    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    return True


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/batch_add.py <urls.txt>")
        print("File format: one URL per line, optional --cat after URL")
        sys.exit(1)

    url_file = Path(sys.argv[1])
    if not url_file.exists():
        print(f"File not found: {url_file}")
        sys.exit(1)

    with open(url_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Parse URLs and categories
    items = []
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        url = parts[0]
        cat = DEFAULT_CAT
        for i, p in enumerate(parts):
            if p == "--cat" and i + 1 < len(parts):
                cat = parts[i + 1]
        items.append((url, cat))

    print(f"Processing {len(items)} URLs...\n")
    ok = 0
    for url, cat in items:
        if add_one(url, cat):
            ok += 1

    print(f"\nDone: {ok}/{len(items)} succeeded")
    print(f"Next: python scripts/build_html.py")


if __name__ == "__main__":
    main()
