"""Run the author's 26 questions against both models. Redacted attributions."""
import json,gzip,os,numpy as np
from sentence_transformers import SentenceTransformer
import torch
D=os.path.expanduser('~/torah/bert/data')
corpus=json.load(gzip.open(f'{D}/bavli_en.json.gz','rt')); keys=list(corpus)
RED={"Havez.txt, the trust named after Leo Jedwab":"personal correspondence",
     "Havez.txt, bitachon":"personal notes, on bitachon (trust)",
     "Havez.txt, kishronotai":"personal notes",
     "Havez.txt, Ghazal 255":"Hafez, Ghazal 255"}
qs=json.load(open(f'{D}/robin_questions.json'))
for x in qs: x['src']=RED.get(x['src'],x['src'])
INS="Represent this sentence for searching relevant passages: "
dev='mps' if torch.backends.mps.is_available() else 'cpu'
out=[dict(x,hits={}) for x in qs]
for label,path in [('zero-shot','BAAI/bge-base-en-v1.5'),
                   ('torah-embed',os.path.expanduser('~/torah/bert/models/torah-embed'))]:
    Dm=np.load(f'{D}/emb_{label}.npy')
    m=SentenceTransformer(path,device=dev); m.max_seq_length=256
    E=m.encode([INS+x['q'] for x in qs],batch_size=32,normalize_embeddings=True,convert_to_numpy=True).astype('float32')
    for i,o in enumerate(out):
        o['hits'][label]=[{"ref":keys[j],"text":corpus[keys[j]][:330]} for j in np.argsort(-(Dm@E[i]))[:3]]
    del Dm,m
json.dump(out,open(f'{D}/author_questions_results.json','w'),indent=1)
same=sum(1 for o in out if o['hits']['zero-shot'][0]['ref']==o['hits']['torah-embed'][0]['ref'])
print(f"done. top-1 unchanged by fine-tuning: {same}/{len(out)}")
