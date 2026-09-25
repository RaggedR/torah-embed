"""Stage ruling batches for question generation. Persists inputs to data/qgen_in/."""
import json,gzip,os,random,sys
random.seed(11)
D=os.path.expanduser('~/torah/bert/data')
os.makedirs(f'{D}/qgen_in',exist_ok=True)
src=json.load(gzip.open(f'{D}/sources_en.json.gz','rt'))
sp=json.load(gzip.open(f'{D}/split.json.gz','rt'))
which=sys.argv[1]           # train | test
n=int(sys.argv[2])          # number of batches
size=int(sys.argv[3])       # rulings per batch
ids=sorted(sp[which])
if which=='train':
    random.shuffle(ids); ids=ids[:n*size]
for i in range(n):
    c=ids[i*size:(i+1)*size]
    if c: json.dump([{"id":q,"ruling":src[q][:1100]} for q in c],
                    open(f'{D}/qgen_in/{which}_{i}.json','w'),indent=1)
print(f"{which}: staged {n} batches x {size} = {min(len(ids),n*size)} rulings -> data/qgen_in/")
