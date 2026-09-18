from PIL import Image
import numpy as np, pickle, sys
sys.path.insert(0,'.')
import glyphs6 as G
from scipy.ndimage import label, find_objects, binary_dilation
comp=pickle.load(open('groups.pkl','rb'))
prs=[c for c in comp if len(c)==2]
new=pickle.load(open('fc_ocr2.pkl','rb'))
rec={f.replace(chr(92),'/').split('/')[-1][:16]:v for f,v in new.items()}
rows=[]
for a,b in prs:
    deg=rec[a]['deg']
    A=np.array(Image.open('fc/%s.png'%a).convert('L').rotate(-deg,resample=Image.BICUBIC,fillcolor=G.BG,expand=True)).astype(int)
    B=np.array(Image.open('fc/%s.png'%b).convert('L').rotate(-deg,resample=Image.BICUBIC,fillcolor=G.BG,expand=True)).astype(int)
    h=min(A.shape[0],B.shape[0]); w=min(A.shape[1],B.shape[1])
    A=A[:h,:w];B=B[:h,:w]
    d=binary_dilation(np.abs(A-B)>10,np.ones((13,13)))
    lab,n=label(d)
    objs=sorted(find_objects(lab),key=lambda sl:-(lab[sl]>0).sum())
    y,x=objs[0]; cy,cx=(y.start+y.stop)//2,(x.start+x.stop)//2
    li=ci=-1
    for lidx,L in enumerate(rec[a]['lines']):
        for cidx,g in enumerate(L):
            if abs(g['y0']-cy)<40 and abs(g['x0']-cx)<26:
                if li<0 or (abs(g['y0']-cy)+abs(g['x0']-cx))<best:
                    best=abs(g['y0']-cy)+abs(g['x0']-cx); li,ci=lidx,cidx
    ca=cb=None
    if li>=0:
        ca=rec[a]['lines'][li][ci]['ch']
        if li<len(rec[b]['lines']) and ci<len(rec[b]['lines'][li]):
            cb=rec[b]['lines'][li][ci]['ch']
    rows.append((a,b,li,ci,ca,cb,len(objs)))
pickle.dump(rows,open('dd5.pkl','wb'))
print('resolved',sum(1 for r in rows if r[4] and r[5]),'of',len(rows))
for r in rows: print(r[0][:8],r[1][:8],'L%s C%s'%(r[2],r[3]),repr(r[4]),'vs',repr(r[5]),'regs',r[6])
