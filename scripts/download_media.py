#!/usr/bin/env python3
"""
Download media (images/videos) from MrLarus X posts.
Reads data.json, downloads media for each prompt, updates data.json with paths.

Requirements: pip install yt-dlp
Usage: python scripts/download_media.py [--limit N] [--type image|video|all]
"""

import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"

# Rate limiting: pause between requests (seconds)
DELAY = 3


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize_filename(s, max_len=60):
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = re.sub(r'\s+', '_', s.strip())
    return s[:max_len]


def download_media(url, output_dir, base_name):
    """Download media from a URL using yt-dlp. Returns list of downloaded files."""
    output_template = str(output_dir / f"{base_name}_%(id)s.%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "--extract-flat",  # Don't download, just extract info
        "--print", "%(id)s",
        url
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        if result.returncode != 0:
            return []
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []

    # Now download with media filter
    img_pattern = str(output_dir / f"{base_name}_img_%(autonumber)02d.%(ext)s")
    vid_pattern = str(output_dir / f"{base_name}_video.%(ext)s")

    # Download images
    img_cmd = [
        "yt-dlp",
        "--no-playlist",
        "--skip-download",
        "--write-thumbnail",  # won't work well for X
        # Approach: download all then separate
        "-o", img_pattern,
        "--match-filter", "ext=mp4",
        url,
    ]

    # Simpler: just download everything with a single yt-dlp call
    dl_cmd = [
        "yt-dlp",
        "--no-playlist",
        "-o", str(output_dir / f"{base_name}_%(autonumber)02d.%(ext)s"),
        "--restrict-filenames",
        url
    ]

    # Get existing files before download
    before = set(os.listdir(output_dir))

    try:
        subprocess.run(dl_cmd, capture_output=True, text=True, timeout=120)
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass

    time.sleep(DELAY)  # Be nice to X servers

    after = set(os.listdir(output_dir))
    new_files = sorted(after - before)
    return new_files


def classify_downloaded(files):
    """Split downloaded files into images and videos."""
    images = []
    videos = []
    for f in files:
        ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
        if ext in ('mp4', 'webm', 'mov'):
            videos.append(f)
        elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
            images.append(f)
    return images, videos


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download media from MrLarus X posts")
    parser.add_argument("--limit", type=int, default=0, help="Max prompts to process (0=all)")
    parser.add_argument("--type", default="all", choices=["image", "video", "all"])
    parser.add_argument("--delay", type=int, default=3, help="Delay between requests (seconds)")
    args = parser.parse_args()

    global DELAY
    DELAY = args.delay

    data = load_data()
    print(f"Loaded {len(data)} prompts from {DATA_FILE}")

    # Ensure directories
    IMAGES_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    processed = 0
    skipped = 0

    for i, prompt in enumerate(data):
        if args.limit > 0 and processed >= args.limit:
            break

        link = prompt.get("link", "")
        if not link or "x.com" not in link and "twitter.com" not in link:
            skipped += 1
            continue

        # Check if already has media
        existing_images = prompt.get("images", [])
        existing_video = prompt.get("video", "")
        if existing_images or existing_video:
            print(f"[{i+1}/{len(data)}] Already has media, skipping: {prompt.get('title','')[:40]}")
            skipped += 1
            continue

        # Check type filter
        ptype = prompt.get("type", "image")
        if args.type != "all" and ptype != args.type:
            skipped += 1
            continue

        base_name = sanitize_filename(f"{i:03d}_{prompt.get('title','')[:30]}")
        print(f"[{i+1}/{len(data)}] Downloading: {prompt.get('title','')[:50]}...")

        try:
            files = download_media(link, ROOT, base_name)

            # Move to correct directories
            all_new = []
            for f in files:
                src = str(ROOT / f)
                if not os.path.exists(src):
                    continue
                ext = f.rsplit('.', 1)[-1].lower() if '.' in f else ''
                if ext in ('mp4', 'webm', 'mov'):
                    dest = str(VIDEOS_DIR / f)
                    os.rename(src, dest)
                    rel_path = f"videos/{f}"
                    if not prompt.get("video"):
                        prompt["video"] = rel_path
                    all_new.append(rel_path)
                elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                    dest = str(IMAGES_DIR / f)
                    os.rename(src, dest)
                    rel_path = f"images/{f}"
                    if "images" not in prompt:
                        prompt["images"] = []
                    prompt["images"].append(rel_path)
                    all_new.append(rel_path)

            if all_new:
                print(f"  -> Downloaded {len(all_new)} files: {', '.join(all_new)}")
                processed += 1
            else:
                print(f"  -> No media found (may need auth/login)")
                skipped += 1

        except Exception as e:
            print(f"  -> Error: {e}")
            skipped += 1
            continue

    save_data(data)
    print(f"\nDone. Downloaded media for {processed} prompts, skipped {skipped}.")
    print(f"Data saved to {DATA_FILE}")
    print(f"Next: commit images/, videos/, and data.json to git")


if __name__ == "__main__":
    main()
