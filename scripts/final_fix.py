import json

with open(r"C:\Users\jding\Desktop\prompt-library\data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Fix #81 (now the 黑白光学概念海报 entry)
e = data[81]
e["type"] = "image"
e["author"] = "@MrLarus"
# Use the showcase text as image_prompt since it describes the concept well
e["image_prompt"] = e.get("text", "")
e["title"] = "2026-04-29 14:27:47"

# Also clean up: for entries that have video but no video_prompt,
# and entries that are type=video but really only have image_prompt
for i, entry in enumerate(data):
    if entry.get("type") == "video" and not entry.get("video") and not entry.get("video_prompt"):
        if entry.get("image_prompt"):
            entry["type"] = "image"

with open(r"C:\Users\jding\Desktop\prompt-library\data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"Done! {len(data)} entries")

# Print summary
video_count = sum(1 for e in data if e.get("type") == "video")
image_count = sum(1 for e in data if e.get("type") == "image")
with_ip = sum(1 for e in data if e.get("image_prompt", "").strip())
with_vp = sum(1 for e in data if e.get("video_prompt", "").strip())
with_imgs = sum(1 for e in data if e.get("images"))
with_vid = sum(1 for e in data if e.get("video", "").strip())
print(f"video={video_count} image={image_count}")
print(f"has_image_prompt={with_ip} has_video_prompt={with_vp}")
print(f"has_images={with_imgs} has_video_file={with_vid}")
