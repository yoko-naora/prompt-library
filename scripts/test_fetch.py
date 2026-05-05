import subprocess, json, shutil
from pathlib import Path

urls = [
    "https://x.com/MrLarus/status/2051335394550022441",
    "https://x.com/MrLarus/status/2050505920740798683",
    "https://x.com/MrLarus/status/2051002066735071574",
]

for url in urls:
    tmp = Path(r"C:\Users\jding\Desktop\prompt-library\.dl_test")
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
        c = meta.get("content", "")
        print(f"OK: {url[-20:]} | author={meta['author']['name']} | {len(c)} chars")
        print(f"  first line: {c[:100]}")
    else:
        print(f"FAIL: {url[-20:]}")
        print(f"  stderr: {r.stderr[:200]}")
    shutil.rmtree(tmp)
    print()
