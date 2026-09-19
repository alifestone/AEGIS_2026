# False_Continuity 解題 pipeline

> ## ⛔ 2026-09-19 暫停點 — 接手者請先讀
>
> **題目的真正結構：一份 base64 文件被撕成 96 張不重複紙屑。**
> 「灰字 = payload、黑字 = 誘餌」是誤導，先前所有灰字分析都作廢。
> 目視證據：`d65d678f` 第 2 行印的是 `dmVsb3BlIH...` = base64 `"velope"`（envelope）。
>
> | 檔案 | 狀態 |
> |---|---|
> | `fc_ocr2.pkl` | ✅ **用這個**（方向已修正，含 `deg`/`score`/`alt`） |
> | `DEPRECATED_fc_ocr_WRONG_ORIENTATION.pkl` | ⛔ **作廢**，46% 的字顛倒，任何基於它的讀值全錯 |
> | `orient2.py` | ✅ pipeline 入口（重跑會產生 fc_ocr2.pkl，很慢，非必要別重跑） |
>
> **下一步只有兩步**：
> 1. 把 `ocr5.py` 的 `CHARS` 限縮成 `A-Za-z0-9+/=` 重跑 OCR
>    （base64 對單字元錯誤零容忍；目前 template matcher 會混淆 V/m、5/s、I/l/1、O/0）
> 2. 用**字元級 overlap** 把 96 張接龍成一條 base64 字串 → 解碼
>
> 完整脈絡見 [status.md](../../../status.md) 的 False_Continuity 段落（修正 1~10）。


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
python ocr5.py             # -> fc_ocr.pkl  ⛔ 方向會錯 46%，改跑 orient2.py
```

## 檔案說明

| 檔案 | 作用 |
|---|---|
| `cc.py` | 8-connected component labeling（本機沒 scipy 時的替代，現在 scipy 已裝可以換掉） |
| `glyphs6.py` | 主 pipeline：±90° 全範圍去斜 → 180° 正反判定 → per-glyph 自適應門檻 → 切行切字 |
| `ocr5.py` | DejaVu Sans Mono template matching OCR，參數已用已知正解調校到 95% |
| `refine.py` | 嘗試用「紙張邊緣」過濾誤判的 faint（**這條路失敗了**，留著當負面紀錄） |
| ~~`fc_ocr.pkl`~~ | ⛔ **已作廢並改名為 `DEPRECATED_fc_ocr_WRONG_ORIENTATION.pkl`**，46% 的字顛倒 |
| `fc_ocr2.pkl` | ✅ **方向已修正的 OCR 結果**，直接 load 即可（由 `orient2.py` 產生） |
| `orient2.py` | ✅ 正確的方向判定：每張在 `deg` 與 `deg+180` 各跑完整 OCR，取 template 匹配較好者 |

## fc_ocr2.pkl 結構

```python
import pickle
d = pickle.load(open('fc_ocr2.pkl','rb'))   # 每筆另有 'deg' / 'score' / 'alt'
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

---

## 交叉驗證腳本（crypto session 加入，2026-09-18）

這三支是**獨立於原 pipeline 重寫**的驗證腳本，用來交叉確認關鍵結論。
放在這裡是因為「用不同實作重跑得到相同結果」比單一實作的自我驗證可信得多。

| 檔案 | 驗證什麼 | 結果 |
|---|---|---|
| `xcheck_pair.py` | 48 對 + 48 單張結構 | ✅ 成立。輪廓 PCA + 72 角度 bin signature（允許 180° roll），真對距離 **恰為 0.000**，次佳 ≥0.011，斷層乾淨 |
| `xcheck_diff.py` | 每對的差異區域數 | ✅ **47 對 = 1 區域，1 對 = 3 區域**。原圖可直接相減（對內無相對旋轉） |
| `xcheck_orient.py` | 180° 方向判定是否可靠 | 🔴 **44/96 需翻轉（45.8%）**，獨立確認原 pipeline 的方向 bug |

`xcheck_orient.py` 的方法：每張分別在 `deg` 與 `deg+180` 下跑完整 OCR，
比較平均 template 最佳匹配距離——顛倒的字配不到正確 template，所以匹配距離會明顯較差。
這比「基線 std vs 頂線 std」的統計啟發式可靠。

執行方式同其他腳本（需先在 scratchpad 解壓 `fc/`）：
```bash
python xcheck_pair.py     # -> mydist.pkl
python xcheck_diff.py     # 需要 mystruct.pkl（由 xcheck_pair 的分組產生）
python xcheck_orient.py   # -> orient2.pkl
```
