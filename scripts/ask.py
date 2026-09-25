"""Query the Talmud index. Usage: python3 ask.py "your question" [-k 8]"""
import json,gzip,os,sys,argparse
import numpy as np
D=os.path.expanduser('~/torah/bert/data')
M=os.path.expanduser('~/torah/bert/models/torah-embed')
ap=argparse.ArgumentParser()
ap.add_argument('question')
ap.add_argument('-k',type=int,default=8)
ap.add_argument('--chars',type=int,default=900)
ap.add_argument('--json',action='store_true')
a=ap.parse_args()
corpus=json.load(gzip.open(f'{D}/bavli_en.json.gz','rt')); keys=list(corpus)
emb=np.load(f'{D}/emb_torah-embed.npy')
from sentence_transformers import SentenceTransformer
import torch
m=SentenceTransformer(M,device='mps' if torch.backends.mps.is_available() else 'cpu')
m.max_seq_length=256
q=m.encode(["Represent this sentence for searching relevant passages: "+a.question],
           normalize_embeddings=True,convert_to_numpy=True).astype('float32')[0]
sc=emb@q
out=[]
for j in np.argsort(-sc)[:a.k]:
    out.append({"ref":keys[j],"score":round(float(sc[j]),3),"text":corpus[keys[j]][:a.chars]})
if a.json:
    print(json.dumps({"question":a.question,"results":out},indent=1))
else:
    print(f"\nQ: {a.question}\n")
    for r in out:
        print(f"[{r['score']:.3f}] {r['ref']}")
        print(f"  {r['text']}\n")
