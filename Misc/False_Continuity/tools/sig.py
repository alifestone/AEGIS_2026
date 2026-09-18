import pickle
pairs,lone=pickle.load(open('twins.pkl','rb'))
ocr=pickle.load(open('fc_ocr.pkl','rb'))
rec={f.replace(chr(92),'/').split('/')[-1][:16]:v for f,v in ocr.items()}
res=[]
for a,b,s in pairs:
    la=[r for L in rec[a]['lines'] for r in L]
    lb=[r for L in rec[b]['lines'] for r in L]
    if len(la)!=len(lb): res.append((a,b,None)); continue
    diff=[(i,x,y) for i,(x,y) in enumerate(zip(la,lb)) if x['ch']!=y['ch']]
    res.append((a,b,diff))
n1=sum(1 for a,b,d in res if d is not None and len(d)==1)
print('pairs with exactly 1 differing glyph: %d / %d'%(n1,len(res)))
print('pairs with 0:',sum(1 for a,b,d in res if d is not None and len(d)==0))
print('pairs with >1:',sum(1 for a,b,d in res if d is not None and len(d)>1))
print('len mismatch:',sum(1 for a,b,d in res if d is None))
pickle.dump(res,open('sig.pkl','wb'))
# the differing pair of chars, and its index
for a,b,d in res:
    if d and len(d)==1:
        i,x,y=d[0]
        print('%s/%s idx%3d  %r vs %r  faint=%s'%(a[:6],b[:6],i,x['ch'],y['ch'],x['faint']))
