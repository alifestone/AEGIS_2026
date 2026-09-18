from PIL import Image
import numpy as np, pickle, sys
sys.path.insert(0,'.')
import glyphs6 as G
comp=pickle.load(open('groups.pkl','rb'))
prs=[c for c in comp if len(c)==2]
from scipy.ndimage import label, find_objects, binary_dilation
res=[]
for i,(a,b) in enumerate(prs):
    deg,lines=G.process('fc/%s.png'%a)   # resolves 180 via baseline score
    A=np.array(Image.open('fc/%s.png'%a).convert('L').rotate(-deg,resample=Image.BICUBIC,fillcolor=G.BG,expand=True)).astype(int)
    B=np.array(Image.open('fc/%s.png'%b).convert('L').rotate(-deg,resample=Image.BICUBIC,fillcolor=G.BG,expand=True)).astype(int)
    h=min(A.shape[0],B.shape[0]); w=min(A.shape[1],B.shape[1])
    A=A[:h,:w]; B=B[:h,:w]
    d=binary_dilation(np.abs(A-B)>10,np.ones((11,11)))
    lab,n=label(d)
    objs=sorted(find_objects(lab),key=lambda sl:-(lab[sl]>0).sum())
    y,x=objs[0]
    cy,cx=(y.start+y.stop)//2,(x.start+x.stop)//2
    # which line/col is this glyph in?
    li=ci=-1
    for lidx,L in enumerate(lines):
        for cidx,g in enumerate(L):
            if g['y0']-4<=cy<=g['y1']+4 and g['x0']-4<=cx<=g['x1']+4:
                li,ci=lidx,cidx
    res.append((a,b,deg,cy,cx,li,ci,len(lines),[len(L) for L in lines]))
    print(i,a[:8],b[:8],'deg %+7.2f'%deg,'line',li,'col',ci,flush=True)
pickle.dump(res,open('dd3.pkl','wb'))
