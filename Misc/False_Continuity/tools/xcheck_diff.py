import pickle, numpy as np
from PIL import Image
from scipy.ndimage import label, find_objects, binary_dilation
pairs,singles=pickle.load(open('mystruct.pkl','rb'))
res=[]
for i,(a,b) in enumerate(pairs):
    A=np.array(Image.open('fc/%s.png'%a).convert('L')).astype(int)
    B=np.array(Image.open('fc/%s.png'%b).convert('L')).astype(int)
    d=np.abs(A-B)
    nz=(d>10)
    lab,n=label(binary_dilation(nz,np.ones((11,11))))
    objs=find_objects(lab)
    regs=[]
    for k,sl in enumerate(objs):
        cnt=int((lab[sl]==k+1).sum())
        ys,xs=sl
        regs.append((cnt,(ys.start+ys.stop)//2,(xs.start+xs.stop)//2,ys,xs))
    regs.sort(key=lambda r:-r[0])
    res.append((a,b,int(nz.sum()),len(regs),regs))
    print(i,a[:8],b[:8],"npx",int(nz.sum()),"regions",len(regs),flush=True)
pickle.dump(res,open('mydiff.pkl','wb'))
from collections import Counter
print(Counter(r[3] for r in res))
