"""Evaluate a retrieval model on the held-out split. Reports BM25 / zero-shot / fine-tuned,
on ruling-shaped AND question-shaped queries, strict and sugya-relaxed credit (D26, D43-45)."""
import json,gzip,os,re,math,glob,collections,statistics,argparse,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import memguard
D=os.path.expanduser('~/torah/bert/data')
ap=argparse.ArgumentParser()
ap.add_argument('--model',default='BAAI/bge-base-en-v1.5')
ap.add_argument('--label',default='zero-shot')
ap.add_argument('--bm25',action='store_true',help='also score BM25')
ap.add_argument('--out',default=f'{D}/eval_results.json')
a=ap.parse_args()
memguard.require(3.0,'for evaluation')
import numpy as np
from scipy.sparse import csr_matrix
corpus=json.load(gzip.open(f'{D}/bavli_en.json.gz','rt'))
src=json.load(gzip.open(f'{D}/sources_en.json.gz','rt'))
test=json.load(gzip.open(f'{D}/split.json.gz','rt'))['test']
QT={}
for f in glob.glob(f'{D}/questions_test_*.json'):
    for x in json.load(open(f)):
        QT[x['id']]=x
keys=list(corpus); kidx={k:i for i,k in enumerate(keys)}
qs=[q for q in sorted(test) if q in src]
print(f"test queries: {len(qs)}  with questions: {sum(1 for q in qs if q in QT)}",flush=True)
def tok(s): return re.findall(r'[a-z]+',s.lower())
def neigh(ref,w=3):
    m=re.match(r'^(.*):(\d+)$',ref)
    if not m: return []
    b,n=m.group(1),int(m.group(2))
    return [kidx[f"{b}:{n+d}"] for d in range(-w,w+1) if f"{b}:{n+d}" in kidx]
res=collections.defaultdict(lambda: collections.defaultdict(list))
def score(name,form,ranks):
    for rk in ranks:
        o=res[(name,form)]
        o['mrr'].append(1/rk if rk else 0); o['r1'].append(1.0 if rk==1 else 0)
        o['r10'].append(1.0 if rk and rk<=10 else 0)
def forms(q):
    out=[('ruling',src[q])]
    if q in QT:
        out.append(('q_practical',QT[q]['q_practical']))
        out.append(('q_conceptual',QT[q]['q_conceptual']))
    return out
# ---- BM25
if a.bm25:
    docs=[tok(corpus[k]) for k in keys]; df=collections.Counter()
    for d in docs: df.update(set(d))
    N=len(docs); avgdl=sum(len(d) for d in docs)/N
    vocab={w:i for i,w in enumerate(df)}
    idf=np.array([math.log(1+(N-df[w]+0.5)/(df[w]+0.5)) for w in vocab],dtype=np.float32)
    k1,b=1.5,0.75; r_,c_,v_=[],[],[]
    for di,d in enumerate(docs):
        ct=collections.Counter(d); dl=len(d)
        for w,f in ct.items():
            r_.append(di); c_.append(vocab[w]); v_.append(f*(k1+1)/(f+k1*(1-b+b*dl/avgdl)))
    M=csr_matrix((v_,(r_,c_)),shape=(N,len(vocab)),dtype=np.float32).multiply(idf[None,:]).tocsr()
    del docs
    for q in qs:
        gold={kidx[x] for x in test[q] if x in kidx}
        if not gold: continue
        rel=set()
        for x in test[q]: rel|=set(neigh(x))
        for form,text in forms(q):
            qv=np.zeros(len(vocab),dtype=np.float32)
            for w in tok(text):
                if w in vocab: qv[vocab[w]]+=1
            o=np.argsort(-M.dot(qv))[:100]
            score('bm25',form,[next((j+1 for j,x in enumerate(o) if x in gold),None)])
            score('bm25',form+'/sugya',[next((j+1 for j,x in enumerate(o) if x in rel),None)])
    del M
# ---- dense
from sentence_transformers import SentenceTransformer
import torch
dev='mps' if torch.backends.mps.is_available() else 'cpu'
m=SentenceTransformer(a.model,device=dev); m.max_seq_length=256
print(f"encoding {len(keys):,} segments with {a.label}...",flush=True)
Dm=m.encode([corpus[k] for k in keys],batch_size=96,normalize_embeddings=True,
            convert_to_numpy=True,show_progress_bar=False).astype('float32')
np.save(f'{D}/emb_{a.label}.npy',Dm)
INS="Represent this sentence for searching relevant passages: "
allq=[(q,f,t) for q in qs for f,t in forms(q)]
E=m.encode([INS+t for _,_,t in allq],batch_size=64,normalize_embeddings=True,convert_to_numpy=True).astype('float32')
for i,(q,form,_) in enumerate(allq):
    gold={kidx[x] for x in test[q] if x in kidx}
    if not gold: continue
    rel=set()
    for x in test[q]: rel|=set(neigh(x))
    o=np.argsort(-(Dm@E[i]))[:100]
    score(a.label,form,[next((j+1 for j,x in enumerate(o) if x in gold),None)])
    score(a.label,form+'/sugya',[next((j+1 for j,x in enumerate(o) if x in rel),None)])
print(f"\n{'model':<14}{'query form':<22}{'n':>5}{'MRR':>8}{'R@1':>8}{'R@10':>8}")
rows={}
for (name,form),o in sorted(res.items()):
    if not o['mrr']: continue
    rows[f"{name}|{form}"]={k:statistics.mean(v) for k,v in o.items()}
    print(f"{name:<14}{form:<22}{len(o['mrr']):>5}{statistics.mean(o['mrr']):>8.3f}{statistics.mean(o['r1']):>8.3f}{statistics.mean(o['r10']):>8.3f}")
old=json.load(open(a.out)) if os.path.exists(a.out) else {}
old.update(rows); json.dump(old,open(a.out,'w'),indent=1)
print(f"\nsaved -> {a.out}")
