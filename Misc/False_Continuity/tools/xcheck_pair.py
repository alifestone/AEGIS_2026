import pickle, numpy as np
sils=pickle.load(open('sils.pkl','rb'))
names=sorted(sils)
def sig(m,nb=72):
    ys,xs=np.nonzero(m)
    P=np.stack([xs-xs.mean(),ys-ys.mean()]).astype(float)
    C=np.cov(P); w,V=np.linalg.eigh(C)
    R=V[:,::-1].T@P
    ang=np.arctan2(R[1],R[0]); rad=np.hypot(R[0],R[1])
    b=((ang+np.pi)/(2*np.pi)*nb).astype(int)%nb
    out=np.zeros(nb)
    for i in range(nb):
        s=rad[b==i]
        out[i]=s.max() if len(s) else 0
    return out/out.max()
S={n:sig(sils[n]) for n in names}
N=len(names)
D=np.zeros((N,N))
for i in range(N):
    for j in range(N):
        a,b=S[names[i]],S[names[j]]
        # allow 180 flip
        D[i,j]=min(np.abs(a-b).mean(), np.abs(a-np.roll(b,36)).mean())
np.fill_diagonal(D,9)
best=D.min(axis=1)
o=np.sort(best)
print("smallest 60 best-match distances:")
print(np.round(o[:60],5))
print("largest 20:",np.round(o[-20:],4))
pickle.dump((names,D),open('mydist.pkl','wb'))
