"""Robust 180 check: OCR the whole scrap at deg and deg+180; the true orientation
matches the font templates much better (lower mean best-match score)."""
import pickle, numpy as np, sys, math
from PIL import Image
sys.path.insert(0,'.')
import glyphs6 as G, ocr5 as O
res=pickle.load(open('mydiff.pkl','rb'))
names=sorted({n for a,b,_,_,_ in res for n in (a,b)})
def mean_score(path,deg):
    a=np.array(Image.open(path).convert('L').rotate(-deg,resample=Image.BICUBIC,
               fillcolor=G.BG,expand=True)).astype(int)
    cs=G.comps_adaptive(a); lines=G.make_lines(cs)
    sc=O.tile_scale(dict(lines=lines))
    tot=[];
    for L in lines:
        if not L: continue
        base=float(np.median([g['y1'] for g in L]))
        for g in L:
            tot.append(O.classify(g,base,sc)[0][0])
    return (np.mean(tot) if tot else 9), len(tot)
out={}
for i,n in enumerate(names):
    deg,_=G.process('fc/%s.png'%n)
    s0,n0=mean_score('fc/%s.png'%n,deg)
    s1,n1=mean_score('fc/%s.png'%n,deg+180)
    flip = s1<s0
    out[n]=dict(deg=deg,s0=s0,s1=s1,flip=flip)
    print(i,n[:8],"deg%+8.2f"%deg,"up=%.4f flip=%.4f"%(s0,s1),"<<FLIP" if flip else "",flush=True)
pickle.dump(out,open('orient2.pkl','wb'))
print("FLIP NEEDED:",sum(1 for v in out.values() if v['flip']),"of",len(out))
