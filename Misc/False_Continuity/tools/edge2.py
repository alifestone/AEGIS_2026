import pickle, numpy as np
sils=pickle.load(open('sils.pkl','rb'))
comp=pickle.load(open('groups.pkl','rb'))
reps=[c[0] for c in comp]
def prof(m,N=256):
    ys,xs=np.nonzero(m)
    pts=np.stack([xs,ys],1).astype(float); c=pts.mean(0); p=pts-c
    u,s,vt=np.linalg.svd(p,full_matrices=False)
    pr=p@vt.T
    a0,a1=pr[:,0],pr[:,1]
    out={}
    b0=np.linspace(a0.min(),a0.max(),N+1)
    i0=np.clip(np.digitize(a0,b0)-1,0,N-1)
    t=np.full(N,np.nan); b=np.full(N,np.nan)
    for i in range(N):
        sel=a1[i0==i]
        if len(sel)>2: t[i]=sel.min(); b[i]=sel.max()
    b1=np.linspace(a1.min(),a1.max(),N+1)
    i1=np.clip(np.digitize(a1,b1)-1,0,N-1)
    l=np.full(N,np.nan); r=np.full(N,np.nan)
    for i in range(N):
        sel=a0[i1==i]
        if len(sel)>2: l[i]=sel.min(); r[i]=sel.max()
    out['top']=t; out['bot']=b; out['lef']=l; out['rig']=r
    out['len0']=a0.max()-a0.min(); out['len1']=a1.max()-a1.min()
    return out
P={n:prof(sils[n]) for n in reps}
pickle.dump(P,open('edges2.pkl','wb'))
def mm(u,v,Lu,Lv):
    if abs(Lu-Lv)/max(Lu,Lv)>0.08: return 1e9   # edges must be similar length
    m=~np.isnan(u)&~np.isnan(v)
    if m.sum()<200: return 1e9
    a=u[m]-u[m].mean(); b=v[m]-v[m].mean()
    return float((a+b).std())
LEN={'top':'len0','bot':'len0','lef':'len1','rig':'len1'}
cand=[]
for x in reps:
    for y in reps:
        if x>=y: continue
        for ka in ('top','bot','lef','rig'):
            for kb in ('top','bot','lef','rig'):
                s=mm(P[x][ka],P[y][kb],P[x][LEN[ka]],P[y][LEN[kb]])
                if s<6: cand.append((s,x,y,ka,kb))
cand.sort()
print('rms<6 candidates:',len(cand))
for s,x,y,ka,kb in cand[:30]: print('  %.2f'%s,x[:8],ka,'<->',y[:8],kb)
pickle.dump(cand,open('cand2.pkl','wb'))
