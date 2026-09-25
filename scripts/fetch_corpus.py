"""Fetch English Bavli + Mishneh Torah source texts from Sefaria. Persists to bert/data/."""
import json,urllib.request,urllib.parse,os,sys,gzip,re,collections
from concurrent.futures import ThreadPoolExecutor
DATA=os.path.expanduser('~/torah/bert/data')
os.makedirs(DATA,exist_ok=True)
def api(u,t=240): return json.load(urllib.request.urlopen(u,timeout=t))
def toc():
    p=f'{DATA}/toc.json.gz'
    if os.path.exists(p):
        return json.load(gzip.open(p,'rt'))
    d=api("https://www.sefaria.org/api/index/")
    json.dump(d,gzip.open(p,'wt')); return d
T=toc()
def walk(nodes,path=()):
    for n in nodes:
        if 'contents' in n: yield from walk(n['contents'],path+(n.get('category',''),))
        else: yield path,n.get('title')
TRACT=sorted({t for p,t in walk(T) if t and len(p)>=3 and p[0]=='Talmud' and p[1]=='Bavli'
              and p[2].startswith('Seder') and 'Commentary' not in p and ' on ' not in t})
def text(ref):
    u="https://www.sefaria.org/api/v3/texts/"+urllib.parse.quote(ref)+"?version=english&return_format=text_only"
    try:
        d=api(u); v=(d.get("versions") or [{}])[0]
        return ref,v.get("text",[])
    except Exception as e:
        sys.stderr.write(f"fail {ref}\n"); return ref,None
# --- Bavli corpus
print(f"fetching {len(TRACT)} tractates...",flush=True)
corpus={}
with ThreadPoolExecutor(max_workers=4) as ex:
    for ref,txt in ex.map(text,TRACT):
        if not txt: continue
        for i,daf in enumerate(txt):
            if not isinstance(daf,list): continue
            lbl=f"{(i//2)+1}{'a' if i%2==0 else 'b'}"
            for j,s in enumerate(daf):
                if isinstance(s,str) and s.strip(): corpus[f"{ref} {lbl}:{j+1}"]=s.strip()
print(f"  corpus segments: {len(corpus):,}")
json.dump(corpus,gzip.open(f'{DATA}/bavli_en.json.gz','wt'))
# --- source books referenced by gold pairs
pairs=json.load(open(f'{DATA}/gold_pairs.json'))
def book(r):
    m=re.match(r'^(.*?)\s+\d+(:\d+)?$',r); return m.group(1) if m else None
books=sorted({book(a) for a,_ in pairs if book(a)})
print(f"fetching {len(books)} source books...",flush=True)
src={}
with ThreadPoolExecutor(max_workers=4) as ex:
    for ref,txt in ex.map(text,books):
        if not txt: continue
        for i,ch in enumerate(txt):
            if not isinstance(ch,list): continue
            for j,s in enumerate(ch):
                if isinstance(s,str) and s.strip(): src[f"{ref} {i+1}:{j+1}"]=s.strip()
print(f"  source segments: {len(src):,}")
json.dump(src,gzip.open(f'{DATA}/sources_en.json.gz','wt'))
print("persisted to",DATA)
