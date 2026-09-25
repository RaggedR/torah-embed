"""Fine-tune bge-base on ein-mishpat pairs. Checkpoints every --ckpt steps; resumable."""
import json,gzip,os,re,random,collections,glob,argparse,sys
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import memguard
random.seed(13)
D=os.path.expanduser('~/torah/bert/data')
M=os.path.expanduser('~/torah/bert/models')
ap=argparse.ArgumentParser()
ap.add_argument('--epochs',type=int,default=1)
ap.add_argument('--batch',type=int,default=16)
ap.add_argument('--lr',type=float,default=2e-5)
ap.add_argument('--maxlen',type=int,default=192)
ap.add_argument('--qweight',type=int,default=3)
ap.add_argument('--maxpos',type=int,default=3)
ap.add_argument('--ckpt',type=int,default=250,help='checkpoint every N steps')
ap.add_argument('--resume',action='store_true')
ap.add_argument('--out',default=f'{M}/torah-embed')
a=ap.parse_args()
memguard.require(5.0,'for training')
os.makedirs(f'{a.out}-ckpt',exist_ok=True)
import torch
from sentence_transformers import SentenceTransformer, InputExample, losses
from torch.utils.data import DataLoader
corpus=json.load(gzip.open(f'{D}/bavli_en.json.gz','rt'))
src=json.load(gzip.open(f'{D}/sources_en.json.gz','rt'))
train=json.load(gzip.open(f'{D}/split.json.gz','rt'))['train']
Q=collections.defaultdict(list)
for f in glob.glob(f'{D}/questions_train_*.json'):
    for x in json.load(open(f)):
        for k in ('q_practical','q_conceptual'):
            if x.get(k): Q[x['id']].append(x[k].strip())
print(f"question anchors: {sum(len(v) for v in Q.values())} over {len(Q)} rulings",flush=True)
bydaf=collections.defaultdict(list)
for k in corpus: bydaf[k.rsplit(':',1)[0]].append(k)
ex=[]; nq=nr=0
for qid,pos in train.items():
    ps=set(pos); negs=[]
    for p in pos[:3]:
        c=[x for x in bydaf.get(p.rsplit(':',1)[0],[]) if x not in ps]
        random.shuffle(c); negs+=c[:2]
    negs=negs[:3]
    for text,rep in [(src[qid],1)]+[(q,a.qweight) for q in Q.get(qid,[])]:
        for p in pos[:a.maxpos]:
            for _ in range(rep):
                ex.append(InputExample(texts=[text,corpus[p]]+([corpus[random.choice(negs)]] if negs else [])))
                if rep>1: nq+=1
                else: nr+=1
del corpus,src,bydaf
random.shuffle(ex)
print(f"examples: {len(ex):,} (question {nq:,}, ruling {nr:,})",flush=True)
base='BAAI/bge-base-en-v1.5'
ck=sorted(glob.glob(f'{a.out}-ckpt/*'),key=lambda p:int(re.sub(r'\D','',os.path.basename(p)) or 0))
if a.resume and ck:
    base=ck[-1]; print(f"RESUMING from {base}",flush=True)
dev='mps' if torch.backends.mps.is_available() else 'cpu'
m=SentenceTransformer(base,device=dev); m.max_seq_length=a.maxlen
dl=DataLoader(ex,shuffle=True,batch_size=a.batch,drop_last=True)
steps=len(dl)*a.epochs
print(f"device={dev} batch={a.batch} maxlen={a.maxlen} epochs={a.epochs} steps={steps:,} ckpt every {a.ckpt}",flush=True)
m.fit(train_objectives=[(dl,losses.MultipleNegativesRankingLoss(m))],epochs=a.epochs,
      warmup_steps=int(0.1*steps),optimizer_params={'lr':a.lr},output_path=a.out,
      checkpoint_path=f'{a.out}-ckpt',checkpoint_save_steps=a.ckpt,checkpoint_save_total_limit=2,
      show_progress_bar=True,use_amp=False)
m.save(a.out); print("SAVED ->",a.out,flush=True)
