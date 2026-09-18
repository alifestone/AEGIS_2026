# False_Continuity 解題 pipeline

由 planner session 建立，交接給 misc session。**路徑假設你在 scratchpad 解壓好 zip**，
144 張 PNG 放在 `fc/` 子目錄下，腳本從當前目錄的 `fc/*.png` 讀取。

```bash
# 1. 解壓到 scratchpad（不要污染題目資料夾）
mkdir -p "$SCRATCH/fc" && unzip -oq Misc/False_Continuity/False_Continuity.zip -d "$SCRATCH/fc"
cd "$SCRATCH"
cp <repo>/Misc/False_Continuity/tools/*.py .

# 2. 去斜 + 切字切行（約 5 分鐘）
python glyphs6.py          # -> fc_g6.pkl

# 3. OCR（約 2 分鐘）
python ocr5.py             # -> fc_ocr.pkl
```

## 檔案說明

| 檔案 | 作用 |
|---|---|
| `cc.py` | 8-connected component labeling（本機沒 scipy 時的替代，現在 scipy 已裝可以換掉） |
| `glyphs6.py` | 主 pipeline：±90° 全範圍去斜 → 180° 正反判定 → per-glyph 自適應門檻 → 切行切字 |
| `ocr5.py` | DejaVu Sans Mono template matching OCR，參數已用已知正解調校到 95% |
| `refine.py` | 嘗試用「紙張邊緣」過濾誤判的 faint（**這條路失敗了**，留著當負面紀錄） |
| `fc_ocr.pkl` | **已跑好的 OCR 結果**，可以直接 load 不用重跑 |

## fc_ocr.pkl 結構

```python
import pickle
d = pickle.load(open('fc_ocr.pkl','rb'))
# d: { 'fc\<name>.png': {'scale': float, 'lines': [[glyph, ...], ...]} }
# glyph: {'ch': 辨識出的字元, 'alts': [前5個候選], 'score': 匹配分數(越小越好),
#         'faint': bool 是否為灰字, 'x0': int, 'y0': int}

# 取出所有灰字
faint = [r['ch'] for f,v in sorted(d.items()) for L in v['lines'] for r in L if r['faint']]
len(faint)   # 764
```

## 已知的事

- 灰字 vs 黑字分界極乾淨：黑字墨色 p10 = 6~16，灰字 p10 = 58~98，門檻設 mn>=45
- ⚠️ **已更正**：不是 72 組重複對。正確是 **45~46 組重複對 + 52~54 張真單張**
  （真對一致率 0.974~0.981，單張最高只有 0.031，中間無灰色地帶）
  → 不重複紙屑數約 **98~99 張**，唯一 payload 約 **536~544 個灰字元**（不是 382）
  → 但「重複是給**錯誤更正**用的、不是編碼」這個結論**仍然成立**
    （45/46 對的灰字 mask 完全相同）
  → 詳見 ../notes.md 的「已更正」段落
- 灰字元的字元集**不是 base64**（只有 76% 落在 base64 字母表內），涵蓋全 printable ASCII

## 卡點

**72 組紙屑的排序未解。** 已排除：檔名（隨機 hex）、誘餌文字接龍（是亂碼）、
灰字墨色深淺（45–98 連續，像渲染雜訊）、背景浮水印（星圖/羅盤在 191–210，是紙張材質）。

詳見 [../notes.md](../notes.md)。
