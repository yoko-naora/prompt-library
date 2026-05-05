import json
with open(r"C:\Users\jding\Desktop\prompt-library\data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

# Delete broken entries (highest index first)
# #84: FINAL+IMG dead | #83: FINAL+IMG dead | #81: ALL dead
to_delete = [84, 83, 81]
for idx in sorted(to_delete, reverse=True):
    e = data[idx]
    print(f"Deleting #{idx}: {e.get('author')} {e.get('link','')[:60]}")
    del data[idx]

with open(r"C:\Users\jding\Desktop\prompt-library\data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)
print(f"Done! {len(data)} entries remaining")
