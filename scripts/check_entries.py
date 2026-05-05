import json
with open(r'C:\Users\jding\Desktop\prompt-library\data.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for i in range(max(0, len(data)-8), len(data)):
    e = data[i]
    print(f'--- #{i} ---')
    print(f'  author={e.get("author")} cat={e.get("cat")} type={e.get("type")}')
    print(f'  title={e.get("title","")[:60]}')
    print(f'  link={e.get("link","")}')
    print(f'  images={len(e.get("images",[]))} video={bool(e.get("video",""))}')
    ip = e.get("image_prompt","")
    vp = e.get("video_prompt","")
    print(f'  image_prompt={len(ip)} chars: {ip[:150]}')
    print(f'  video_prompt={len(vp)} chars: {vp[:150]}')
    print()
