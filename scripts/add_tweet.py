#!/usr/bin/env python3
"""Add a single X tweet to the prompt library. Auto-extracts content, media, and classifies.

Usage: python scripts/add_tweet.py <url> [--cat category]
"""

import json, re, shutil, subprocess, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"
TMP_DIR = ROOT / ".dl_tmp"


def extract_tweet(url):
    """Download tweet info + media using gallery-dl."""
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True)

    cmd = ["gallery-dl", "--no-download", "--write-info-json", "-d", str(TMP_DIR), url]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)

    # Also download media
    dl_cmd = ["gallery-dl", "-d", str(TMP_DIR), url]
    subprocess.run(dl_cmd, capture_output=True, text=True, timeout=180)

    # Find JSON metadata
    json_files = list(TMP_DIR.rglob("*.json"))
    if not json_files:
        print("ERROR: Could not fetch tweet metadata")
        return None

    import json as j
    with open(json_files[0], "r", encoding="utf-8") as f:
        meta = j.load(f)

    # Find media files
    media_files = [f for f in TMP_DIR.rglob("*") if f.is_file() and f.suffix.lower() in
                   {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}]

    return meta, media_files


def classify_tweet(text, meta):
    """Classify as image or video prompt."""
    cat = (meta.get("category", "")).lower()
    txt = text.lower()
    if "seedance" in txt or "seedance" in cat:
        return "video"
    if re.search(r'16.*宫格.*编舞|生成.*舞|生成.*短片|生成.*广告片|生成.*视频', txt):
        return "video"
    if "gpt-image" in txt or "image2" in txt or "chatgpt.*image" in txt.lower():
        return "image"
    # Check media: has video -> video, has only images -> image
    return "image"


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/add_tweet.py <url> [--cat category]")
        print("Example: python scripts/add_tweet.py https://x.com/MrLarus/status/123456")
        sys.exit(1)

    url = sys.argv[1]
    cat = "其他"
    for i, arg in enumerate(sys.argv):
        if arg == "--cat" and i + 1 < len(sys.argv):
            cat = sys.argv[i + 1]

    print(f"Adding tweet: {url}")
    print(f"Category: {cat}")

    # Extract
    result = extract_tweet(url)
    if not result:
        sys.exit(1)

    meta, media_files = result

    author_name = meta.get("author", {}).get("name", "unknown")
    date = meta.get("date", "")
    content = meta.get("content", "")

    print(f"Author: @{author_name}")
    print(f"Date: {date}")
    print(f"Content: {content[:120]}...")
    print(f"Media files: {len(media_files)}")

    # Classify
    ptype = classify_tweet(content, meta)
    print(f"Classified as: {ptype}")

    # Load existing data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        import json as j
        data = j.load(f)

    # Move media files
    IMAGES_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    images = []
    video = None

    for mf in media_files:
        ext = mf.suffix.lower()
        dest_name = f"{author_name}_{mf.name}"
        if ext in ('.mp4', '.webm', '.mov'):
            dest = VIDEOS_DIR / dest_name
            shutil.move(str(mf), str(dest))
            if not video:
                video = f"videos/{dest_name}"
            print(f"  Video: {dest_name} ({dest.stat().st_size // 1024}KB)")
        elif ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            dest = IMAGES_DIR / dest_name
            shutil.move(str(mf), str(dest))
            images.append(f"images/{dest_name}")
            print(f"  Image: {dest_name} ({dest.stat().st_size // 1024}KB)")

    # Determine prompt fields
    has_image_keywords = bool(re.search(r'gpt[\s.\-]*image|image2|image\s*prompt|chatgpt.*image',
                                         content, re.IGNORECASE))
    has_video_keywords = bool(re.search(r'seedance|video\s*prompt|生成.*视频|生成.*短片',
                                        content, re.IGNORECASE))

    if ptype == "video":
        video_content = content
        image_content = ""
        if has_image_keywords:
            # Extract image prompt: from "Image prompt:" / "Image Prompt:" to before "Seedance" or end
            m = re.search(r'(?is)(?:image\s*prompt|gpt[\s.\-]*image)\s*[:：]\s*\n?(.+?)(?=\bseedance\b|$)', content)
            if m:
                image_content = m.group(1).strip()
            else:
                # If "Image prompt:" not found but has image keywords, try content before "Seedance"
                parts = re.split(r'(?i)\bseedance\b', content, maxsplit=1)
                image_content = parts[0].strip().rstrip("+").strip()
    elif ptype == "image" and has_video_keywords:
        # Image tweet that also mentions Seedance: extract Seedance part
        m = re.search(r'(?is)(?:seedance|video\s*prompt)\s*[:：]?\s*\n?(.+?)(?=\bimage\s*prompt\b|$)', content)
        if m:
            video_content = m.group(1).strip()
        else:
            parts = re.split(r'(?i)\bimage\s*prompt\b', content, maxsplit=1)
            video_content = parts[0].strip() if len(parts) > 1 else ""
        image_content = content
    else:
        image_content = content
        video_content = ""

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
        "video": video or "",
    }

    if ptype == "video" and not images and not video:
        print("WARNING: Video-type tweet has no media. Is this correct?")

    data.append(new_entry)
    print(f"\nAdded as entry #{len(data)-1} ({ptype})")

    # Save
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        j.dump(data, f, ensure_ascii=False, indent=2)

    # Cleanup
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)

    print(f"\nDone! Total prompts: {len(data)}")
    print(f"Next: python scripts/build_html.py")


if __name__ == "__main__":
    main()
