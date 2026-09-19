# ⛔ 注意：本檔 load 的 fc_ocr.pkl 已作廢（180° 方向判定錯 46%）。
# 該檔已改名為 DEPRECATED_fc_ocr_WRONG_ORIENTATION.pkl，本腳本目前會跑不起來。
# 本腳本的結果僅供歷史參考；要重跑請改用 fc_ocr2.pkl（見 tools/README.md）。

import pickle
ocr=pickle.load(open('fc_ocr.pkl','rb'))
rec={}
for f,v in ocr.items():
    n=f.replace(chr(92),'/').split('/')[-1][:16]
    rec[n]=v
names=sorted(rec)

# per-line comparison, tolerant of OCR errors: compare line-length profile + char agreement
def lines_of(n):
    return [''.join(r['ch'] for r in L) for L in rec[n]['lines']]
def faintmask(n):
    return [''.join('1' if r['faint'] else '0' for r in L) for L in rec[n]['lines']]

def score(a,b):
    la,lb=lines_of(a),lines_of(b)
    if len(la)!=len(lb): return 0.0
    tot=0;agree=0
    for x,y in zip(la,lb):
        if abs(len(x)-len(y))>1: return 0.0
        m=min(len(x),len(y))
        agree+=sum(1 for i in range(m) if x[i]==y[i]); tot+=max(len(x),len(y))
    return agree/tot if tot else 0.0

best={}
for n in names:
    c=sorted(((score(n,m),m) for m in names if m!=n),reverse=True)
    best[n]=c[0]
seen=set();pairs=[];lone=[]
for n in names:
    s,m=best[n]
    if s>0.5 and best[m][1]==n and n not in seen:
        seen.add(n);seen.add(m);pairs.append((n,m,s))
lone=[n for n in names if n not in seen]
print('structural twin pairs:',len(pairs),' lone:',len(lone))
for n in lone: print('  lone',n,'best %.2f'%best[n][0],best[n][1],'lines',len(rec[n]['lines']))
pickle.dump((pairs,lone),open('twins.pkl','wb'))
