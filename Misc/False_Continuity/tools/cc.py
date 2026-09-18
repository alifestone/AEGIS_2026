import numpy as np
def label(mask):
    """8-connected labeling via union-find, no scipy."""
    H,W=mask.shape
    lab=np.zeros((H,W),np.int32)
    parent=[0]
    def find(x):
        while parent[x]!=x:
            parent[x]=parent[parent[x]]; x=parent[x]
        return x
    def union(a,b):
        ra,rb=find(a),find(b)
        if ra!=rb: parent[max(ra,rb)]=min(ra,rb)
    nxt=1
    for y in range(H):
        row=mask[y]
        for x in range(W):
            if not row[x]: continue
            nb=[]
            if x>0 and lab[y,x-1]: nb.append(lab[y,x-1])
            if y>0:
                if lab[y-1,x]: nb.append(lab[y-1,x])
                if x>0 and lab[y-1,x-1]: nb.append(lab[y-1,x-1])
                if x<W-1 and lab[y-1,x+1]: nb.append(lab[y-1,x+1])
            if nb:
                m=min(nb); lab[y,x]=m
                for o in nb: union(m,o)
            else:
                lab[y,x]=nxt; parent.append(nxt); nxt+=1
    # flatten
    remap={}
    out=np.zeros((H,W),np.int32); k=0
    for y in range(H):
        for x in range(W):
            if lab[y,x]:
                r=find(lab[y,x])
                if r not in remap:
                    k+=1; remap[r]=k
                out[y,x]=remap[r]
    return out,k
