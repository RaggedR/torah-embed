import json,urllib.request,urllib.parse,os,sys
from concurrent.futures import ThreadPoolExecutor
os.makedirs("linkcache",exist_ok=True)
def get(url,t=120):
    return json.load(urllib.request.urlopen(url,timeout=t))
def fetch(ref):
    p="linkcache/"+urllib.parse.quote(ref,safe="")+".json"
    if os.path.exists(p):
        try: return json.load(open(p))
        except Exception: pass
    try:
        d=get("https://www.sefaria.org/api/links/"+urllib.parse.quote(ref)+"?with_text=0",180)
        if isinstance(d,list): json.dump(d,open(p,"w")); return d
    except Exception as e: sys.stderr.write(f"fail {ref}: {str(e)[:40]}\n")
    return []
# Shulchan Arukh: per-siman
SA=["Shulchan Arukh, Orach Chayim","Shulchan Arukh, Yoreh De'ah","Shulchan Arukh, Even HaEzer","Shulchan Arukh, Choshen Mishpat"]
refs=[]
for b in SA:
    try:
        ix=get("https://www.sefaria.org/api/index/"+urllib.parse.quote(b))
        n=(ix.get("schema",{}).get("lengths") or [0])[0]
    except Exception: n=0
    print(f"  {b}: {n} simanim",flush=True)
    refs+=[f"{b} {i}" for i in range(1,n+1)]
# Mishnah whole-book
toc=json.load(open('toc.json'))
def walk(nodes,path=()):
    for n in nodes:
        if 'contents' in n: yield from walk(n['contents'],path+(n.get('category',''),))
        else: yield path,n.get('title')
MISH=[t for p,t in walk(toc) if t and p and p[0]=='Mishnah' and t.startswith('Mishnah ') and ' on ' not in t and 'Commentary' not in p]
print(f"  Mishnah books: {len(MISH)}",flush=True)
refs+=MISH
print(f"fetching {len(refs)} refs...",flush=True)
done=0
with ThreadPoolExecutor(max_workers=6) as ex:
    for _ in ex.map(fetch,refs):
        done+=1
        if done%250==0: print(f"  {done}/{len(refs)}",flush=True)
print("done",done)
