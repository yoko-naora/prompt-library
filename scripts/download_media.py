#!/usr/bin/env python3
"""
Download and VERIFY media from MrLarus X posts.
- Downloads images/videos via yt-dlp
- Verifies every file (size > 0, valid format)
- Retries failed downloads up to 3 times
- Only writes to data.json after verification
- Prints clear success/failure report

Requirements: pip install yt-dlp
Usage: python scripts/download_media.py [--limit N] [--retries N]
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
FAILURE_LOG = ROOT / "download_failures.txt"

DEFAULT_RETRIES = 3
DELAY_BASE = 5  # seconds between requests


def check_prerequisites():
    """Verify yt-dlp is installed."""
    try:
        r = subprocess.run(["yt-dlp", "--version"], capture_output=True, text=True, timeout=10)
        if r.returncode == 0:
            print(f"  yt-dlp version: {r.stdout.strip()}")
            return True
    except FileNotFoundError:
        pass
    print("ERROR: yt-dlp not found. Install with: pip install yt-dlp")
    return False


def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def sanitize(s, max_len=50):
    s = re.sub(r'[<>:"/\\|?*]', '', s)
    s = re.sub(r'\s+', '_', s.strip())
    return s[:max_len]


def verify_file(filepath):
    """Check that a downloaded file is valid (exists, non-empty, right extension)."""
    path = Path(filepath)
    if not path.exists():
        return False, "file not found"
    if path.stat().st_size == 0:
        path.unlink()  # Remove empty file
        return False, "empty file (0 bytes)"
    ext = path.suffix.lower()
    valid = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
    if ext not in valid:
        return False, f"unexpected extension: {ext}"
    if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
        if path.stat().st_size < 500:
            path.unlink()
            return False, f"image too small ({path.stat().st_size} bytes)"
    if ext in ('.mp4', '.webm', '.mov'):
        if path.stat().st_size < 5000:
            path.unlink()
            return False, f"video too small ({path.stat().st_size} bytes)"
    return True, "ok"


def download_one(url, output_dir, base_name, retries=DEFAULT_RETRIES):
    """
    Download all media from a single URL using yt-dlp.
    Returns (image_paths, video_path, errors).
    """
    images = []
    video = None
    errors = []

    output_template = str(output_dir / f"{base_name}_%(autonumber)02d.%(ext)s")

    for attempt in range(1, retries + 1):
        if attempt > 1:
            wait = DELAY_BASE * (2 ** attempt)
            print(f"    Retry {attempt}/{retries} after {wait}s...")
            time.sleep(wait)

        # Record existing files before download
        before = set()
        for f in output_dir.iterdir():
            if f.name.startswith(base_name):
                before.add(f.name)

        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--no-mtime",
            "-o", output_template,
            "--restrict-filenames",
            "--socket-timeout", "30",
            "--retries", "3",
            "--fragment-retries", "3",
        ]

        # For X/Twitter, try loading cookies from browser if available
        # This helps with authentication
        cmd.extend([url])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True, text=True,
                timeout=180,
                cwd=str(output_dir)
            )
        except subprocess.TimeoutExpired:
            errors.append(f"Attempt {attempt}: download timed out")
            continue
        except Exception as e:
            errors.append(f"Attempt {attempt}: {e}")
            continue

        # Find new files
        after = set()
        for f in output_dir.iterdir():
            if f.name.startswith(base_name):
                after.add(f.name)

        new_files = after - before

        if not new_files:
            # Check if yt-dlp output indicates auth issue
            stderr = result.stderr.lower() if result.stderr else ""
            stdout = result.stdout.lower() if result.stdout else ""

            if "login" in stderr or "login" in stdout or "protected" in stderr:
                errors.append(f"Attempt {attempt}: X requires login/cookies. "
                              f"Run: yt-dlp --cookies-from-browser chrome {url}")
            elif "not found" in stderr or "404" in stderr:
                errors.append(f"Attempt {attempt}: tweet not found or deleted")
                break  # Don't retry 404s
            else:
                errors.append(f"Attempt {attempt}: no media found in tweet")
            continue

        # Verify each downloaded file
        all_ok = True
        for fname in sorted(new_files):
            fpath = output_dir / fname
            ok, reason = verify_file(fpath)

            if not ok:
                errors.append(f"Attempt {attempt}: {fname} invalid ({reason})")
                all_ok = False
                continue

            ext = fpath.suffix.lower()
            if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
                images.append(fname)
            elif ext in ('.mp4', '.webm', '.mov'):
                if video is None:
                    video = fname

        if all_ok and (images or video):
            return images, video, errors

        # If we got here, some files failed verification — clean up and retry
        for fname in new_files:
            fpath = output_dir / fname
            if fpath.exists():
                fpath.unlink()

    return [], None, errors


def organize_files(new_files, base_dir, images_dir, videos_dir):
    """Move downloaded files to images/ and videos/ directories."""
    image_paths = []
    video_path = None

    for fname in new_files:
        src = base_dir / fname
        if not src.exists():
            continue
        ext = src.suffix.lower()
        if ext in ('.jpg', '.jpeg', '.png', '.gif', '.webp'):
            dest = images_dir / fname
            src.rename(dest)
            image_paths.append(f"images/{fname}")
        elif ext in ('.mp4', '.webm', '.mov'):
            dest = videos_dir / fname
            src.rename(dest)
            video_path = f"videos/{fname}"

    return image_paths, video_path


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
        print(f"Testing download of: {args.single}")
        IMAGES_DIR.mkdir(exist_ok=True)
        VIDEOS_DIR.mkdir(exist_ok=True)
        imgs, vid, errs = download_one(args.single, ROOT, "test", args.retries)
        if imgs or vid:
            print(f"  SUCCESS: {len(imgs)} images, {'1 video' if vid else 'no video'}")
            organize_files(imgs + ([vid] if vid else []), ROOT, IMAGES_DIR, VIDEOS_DIR)
        for e in errs:
            print(f"  ERROR: {e}")
        return

    # ========== MAIN FLOW ==========
    print("=" * 60)
    print("MrLarus Prompt Library — Media Download & Verification")
    print("=" * 60)

    if not check_prerequisites():
        print("\nInstall yt-dlp first:")
        print("  pip install yt-dlp")
        print("\nOr if using cookies for X authentication:")
        print("  yt-dlp --cookies-from-browser chrome <url>")
        sys.exit(1)

    data = load_data()
    print(f"\nLoaded {len(data)} prompts")

    IMAGES_DIR.mkdir(exist_ok=True)
    VIDEOS_DIR.mkdir(exist_ok=True)

    # ===== BUILD TODO LIST =====
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

    # ===== PROCESS =====
    success = 0
    failed = []
    skipped_no_link = 0

    for idx, prompt_idx in enumerate(todo):
        p = data[prompt_idx]
        link = p.get("link", "")

        print(f"\n[{idx+1}/{len(todo)}] #{prompt_idx}: {p.get('title','')[:60]}")
        print(f"  URL: {link}")

        base_name = sanitize(f"{prompt_idx:03d}")
        imgs, vid, errors = download_one(link, ROOT, base_name, args.retries)

        if errors:
            for e in errors:
                print(f"  ! {e}")

        if imgs or vid:
            # Move to proper directories
            all_files = imgs + ([vid] if vid else [])
            img_paths, vid_path = organize_files(all_files, ROOT, IMAGES_DIR, VIDEOS_DIR)

            # Update data
            if img_paths:
                p.setdefault("images", [])
                p["images"].extend(img_paths)
            if vid_path and not p.get("video"):
                p["video"] = vid_path

            print(f"  OK: {len(img_paths)} images, {'1 video' if vid_path else '0 videos'}")
            success += 1

            # Save after each success
            save_data(data)
        else:
            print(f"  FAILED after {args.retries} attempts")
            failed.append({
                "index": prompt_idx,
                "title": p.get("title", ""),
                "link": link,
                "errors": errors
            })

        # Rate limit
        if idx < len(todo) - 1:
            time.sleep(args.delay)

    # ===== REPORT =====
    print("\n" + "=" * 60)
    print("DOWNLOAD REPORT")
    print("=" * 60)
    print(f"  Success:  {success}")
    print(f"  Failed:   {len(failed)}")
    print(f"  Total:    {len(todo)}")

    save_data(data)

    if failed:
        print(f"\nFAILED PROMPTS (need manual handling):")
        with open(FAILURE_LOG, "w", encoding="utf-8") as f:
            f.write("# Failed downloads — need manual handling\n\n")
            for item in failed:
                msg = f"  #{item['index']}: {item['link']}"
                print(msg)
                f.write(f"{msg}\n")
                for e in item['errors']:
                    print(f"      {e}")
                    f.write(f"      {e}\n")
                f.write("\n")
        print(f"\nFull list saved to: {FAILURE_LOG}")
        print("\nManual fix options:")
        print("  1. Open each link in browser, download media manually")
        print("  2. Place images in images/, videos in videos/")
        print("  3. Update data.json with paths")
        print("  4. Run: python scripts/build_html.py && git push")
    else:
        print("\nAll downloads successful!")
        if FAILURE_LOG.exists():
            FAILURE_LOG.unlink()

    print(f"\nNext steps:")
    print(f"  1. Review images/ and videos/ directories")
    print(f"  2. python scripts/build_html.py")
    print(f"  3. git add . && git commit -m 'Add media files' && git push")


if __name__ == "__main__":
    main()
