import re, openpyxl
from pathlib import Path
import os

QUEUE_FILE = Path(os.environ["USERPROFILE"]) / "Desktop" / "prompt_queue.xlsx"
wb = openpyxl.load_workbook(QUEUE_FILE)
ws = wb["入列"]

deleted_nums = {42, 48, 49, 50, 54, 57, 62, 63, 64, 66}
updated_nums = {56, 58, 60, 65}
broken_nums = {81, 83, 84}  # indices from data.json that correspond to entries we had to delete

for row in ws.iter_rows(min_row=2):
    note_cell = row[7]
    note = (note_cell.value or "").strip() if note_cell.value else ""

    m = re.search(r'#(\d+)', note)
    has_url = row[3].value and str(row[3].value).strip()

    if m:
        num = int(m.group(1))
        if num in deleted_nums:
            row[0].value = "✅"  # Deleted successfully
        elif num in updated_nums and has_url:
            row[0].value = "✅"  # Updated successfully
        elif num in {43, 53, 55, 67}:
            pass  # Skipped, leave as ⬜
        else:
            row[0].value = "⬜"  # Not processed
    elif has_url and note:
        # New entries without #number
        if "霓裳羽衣舞" in note or "Food of Japan" in note:
            row[0].value = "✅"
        elif "西域胡旋舞" in note:
            row[0].value = "❌"  # Tweets deleted
            if not note.endswith("推文已删除"):
                note_cell.value = note + " 推文已删除"
        elif "街头篮球" in note:
            row[0].value = "❌"  # Tweets deleted
            if not note.endswith("推文已删除"):
                note_cell.value = note + " 推文已删除"
        elif "街头花式足球" in note:
            row[0].value = "❌"  # Tweets deleted
            if not note.endswith("推文已删除"):
                note_cell.value = note + " 推文已删除"
        elif "黑白光学" in note:
            row[0].value = "⚠️"  # Partial (has images but no prompt URLs)

wb.save(QUEUE_FILE)
print("Excel updated!")

# Print summary of what was done
print("\nSummary:")
print(f"  Deleted from data.json: {len(deleted_nums)} entries")
print(f"  Updated with image_prompt: {len(updated_nums)} entries")
print(f"  Newly added: 2 (霓裳羽衣舞 + Food of Japan)")
print(f"  Failed (tweets deleted): 3 (西域胡旋舞, 街头篮球, 街头花式足球)")
print(f"  Partial: 1 (黑白光学概念海报 - has images, needs prompt)")
print(f"  Skipped (no new URLs): 4 (#43, #53, #55, #67)")
