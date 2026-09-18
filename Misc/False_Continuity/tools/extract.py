from PIL import Image
import numpy as np, pickle
from scipy.ndimage import label, find_objects, binary_dilation
comp=pickle.load(open('groups.pkl','rb'))
prs=[c for c in comp if len(c)==2]
singles=[c[0] for c in comp if len(c)==1]
print('pairs',len(prs),'singles',len(singles))
recs=[]
for a,b in prs:
    A=np.array(Image.open('fc/%s.png'%a).convert('L')).astype(int)
    B=np.array(Image.open('fc/%s.png'%b).convert('L')).astype(int)
    d=np.abs(A-B)>10
    dd=binary_dilation(d,np.ones((11,11)))
    lab,n=label(dd)
    regs=[]
    for sl in find_objects(lab):
        y,x=sl
        regs.append((int(y.start),int(y.stop),int(x.start),int(x.stop)))
    recs.append((a,b,regs))
import collections
c=collections.Counter(len(r[2]) for r in recs)
print('regions per pair:',sorted(c.items()))
pickle.dump((recs,singles),open('extract.pkl','wb'))
