import subprocess, json, shutil
from pathlib import Path

url = "https://x.com/MrLarus/status/2049495868873531629"
tmp = Path(r"C:\Users\jding\Desktop\prompt-library\.dl_check")
if tmp.exists():
    shutil.rmtree(tmp)
tmp.mkdir(exist_ok=True)

r = subprocess.run(
    ["gallery-dl", "--no-download", "--write-info-json", "-d", str(tmp), url],
    capture_output=True, text=True, timeout=60
)

jf = list(tmp.rglob("info.json"))
if jf:
    meta = json.load(open(jf[0], "r", encoding="utf-8"))
    print(f"Author: {meta['author']['name']}")
    print(f"Date: {meta['date']}")
    print(f"Content ({len(meta['content'])} chars):")
    print(meta['content'])
    print(f"\nMedia count: {meta.get('count', 0)}")
else:
    print(f"FAILED: {r.stderr[:300]}")
shutil.rmtree(tmp)
