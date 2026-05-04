#!/usr/bin/env python3
"""
Download and VERIFY media from MrLarus X posts using gallery-dl.
- Downloads images/videos via gallery-dl (works without X login)
- Verifies every file (size > 0, valid format, minimum size)
- Retries failed downloads up to 3 times
- Only writes to data.json after verification
- Prints clear success/failure report

Requirements: pip install gallery-dl
Usage: python scripts/download_media.py [--limit N] [--retries N]
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"
TMP_DIR = ROOT / ".dl_tmp"
FAILURE_LOG = ROOT / "download_failures.txt"

DEFAULT_RETRIES = 3
DELAY_BASE = 5


def check_prerequisites():
    try:
        r = subprocess.run(["gallery-dl", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"  gallery-dl version: {r.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("ERROR: gallery-dl not found. Install with: pip install gallery-dl")
    return False


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def verify_file(filepath):
    path = Path(filepath)
    if not path.exists():
        return False, "not found"
    size = path.stat().st_size
    if size == 0:
        path.unlink()
        return False, "empty (0 bytes)"
    ext = path.suffix.lower()
    valid_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
    if ext not in valid_exts:
        return False, f"bad extension {ext}"
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp') and size < 500:
        path.unlink()
        return False, f"image too small ({size}B)"
    if ext in ('.mp4', '.webm', '.mov') and size < 5000:
        path.unlink()
        return False, f"video too small ({size}B)"
    return True, f"{size//1024}KB"


def download_one(url, retries=DEFAULT_RETRIES):
    """
    Download media from a single X URL. Returns (image_paths, video_path, errors).
    All files go to TMP_DIR first, then caller moves them.
    """
    images = []
    video = None
    errors = []

    # Clean tmp dir
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

    for attempt in range(1, retries + 1):
        if attempt > 1:
            wait = DELAY_BASE * (2 ** attempt)
            print(f"    Retry {attempt}/{retries} after {wait}s...")
            time.sleep(wait)
            # Clean tmp for retry
            if TMP_DIR.exists():
                shutil.rmtree(TMP_DIR)
            TMP_DIR.mkdir(parents=True, exist_ok=True)

        # First, test if media exists (dry run)
        dry_cmd = ["gallery-dl", "--no-download", url]
        try:
            dry = subprocess.run(dry_cmd, capture_output=True, text=True, timeout=30)
        except subprocess.TimeoutExpired:
            errors.append(f"Attempt {attempt}: timed out checking media")
            continue

        if dry.returncode != 0:
            stderr = (dry.stderr or "").lower()
            if "not found" in stderr or "404" in stderr:
                errors.append(f"Attempt {attempt}: tweet not found")
                break
            errors.append(f"Attempt {attempt}: gallery-dl error: {dry.stderr[:120]}")
            continue

        # Count expected files
        expected = [l.strip() for l in dry.stdout.splitlines() if l.strip()]
        if not expected:
            errors.append(f"Attempt {attempt}: no media in tweet")
            continue

        print(f"    Found {len(expected)} media items, downloading...")

        # Download
        dl_cmd = ["gallery-dl", "-d", str(TMP_DIR), url]
        try:
            dl = subprocess.run(dl_cmd, capture_output=True, text=True, timeout=180)
        except subprocess.TimeoutExpired:
            errors.append(f"Attempt {attempt}: download timed out")
            continue

        # Find downloaded files recursively
        downloaded = list(TMP_DIR.rglob("*"))
        downloaded = [f for f in downloaded if f.is_file()]

        if not downloaded:
            errors.append(f"Attempt {attempt}: download produced no files")
            continue

        # Verify each file
        all_ok = True
        for fpath in downloaded:
            ok, reason = verify_file(fpath)
            if not ok:
                errors.append(f"Attempt {attempt}: {fpath.name} invalid ({reason})")
                all_ok = False
            else:
                ext = fpath.suffix.lower()
                if ext in ('.mp4', '.webm', '.mov'):
                    if video is None:
                        video = fpath
                else:
                    images.append(fpath)

        if all_ok and (images or video):
            return images, video, errors

    return [], None, errors


def move_to_media_dirs(images, video):
    """Move files from TMP_DIR to images/ and videos/. Returns (rel_paths, rel_video)."""
    IMAGES_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    img_rel = []
    vid_rel = None

    for src in images:
        # Rename to avoid conflicts: use tweet_id from path
        parent_dir = src.parent.name  # e.g., "MrLarus"
        dest_name = f"{parent_dir}_{src.name}"
        dest = IMAGES_DIR / dest_name
        # Avoid overwrite
        counter = 1
        while dest.exists():
            stem, ext = dest_name.rsplit('.', 1)
            dest = IMAGES_DIR / f"{stem}_{counter}.{ext}"
            counter += 1
        shutil.move(str(src), str(dest))
        img_rel.append(f"images/{dest.name}")

    if video:
        parent_dir = video.parent.name
        dest_name = f"{parent_dir}_{video.name}"
        dest = VIDEOS_DIR / dest_name
        counter = 1
        while dest.exists():
            stem, ext = dest_name.rsplit('.', 1)
            dest = VIDEOS_DIR / f"{stem}_{counter}.{ext}"
            counter += 1
        shutil.move(str(video), str(dest))
        vid_rel = f"videos/{dest.name}"

    # Clean tmp
    if TMP_DIR.exists():
        shutil.rmtree(TMP_DIR)

    return img_rel, vid_rel


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Download and verify media from X posts")
    parser.add_argument("--limit", type=int, default=0, help="Max prompts to process (0=all)")
    parser.add_argument("--retries", type=int, default=DEFAULT_RETRIES, help="Retries per prompt")
    parser.add_argument("--delay", type=int, default=DELAY_BASE, help="Base delay between requests")
    parser.add_argument("--force", action="store_true", help="Re-download even if media exists")
    parser.add_argument("--single", type=str, help="Download a single X URL for testing")
    args = parser.parse_args()

    # Single URL mode
    if args.single:
        print(f"Testing: {args.single}")
        images, video, errors = download_one(args.single, args.retries)
        if images or video:
            img_rel, vid_rel = move_to_media_dirs(images, video)
            print(f"  OK: {len(img_rel)} images, {'1 video' if vid_rel else '0 videos'}")
            for p in img_rel:
                fsize = (IMAGES_DIR / Path(p).name).stat().st_size // 1024
                print(f"    {p} ({fsize}KB)")
            if vid_rel:
                fsize = (VIDEOS_DIR / Path(vid_rel).name).stat().st_size // 1024
                print(f"    {vid_rel} ({fsize}KB)")
        for e in errors:
            print(f"  ERROR: {e}")
        if not images and not video and not errors:
            print("  No media found.")
        return

    # ========== MAIN FLOW ==========
    print("=" * 60)
    print("MrLarus Prompt Library — Media Download & Verification")
    print("=" * 60)

    if not check_prerequisites():
        print("\nInstall gallery-dl:")
        print("  pip install gallery-dl")
        sys.exit(1)

    data = load_data()
    print(f"\nLoaded {len(data)} prompts")

    # Build todo list
    todo = []
    for i, p in enumerate(data):
        link = p.get("link", "")
        if not link or ("x.com" not in link and "twitter.com" not in link):
            continue
        has_media = (p.get("images") and len(p["images"]) > 0) or p.get("video")
        if has_media and not args.force:
            continue
        todo.append(i)

    if not todo:
        print("All prompts already have media. Use --force to re-download.")
        return

    print(f"To download: {len(todo)} prompts")
    if args.limit > 0:
        todo = todo[:args.limit]
        print(f"Limited to first {args.limit}")

    # Process
    success = 0
    failed = []
    skipped = 0

    for idx, prompt_idx in enumerate(todo):
        p = data[prompt_idx]
        link = p.get("link", "")

        print(f"\n[{idx+1}/{len(todo)}] #{prompt_idx}: {p.get('title','')[:60]}")
        print(f"  {link}")

        images, video, errors = download_one(link, args.retries)

        for e in errors:
            print(f"  ! {e}")

        if images or video:
            img_rel, vid_rel = move_to_media_dirs(images, video)

            if img_rel:
                p.setdefault("images", [])
                p["images"].extend(img_rel)
            if vid_rel and not p.get("video"):
                p["video"] = vid_rel

            print(f"  OK: {len(img_rel)} images" + (f", 1 video" if vid_rel else ""))
            success += 1
            save_data(data)
        else:
            print(f"  FAILED after {args.retries} attempts")
            failed.append({
                "index": prompt_idx,
                "title": p.get("title", ""),
                "link": link,
                "errors": errors,
            })

        if idx < len(todo) - 1:
            time.sleep(args.delay)

    # ===== REPORT =====
    print("\n" + "=" * 60)
    print("DOWNLOAD REPORT")
    print("=" * 60)
    total_imgs = sum(len(p.get("images", [])) for p in data)
    total_vids = sum(1 for p in data if p.get("video"))
    print(f"  Total media in library: {total_imgs} images, {total_vids} videos")
    print(f"  This run: {success} succeeded, {len(failed)} failed")

    save_data(data)

    if failed:
        print(f"\nFAILED ({len(failed)} items — need manual handling):")
        with open(FAILURE_LOG, "w", encoding="utf-8") as f:
            f.write("# Failed downloads — open each link and download manually\n\n")
            for item in failed:
                print(f"  #{item['index']}: {item['link']}")
                f.write(f"#{item['index']}: {item['link']}\n")
                for e in item['errors']:
                    f.write(f"  {e}\n")
                f.write("\n")
        print(f"\nSaved to: {FAILURE_LOG}")

    print(f"\nNext: python scripts/build_html.py && git push")


if __name__ == "__main__":
    main()
