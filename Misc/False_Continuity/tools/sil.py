from PIL import Image
import numpy as np, glob, os, pickle
from scipy.ndimage import binary_fill_holes, binary_closing, uniform_filter

out={}
for f in sorted(glob.glob('fc/*.png')):
    a=np.array(Image.open(f).convert('L')).astype(float)
    var=uniform_filter(a**2,7)-uniform_filter(a,7)**2
    m=binary_fill_holes(binary_closing(var>2.0,np.ones((9,9))))
    out[os.path.basename(f)[:16]]=m
pickle.dump(out,open('sils.pkl','wb'))
areas=[m.sum() for m in out.values()]
print('n',len(out),'area min %d max %d mean %d'%(min(areas),max(areas),sum(areas)/len(areas)))
