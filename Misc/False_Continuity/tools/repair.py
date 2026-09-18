import pickle, numpy as np
sils=pickle.load(open('sils.pkl','rb'))
def shapesig(m):
    ys,xs=np.nonzero(m); pts=np.stack([xs,ys],1).astype(float); pts-=pts.mean(0)
    u,s,vt=np.linalg.svd(pts,full_matrices=False)
    pr=pts@vt.T
    r=np.sqrt((pr**2).sum(1)); th=np.arctan2(pr[:,1],pr[:,0])
    sig=np.zeros(72)
    b=((th+np.pi)/(2*np.pi)*72).astype(int)%72
    for i in range(72):
        sel=r[b==i]; sig[i]=sel.max() if len(sel) else 0
    return sig
sig={n:shapesig(m) for n,m in sils.items()}
names=sorted(sig)
def d(a,b):
    A,B=sig[a],sig[b]
    return min(np.abs(np.roll(A,k)-B).mean() for k in (0,36))
best={}
for n in names:
    c=sorted(((d(n,m),m) for m in names if m!=n))
    best[n]=c[:2]
seen=set(); prs=[]
for n in names:
    dd,m=best[n][0]
    if best[m][0][1]==n and n not in seen:
        seen.add(n); seen.add(m); prs.append((n,m,dd,best[n][1][0]))
print('mutual silhouette pairs:',len(prs))
ds=sorted(p[2] for p in prs)
print('pair distances: min %.3f max %.3f'%(ds[0],ds[-1]))
print('worst 8:')
for p in sorted(prs,key=lambda x:-x[2])[:8]:
    print('  d=%.3f next=%.3f'%(p[2],p[3]),p[0][:8],p[1][:8])
un=[n for n in names if n not in seen]
print('unpaired:',len(un))
pickle.dump([(a,b) for a,b,c,e in prs],open('sil_pairs.pkl','wb'))
