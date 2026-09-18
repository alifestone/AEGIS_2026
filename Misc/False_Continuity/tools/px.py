from PIL import Image
import numpy as np, glob, os, pickle

files=sorted(glob.glob('fc/*.png'))
# rotation-invariant: radial+intensity profile of INK only, plus scrap silhouette stats
prof={}
for f in files:
    a=np.array(Image.open(f).convert('L')).astype(np.float32)
    paper=a>120
    ys,xs=np.nonzero(paper)
    cy,cx=ys.mean(),xs.mean()
    ink=(a<=120)
    iy,ix=np.nonzero(ink)
    r=np.sqrt((iy-cy)**2+(ix-cx)**2)
    h=np.histogram(r,bins=40,range=(0,320))[0].astype(float)
    py,px_=np.nonzero(paper)
    rp=np.sqrt((py-cy)**2+(px_-cx)**2)
    hp=np.histogram(rp,bins=40,range=(0,320))[0].astype(float)
    prof[os.path.basename(f)[:16]]=(h/max(h.sum(),1),hp/max(hp.sum(),1),paper.sum(),ink.sum())

names=sorted(prof)
def d(a,b):
    ha,hpa,pa,ia=prof[a]; hb,hpb,pb,ib=prof[b]
    return (np.abs(ha-hb).sum()+np.abs(hpa-hpb).sum()
            +abs(pa-pb)/max(pa,pb)+abs(ia-ib)/max(ia,ib,1))
best={}
for n in names:
    c=sorted(((d(n,m),m) for m in names if m!=n))
    best[n]=(c[0],c[1])
# distribution of best distances - bimodal means real twins exist
ds=sorted(best[n][0][0] for n in names)
print('best-dist quartiles:',[round(ds[i],3) for i in (0,35,71,107,143)])
cnt=sum(1 for n in names if best[n][0][0]<0.25)
print('files with a very close image twin (<0.25):',cnt)
mut=0;seen=set()
for n in names:
    m=best[n][0][1]
    if best[m][0][1]==n and best[n][0][0]<0.25 and n not in seen:
        seen.add(n);seen.add(m);mut+=1
print('mutual close image pairs:',mut)
pickle.dump(prof,open('prof.pkl','wb'))
