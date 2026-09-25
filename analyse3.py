import json,os,urllib.parse,collections
toc=json.load(open('toc.json'))
def walk(nodes,path=()):
    for n in nodes:
        if 'contents' in n: yield from walk(n['contents'],path+(n.get('category',''),))
        else: yield path,n.get('title')
TRACT={t for p,t in walk(toc) if t and len(p)>=3 and p[0]=='Talmud' and p[1]=='Bavli'
       and p[2].startswith('Seder') and 'Commentary' not in p and ' on ' not in t}
def census(pred,label):
    pairs=set(); anch=set(); tgt=set(); typ=collections.Counter()
    for f in os.listdir('linkcache'):
        src=urllib.parse.unquote(f[:-5])
        if not pred(src): continue
        for l in json.load(open('linkcache/'+f)):
            if l.get('index_title') in TRACT:
                a=l.get('anchorRef') or l.get('sourceRef') or ''
                pairs.add((a,l['ref'])); anch.add(a); tgt.add(l['ref']); typ[l.get('type','?')]+=1
    print(f"\n=== {label} -> Bavli ===")
    print(f"  unique pairs          : {len(pairs):,}")
    print(f"  distinct source segs  : {len(anch):,}")
    print(f"  distinct Bavli targets: {len(tgt):,}")
    print("  types:", dict(typ.most_common(4)))
    return pairs,tgt
p1,t1=census(lambda s:s.startswith('Mishneh Torah'),"Mishneh Torah")
p2,t2=census(lambda s:s.startswith('Shulchan Arukh'),"Shulchan Arukh")
p3,t3=census(lambda s:s.startswith('Mishnah '),"Mishnah")
allp=p1|p2|p3; allt=t1|t2|t3
print(f"\n=== COMBINED GOLD SET ===")
print(f"  total unique cross-register pairs : {len(allp):,}")
print(f"  distinct Bavli segments covered   : {len(allt):,}")
json.dump({"mt":len(p1),"sa":len(p2),"mishnah":len(p3),"total":len(allp),
           "bavli_targets":len(allt)}, open('phase1_counts.json','w'))
json.dump(sorted(allp), open('gold_pairs.json','w'))
print("  saved -> gold_pairs.json, phase1_counts.json")
