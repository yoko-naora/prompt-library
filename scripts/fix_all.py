"""
Fix all new/updated entries: re-fetch tweets, properly extract prompts, update data.json.
"""
import json, re, shutil, subprocess
from pathlib import Path

ROOT = Path(r"C:\Users\jding\Desktop\prompt-library")
DATA_FILE = ROOT / "data.json"
IMAGES_DIR = ROOT / "images"
VIDEOS_DIR = ROOT / "videos"

def fetch_tweet(url):
    """Fetch tweet content + media. Returns dict or None if failed."""
    tmp = ROOT / ".dl_fix2"
    if tmp.exists():
        shutil.rmtree(tmp)
    tmp.mkdir(parents=True)

    r1 = subprocess.run(
        ["gallery-dl", "--no-download", "--write-info-json", "-d", str(tmp), url],
        capture_output=True, text=True, timeout=90
    )
    if "No results" in r1.stderr or "no results" in r1.stdout:
        return None

    subprocess.run(
        ["gallery-dl", "-d", str(tmp), url],
        capture_output=True, text=True, timeout=180
    )

    jf = list(tmp.rglob("info.json"))
    if not jf:
        return None

    with open(jf[0], "r", encoding="utf-8") as f:
        meta = json.load(f)

    content = meta.get("content", "")
    author = meta.get("author", {}).get("name", "unknown")
    date = meta.get("date", "")

    media_exts = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.mp4', '.webm', '.mov'}
    media_files = [f for f in tmp.rglob("*") if f.is_file() and f.suffix.lower() in media_exts]

    images = []
    video = None
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

    shutil.rmtree(tmp)
    return {"content": content, "author": f"@{author}", "date": date,
            "images": images, "video": video}


def extract_image_prompt_from_step1(text):
    """Extract GPT-Image2 prompt from a Step 1 tweet."""
    if not text:
        return ""
    # Remove "Step 1｜title" header line
    text = re.sub(r'(?i)^step\s*1\s*[｜|:：].*?\n', '', text.strip())
    text = text.strip()

    # Find the prompt: look for "Prompt：" / "Please create" / "请创作"
    m = re.search(r'(?i)(?:Prompt|提示词)\s*[：:]\s*\n?(.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    m = re.search(r'(请创作.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: skip intro lines (usually describing "先用ChatGPT规划...")
    lines = text.split('\n')
    intro_keywords = ('先用', '重点不是', '当然，', '把第', '上传到')
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not any(s.startswith(k) for k in intro_keywords):
            return '\n'.join(lines[i:]).strip()

    return text


def extract_video_prompt_from_step2(text):
    """Extract Seedance prompt from a Step 2 tweet."""
    if not text:
        return ""
    # Remove "Step 2｜title" header line
    text = re.sub(r'(?i)^step\s*2\s*[｜|:：].*?\n', '', text.strip())
    text = text.strip()

    # Find the prompt
    m = re.search(r'(?i)(?:Prompt|提示词)\s*[：:]\s*\n?(.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    m = re.search(r'(请根据.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()

    # Fallback: skip intro
    lines = text.split('\n')
    intro_keywords = ('把第', '上传到', '先用', '重点')
    for i, line in enumerate(lines):
        s = line.strip()
        if s and not any(s.startswith(k) for k in intro_keywords):
            return '\n'.join(lines[i:]).strip()

    return text


def extract_prompt_single(text, ptype):
    """Extract prompt from a single (English) tweet."""
    if not text:
        return ""
    m = re.search(r'(?i)(?:prompt|提示词)\s*[：:]\s*\n?(.+)', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text


# Load data
with open(DATA_FILE, "r", encoding="utf-8") as f:
    data = json.load(f)

# Fix entries by index
fixes = {
    # Index: { "img_url": ..., "vid_url": ..., "final_url": ... }
    79: {
        "img_url": "https://x.com/MrLarus/status/2051002066735071574",
        "vid_url": "https://x.com/MrLarus/status/2051002488745046029",
        "final_url": "https://x.com/MrLarus/status/2051335394550022441",
    },
    80: {
        # Food of Japan - single EN tweet, already OK but check
        "img_url": "",
        "vid_url": "",
        "final_url": "https://x.com/AIwithSynthia/status/2051311862265102635",
    },
    81: {
        "img_url": "https://x.com/MrLarus/status/2050506323603702139",
        "vid_url": "https://x.com/MrLarus/status/2050505920740798683",
        "final_url": "https://x.com/MrLarus/status/2050505920740798683",
    },
    82: {
        "img_url": "",
        "vid_url": "https://x.com/MrLarus/status/2049495868873531629",
        "final_url": "https://x.com/MrLarus/status/2049496194586382563",
    },
    83: {
        "img_url": "https://x.com/MrLarus/status/2051336194860941619",
        "vid_url": "https://x.com/MrLarus/status/2051335394550022441",
        "final_url": "https://x.com/MrLarus/status/2051335835962814752",
    },
    84: {
        "img_url": "https://x.com/MrLarus/status/2050524635259715632",
        "vid_url": "https://x.com/MrLarus/status/2050523376314142978",
        "final_url": "https://x.com/MrLarus/status/2050524226717679949",
    },
}

for idx, urls in fixes.items():
    if idx >= len(data):
        print(f"#{idx}: OUT OF RANGE (data has {len(data)} entries)")
        continue

    entry = data[idx]
    print(f"\n=== Fixing #{idx}: {entry.get('author','?')} ===")

    # Fetch final tweet (for media + title)
    final_url = urls["final_url"]
    if final_url:
        result = fetch_tweet(final_url)
        if result:
            entry["text"] = result["content"]
            entry["title"] = result["date"]
            entry["author"] = result["author"]
            if result["images"]:
                entry["images"] = list(set(entry.get("images", []) + result["images"]))
            if result["video"] and not entry.get("video"):
                entry["video"] = result["video"]
            print(f"  FINAL OK: {len(result['images'])} images, video={bool(result['video'])}")
        else:
            print(f"  FINAL FAILED: {final_url}")

    # Fetch image prompt tweet
    img_url = urls["img_url"]
    if img_url and img_url != final_url:
        result = fetch_tweet(img_url)
        if result:
            ip = extract_image_prompt_from_step1(result["content"])
            if ip:
                entry["image_prompt"] = ip
                print(f"  IMG OK: image_prompt={len(ip)} chars")
            else:
                print(f"  IMG WARNING: could not extract prompt from {len(result['content'])} chars")
            # Also add any images from this tweet
            if result["images"]:
                entry["images"] = list(set(entry.get("images", []) + result["images"]))
        else:
            print(f"  IMG FAILED: {img_url}")

    # Fetch video prompt tweet
    vid_url = urls["vid_url"]
    if vid_url:
        result = fetch_tweet(vid_url)
        if result:
            # Check if this is a Step 2 tweet or a showcase tweet
            content = result["content"]
            if re.search(r'(?i)step\s*2', content):
                vp = extract_video_prompt_from_step2(content)
                if vp:
                    entry["video_prompt"] = vp
                    print(f"  VID OK (Step2): video_prompt={len(vp)} chars")
            elif "Seedance" in content and ("Prompt" in content or "提示词" in content or "请根据" in content):
                vp = extract_video_prompt_from_step2(content)
                if vp:
                    entry["video_prompt"] = vp
                    print(f"  VID OK (has prompt): video_prompt={len(vp)} chars")
                else:
                    print(f"  VID: Seedance tweet but couldn't extract prompt")
            else:
                # This might be a showcase tweet, not a prompt tweet
                # Don't use it as video_prompt
                print(f"  VID: looks like showcase tweet, not using as video_prompt")

            if result["video"] and not entry.get("video"):
                entry["video"] = result["video"]
            if result["images"]:
                entry["images"] = list(set(entry.get("images", []) + result["images"]))
        else:
            print(f"  VID FAILED: {vid_url}")

    # Determine type
    if entry.get("video") or entry.get("video_prompt"):
        entry["type"] = "video"
    elif entry.get("image_prompt"):
        entry["type"] = "image"

    print(f"  RESULT: images={len(entry.get('images',[]))} video={bool(entry.get('video'))} "
          f"ip={len(entry.get('image_prompt',''))} vp={len(entry.get('video_prompt',''))}")

# Save
with open(DATA_FILE, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\n=== Done! {len(data)} entries ===")
