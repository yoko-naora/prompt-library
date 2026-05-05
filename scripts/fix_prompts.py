"""Fix entries with empty prompts by re-fetching and properly extracting."""
import json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\jding\Desktop\prompt-library")
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"

def fetch_tweet(url):
    tmp = ROOT / ".dl_fix"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    subprocess.run(["gallery-dl", "--no-download", "--write-info-json", "-d", str(tmp), url],
                   capture_output=True, text=True, timeout=90)
    subprocess.run(["gallery-dl", "-d", str(tmp), url],
                   capture_output=True, text=True, timeout=180)

    json_files = list(tmp.rglob("info.json"))
    content = ""
    if json_files:
        with open(json_files[0], "r", encoding="utf-8") as f:
            meta = json.load(f)
        content = meta.get("content", "")

    media_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
    media_files = [f for f in tmp.rglob("*") if f.is_file() and f.suffix.lower() in media_exts]
    images = []
    video = None
    author = "unknown"
    if json_files:
        author = meta.get("author", {}).get("name", "unknown")

    for mf in media_files:
        ext = mf.suffix.lower()
        dest_name = f"{author}_{mf.name}"
        if ext in ('.mp4', '.webm', '.mov'):
            dest = VIDEOS_DIR / dest_name
            shutil.move(str(mf), str(dest))
            if not video:
                video = f"videos/{dest_name}"
        else:
            dest = IMAGES_DIR / dest_name
            shutil.move(str(mf), str(dest))
            images.append(f"images/{dest_name}")

    if tmp.exists():
        shutil.rmtree(tmp)

    return {"content": content, "images": images, "video": video}


def extract_image_prompt(text):
    """Extract image prompt from a Step 1 tweet."""
    # Remove the "Step 1｜..." header
    text = re.sub(r'(?i)^step\s*1\s*[｜|:：].*?\n', '', text.strip(), count=1)
    text = text.strip()

    # Find the actual prompt: look for "Prompt：" or "请创作" which marks the start
    # For tweets that START with the prompt directly (no header), use full text
    # Pattern: the prompt usually starts with "请创作" or after "Prompt："
    m = re.search(r'(?i)(?:Prompt|提示词)\s*[：:]\s*\n?(.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # If "请创作" is the marker, return from there
    m = re.search(r'(请创作.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: return the text after the first header/blank line
    # Often the tweet intro is 1-2 lines, then the prompt follows
    lines = text.split('\n')
    # Skip intro lines (usually starting with "先用", "重点", "当然")
    prompt_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped:
            prompt_start = i + 1
            break
        if stripped.startswith(('Prompt', '提示词', '请创作', '请根据', '创作', '生成')):
            prompt_start = i
            break

    if prompt_start > 0:
        return '\n'.join(lines[prompt_start:]).strip()

    return text


def extract_video_prompt(text):
    """Extract video prompt from a Step 2 tweet."""
    # Remove "Step 2｜..." header
    text = re.sub(r'(?i)^step\s*2\s*[｜|:：].*?\n', '', text.strip(), count=1)
    text = text.strip()

    # Find the actual prompt
    m = re.search(r'(?i)(?:Prompt|提示词)\s*[：:]\s*\n?(.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Look for "请根据" or similar prompt starters
    m = re.search(r'(请根据.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: return text after intro
    lines = text.split('\n')
    prompt_start = 0
    for i, line in enumerate(lines):
        stripped = line.strip()
        if stripped.startswith(('Prompt', '提示词', '请根据', '核心要求')):
            prompt_start = i
            break

    if prompt_start > 0:
        return '\n'.join(lines[prompt_start:]).strip()

    return text


with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

fixes = 0
for i, entry in enumerate(data):
    needs_fix = False

    # Check for entries with empty image_prompt that have images (video type with missing prompt)
    if entry.get("type") == "video" and not entry.get("image_prompt", "").strip():
        needs_fix = True
        # Try to find image_prompt from the entry's link or related tweets
        # We need the original IMG URL which is stored... but where?
        # For now, print which entries still have issues
        print(f"#{i} [{entry.get('author')}] {entry.get('text','')[:50]}... image_prompt EMPTY")

    if entry.get("type") == "video" and not entry.get("video_prompt", "").strip():
        needs_fix = True
        print(f"#{i} [{entry.get('author')}] {entry.get('text','')[:50]}... video_prompt EMPTY")

    # Check for entries with no images
    if not entry.get("images"):
        if entry.get("link"):
            print(f"#{i} [{entry.get('author')}] {entry.get('text','')[:50]}... NO IMAGES, link={entry['link']}")

    # Check for entries with no video (type=video)
    if entry.get("type") == "video" and not entry.get("video", "").strip():
        print(f"#{i} [{entry.get('author')}] {entry.get('text','')[:50]}... NO VIDEO")

print(f"\nTotal entries: {len(data)}")
