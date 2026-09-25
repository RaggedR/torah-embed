import json,urllib.request,urllib.parse,os,sys
from concurrent.futures import ThreadPoolExecutor
os.makedirs("linkcache",exist_ok=True)
books=json.load(open("books.json"))
targets=[b for b in books["mt"] if not any(x in b for x in ["Positive Mitzvot","Negative Mitzvot","Overview","Transmission"])] \
      + [b for b in books["sa"] if "Introduction" not in b]
def fetch(ref):
    p="linkcache/"+urllib.parse.quote(ref,safe="")+".json"
    if os.path.exists(p):
        try: return ref,json.load(open(p))
        except Exception: pass
    u="https://www.sefaria.org/api/links/"+urllib.parse.quote(ref)+"?with_text=0"
    try:
        d=json.load(urllib.request.urlopen(u,timeout=180))
        if isinstance(d,list):
            json.dump(d,open(p,"w")); return ref,d
    except Exception as e:
        sys.stderr.write(f"fail {ref}: {str(e)[:50]}\n")
    return ref,[]
print(f"crawling {len(targets)} books...", flush=True)
done=0
with ThreadPoolExecutor(max_workers=6) as ex:
    for ref,d in ex.map(fetch,targets):
        done+=1
        if done%20==0: print(f"  {done}/{len(targets)}",flush=True)
print("done",done)
