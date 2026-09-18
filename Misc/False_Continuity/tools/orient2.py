"""Decide 180 orientation by which way OCRs better (total template distance)."""
import pickle, numpy as np, sys, glob
from PIL import Image
sys.path.insert(0,'.')
import glyphs6 as G
import ocr5 as O

def run(path, deg):
    im=Image.open(path).convert('L')
    a=np.array(im.rotate(-deg,resample=Image.BICUBIC,fillcolor=G.BG,expand=True)).astype(int)
    cs=G.comps_adaptive(a); lines=G.make_lines(cs)
    v=dict(lines=lines)
    sc=O.tile_scale(v)
    tot=[];out=[]
    for L in lines:
        if not L: out.append([]); continue
        base=float(np.median([g['y1'] for g in L]))
        row=[]
        for g in L:
            c=O.classify(g,base,sc)
            row.append(dict(ch=c[0][1],alts=[x[1] for x in c[:5]],score=float(c[0][0]),
                            faint=g['faint'],x0=g['x0'],y0=g['y0']))
            tot.append(c[0][0])
        out.append(row)
    return (np.mean(tot) if tot else 9.9), out, sc

res={}
for k,f in enumerate(sorted(glob.glob('fc/*.png'))):
    d0=G.best_angle(G.comps_adaptive(np.array(Image.open(f).convert('L')).astype(int)))
    cands=[]
    for dd in (d0, d0+180):
        s,lines,sc=run(f,dd)
        cands.append((s,dd,lines,sc))
    cands.sort(key=lambda t:t[0])
    s,dd,lines,sc=cands[0]
    res[f]=dict(deg=dd,scale=sc,lines=lines,score=s,alt=cands[1][0])
    print('%3d %s deg=%+7.2f score=%.4f (alt %.4f) %s'%(k,f[3:19],dd,s,cands[1][0],
          ''.join(r['ch'] for L in lines for r in L)[:24]),flush=True)
pickle.dump(res,open('fc_ocr2.pkl','wb'))
print('SAVED')
