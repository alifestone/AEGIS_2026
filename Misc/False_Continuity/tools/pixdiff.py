from PIL import Image
import numpy as np, pickle
from scipy.ndimage import label, find_objects
pairs,lone=pickle.load(open('twins.pkl','rb'))
res={}
for a,b,s in pairs:
    A=np.array(Image.open('fc/%s.png'%a).convert('L')).astype(int)
    B=np.array(Image.open('fc/%s.png'%b).convert('L')).astype(int)
    d=np.abs(A-B)>10
    lab,n=label(d)
    res[(a,b)]=(n,d.sum())
import collections
c=collections.Counter(v[0] for v in res.values())
print('regions-differing per twin pair:',sorted(c.items()))
for k,v in list(res.items())[:15]:
    print(k[0][:8],k[1][:8],'regions',v[0],'px',v[1])
pickle.dump(res,open('pixdiff.pkl','wb'))
