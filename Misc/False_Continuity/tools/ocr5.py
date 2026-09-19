"""Final OCR over all tiles with tuned parameters.

⛔ LEGACY：本腳本用 glyphs6.process() 的 180° 判定，會錯 46% 的紙屑。
要產生正確的 OCR 結果請跑 orient2.py（輸出 fc_ocr2.pkl）。
下一步優化：把下方 CHARS 限縮成 A-Za-z0-9+/= 以降低 base64 誤判。
"""
import pickle, string, sys, json
import numpy as np
from PIL import Image, ImageFont, ImageDraw
sys.path.insert(0,'.')

FONT='C:/Windows/Fonts/DejaVuSansMono-Roman.ttf'
CHARS=(string.ascii_uppercase+string.ascii_lowercase+string.digits+
       "+/=*,._<>{}()[]!?@#$%^&-:;'\"`~|\\")
SZ=32; PX=32; WA,WT,WH=0.05,0.05,0.1

def nrm(mask):
    h,w=mask.shape; s=max(h,w)
    c=np.zeros((s,s),float); c[(s-h)//2:(s-h)//2+h,(s-w)//2:(s-w)//2+w]=mask
    return np.array(Image.fromarray((c*255).astype(np.uint8)).resize((SZ,SZ),Image.BILINEAR)).astype(float)/255.

def build(px):
    f=ImageFont.truetype(FONT,px); out={}
    for ch in CHARS:
        im=Image.new('L',(px*3,px*3),255)
        ImageDraw.Draw(im).text((px,px),ch,font=f,fill=0,anchor='ls')
        a=np.array(im)<128; ys,xs=np.where(a)
        if len(ys)==0: continue
        m=a[ys.min():ys.max()+1,xs.min():xs.max()+1]
        out[ch]=dict(v=nrm(m),w=m.shape[1],h=m.shape[0],
                     top=int(ys.min()-px),bot=int(ys.max()-px),asp=m.shape[1]/m.shape[0])
    return out

T=build(PX)

def classify(g, base, scale):
    """scale = ratio of this tile's glyph size to template size"""
    gv=nrm(g['mask'].astype(float)); gasp=g['w']/g['h']
    gt=(g['y0']-base)/scale; gb=(g['y1']-base)/scale
    gh=g['h']/scale
    out=[]
    for ch,t in T.items():
        dd=np.abs(gv-t['v']).mean()
        pa=abs(np.log((gasp+1e-6)/(t['asp']+1e-6)))
        pp=(abs(gt-t['top'])+abs(gb-t['bot']))/PX
        ph=abs(np.log((gh+1e-6)/(t['h']+1e-6)))
        out.append((dd+WA*pa+WT*pp+WH*ph, ch))
    out.sort()
    return out

def tile_scale(v):
    dxs=[]
    for L in v['lines']:
        if len(L)<4: continue
        dxs+=[b['x0']-a['x0'] for a,b in zip(L,L[1:]) if 12<b['x0']-a['x0']<45]
    if not dxs: return 1.0
    # DejaVu Sans Mono advance width = 0.60205 em
    return (float(np.median(dxs))/0.60205)/PX

if __name__=="__main__":
    d=pickle.load(open('fc_g6.pkl','rb'))
    res={}
    for k,(f,v) in enumerate(sorted(d.items())):
        sc=tile_scale(v)
        lines=[]
        for L in v['lines']:
            if not L: lines.append([]); continue
            base=float(np.median([g['y1'] for g in L]))
            row=[]
            for g in L:
                c=classify(g,base,sc)
                row.append(dict(ch=c[0][1], alts=[x[1] for x in c[:5]],
                                score=float(c[0][0]), faint=g['faint'],
                                x0=g['x0'], y0=g['y0']))
            lines.append(row)
        res[f]=dict(scale=sc, lines=lines)
        txt=' | '.join(''.join(r['ch'] for r in L) for L in lines)
        fnt=''.join(r['ch'] for L in lines for r in L if r['faint'])
        print(f"{k:3d} {f[3:]} sc={sc:.2f} faint='{fnt}'", flush=True)
    # ⛔ 不再寫成 fc_ocr.pkl：那個名字已被標記作廢（方向錯 46%），
    #    若沿用同名會把 DEPRECATED 防呆蓋掉，讓後人以為這是可用的結果。
    pickle.dump(res,open('fc_ocr_LEGACY_WRONG_ORIENTATION.pkl','wb'))
    print("SAVED")
