"""Re-classify faint vs normal using pure-black test, rejecting edge-clipped glyphs."""
import pickle, sys, math
sys.path.insert(0,'.')
import numpy as np
from PIL import Image

d=pickle.load(open('fc_g6.pkl','rb'))
out={}
for f,v in d.items():
    im=Image.open(f).convert('L').rotate(-v['deg'],resample=Image.BICUBIC,fillcolor=218,expand=True)
    a=np.array(im).astype(int)
    # paper = anything not exactly the rotation fill and reasonably light OR ink
    paper=(a!=218)
    # erode paper mask by ~6px to find "interior"
    from numpy.lib.stride_tricks import sliding_window_view
    P=np.pad(paper,2,constant_values=False)
    win=sliding_window_view(P,(5,5))
    interior=win.all(axis=(2,3))
    lines=[]
    for L in v['lines']:
        row=[]
        for g in L:
            y0,y1,x0,x1=g['y0'],g['y1'],g['x0'],g['x1']
            # is the glyph fully inside the paper interior?
            sub=interior[max(0,y0-2):y1+3, max(0,x0-2):x1+3]
            inside = sub.size>0 and sub.mean()>0.95
            gg=dict(g); gg['inside']=bool(inside)
            gg['faint2']= bool(g['mn']>=45 and inside)
            row.append(gg)
        lines.append(row)
    out[f]=dict(deg=v['deg'],lines=lines)
    print(f"{f[3:]} faint_old={sum(1 for L in v['lines'] for g in L if g['mn']>=45)} "
          f"faint_new={sum(1 for L in lines for g in L if g['faint2'])}",flush=True)
pickle.dump(out,open('fc_g7.pkl','wb'))
print("SAVED")
