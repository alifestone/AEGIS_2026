"""Re-segment using per-glyph adaptive threshold (halfway between ink min and paper)."""
import sys, glob, math, pickle
sys.path.insert(0,'.')
import numpy as np
from PIL import Image
from cc import label

THR=205; MINPX=40; FAINT_MN=45; BG=218; PAPER=216

def comps_adaptive(a):
    """first pass at THR to find glyph regions, then re-threshold each at its own level"""
    lab,n=label(a<THR); out=[]
    for i in range(1,n+1):
        m=lab==i
        if m.sum()<MINPX: continue
        ys,xs=np.where(m)
        y0,y1,x0,x1=int(ys.min()),int(ys.max()),int(xs.min()),int(xs.max())
        patch=a[y0:y1+1,x0:x1+1]
        mn=int(patch[m[y0:y1+1,x0:x1+1]].min())
        # adaptive: midpoint between this glyph's darkest ink and the paper level
        t=(mn+PAPER)//2
        core=(patch<=t) & m[y0:y1+1,x0:x1+1]
        if core.sum()<20: core=m[y0:y1+1,x0:x1+1]
        ys2,xs2=np.where(core)
        ny0,ny1,nx0,nx1=ys2.min(),ys2.max(),xs2.min(),xs2.max()
        out.append(dict(x0=x0+int(nx0),x1=x0+int(nx1),y0=y0+int(ny0),y1=y0+int(ny1),
                        w=int(nx1-nx0+1),h=int(ny1-ny0+1),n=int(core.sum()),mn=mn,
                        faint=bool(mn>=FAINT_MN),
                        mask=core[ny0:ny1+1, nx0:nx1+1]))
    return out

def best_angle(cs):
    if len(cs)<3: return 0.0
    pts=np.array([[(c['x0']+c['x1'])/2,(c['y0']+c['y1'])/2] for c in cs])
    best=None
    for deg in np.arange(-90,90,0.25):
        t=math.radians(deg)
        v=pts[:,0]*math.sin(t)+pts[:,1]*math.cos(t)
        h,_=np.histogram(v,bins=np.arange(v.min()-0.5,v.max()+6,3.0))
        s=(h.astype(float)**2).sum()/max(1,(h>0).sum())
        if best is None or s>best[1]: best=(deg,s)
    return best[0]

def make_lines(cs):
    if not cs: return []
    cs=sorted(cs,key=lambda c:(c['y0']+c['y1'])/2)
    med=np.median([c['h'] for c in cs]); gap=max(7.0,med*0.6)
    lines=[];cur=[cs[0]]
    for c in cs[1:]:
        if (c['y0']+c['y1'])/2-(cur[-1]['y0']+cur[-1]['y1'])/2>gap: lines.append(cur);cur=[]
        cur.append(c)
    lines.append(cur)
    for L in lines: L.sort(key=lambda c:c['x0'])
    return lines

def orient_score(lines):
    sc=0;cnt=0
    for L in lines:
        if len(L)<4: continue
        sc+=np.std([c['y0'] for c in L])-np.std([c['y1'] for c in L]); cnt+=1
    return sc/max(1,cnt)

def process(path):
    im=Image.open(path).convert('L')
    deg0=best_angle(comps_adaptive(np.array(im).astype(int)))
    best=None
    for dd in (deg0,deg0+180):
        a=np.array(im.rotate(-dd,resample=Image.BICUBIC,fillcolor=BG,expand=True)).astype(int)
        cs=comps_adaptive(a); lines=make_lines(cs); s=orient_score(lines)
        if best is None or s>best[0]: best=(s,dd,lines)
    return best[1],best[2]

if __name__=="__main__":
    out={}
    for k,f in enumerate(sorted(glob.glob('fc/*.png'))):
        deg,lines=process(f)
        out[f]=dict(deg=deg,lines=lines)
        print(f"{k:3d} {f[3:]} deg={deg:+7.2f} lens={[len(L) for L in lines]} "
              f"faint={sum(1 for L in lines for g in L if g['faint'])}",flush=True)
    pickle.dump(out,open('fc_g6.pkl','wb'))
    print("SAVED")
