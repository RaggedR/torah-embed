"""Regenerate the train/test split. Deterministic (seed 7). Persists to bert/data/."""
import json,re,gzip,os,collections,random
random.seed(7)
D=os.path.expanduser('~/torah/bert/data')
corpus=json.load(gzip.open(f'{D}/bavli_en.json.gz','rt'))
src=json.load(gzip.open(f'{D}/sources_en.json.gz','rt'))
pairs=json.load(open(f'{D}/gold_pairs.json'))
def expand(ref):
    m=re.match(r'^(.*?)\s+(\d+[ab])(?::(\d+)(?:-(\d+))?)?$',ref)
    if not m: return []
    t,daf,s1,s2=m.groups()
    if s1 is None: return [k for k in corpus if k.startswith(f"{t} {daf}:")]
    a,b=int(s1),int(s2) if s2 else int(s1)
    return [f"{t} {daf}:{i}" for i in range(a,b+1) if f"{t} {daf}:{i}" in corpus]
q2t=collections.defaultdict(set)
for a,b in pairs:
    if not a.startswith('Mishneh Torah') or a not in src: continue
    e=expand(b)
    if e: q2t[a]|=set(e)
print(f"MT queries with resolvable targets: {len(q2t):,}")
def tr(r): return r.rsplit(' ',1)[0]
qt=collections.Counter()
for q,ts in q2t.items():
    for t in {tr(x) for x in ts}: qt[t]+=1
tot=len(q2t); held=[]; acc=0
for t,n in sorted(qt.items(),key=lambda x:-x[1])[4:]:
    if acc+n>0.18*tot: continue
    held.append(t); acc+=n
    if acc>0.13*tot: break
held=set(held)
train,test=[],[]
for q,ts in q2t.items():
    tt={tr(x) for x in ts}
    if tt<=held: test.append(q)
    elif tt&held: pass
    else: train.append(q)
print(f"held out: {sorted(held)}")
print(f"train {len(train):,}  test {len(test):,}  discarded(mixed) {len(q2t)-len(train)-len(test):,}")
out={"train":{q:sorted(q2t[q]) for q in train},"test":{q:sorted(q2t[q]) for q in test},
     "held_out_tractates":sorted(held)}
json.dump(out,gzip.open(f'{D}/split.json.gz','wt'))
print(f"train pairs: {sum(len(v) for v in out['train'].values()):,}  -> persisted")
