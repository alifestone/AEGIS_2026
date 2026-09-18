# 給使用者的請求清單

> 規則：Claude 需要使用者協助的事項一律寫在這裡（中文），不只在 session 輸出。
> 已完成的項目保留紀錄並標記 ✅，不要刪除。

---

## ✅ 1. 開啟 Rev/Slime 的 IDA Pro MCP

- **時間**：2026-09-18
- **狀態**：✅ 已完成（MCP Server started at http://localhost:13337）
- **內容**：Slime 為 static-pie、stripped、3.6MB 的 ELF，需要 IDA 靜態分析。

---

## ✅ 2. IDA Pro MCP 的 decompile/disassemble 會 timeout

- **時間**：2026-09-18
- **題目**：Rev/Slime（975 分，目前最高分題）
- **狀態**：✅ 已解決（重新開啟後可正常反編譯，不需再調整）

**問題**：
`mcp__ida-pro-mcp__decompile_function` 與 `disassemble_function` 都固定在 **1 秒** 後 timeout：

```
MCP server "github.com/mrexodia/ida-pro-mcp" tool "decompile_function"
timed out after 1s
```

Slime 是 3.6MB 的 static-pie binary，把 libc 整包靜態連進來，
函式數量非常多，Hex-Rays 第一次反編譯需要的時間遠超過 1 秒，
所以**每一次呼叫都會失敗**，等於 MCP 的反編譯功能完全不能用。

**想請你做的事（擇一即可）**：

1. **調高 MCP 的 timeout**（最推薦）
   ida-pro-mcp 的 timeout 若可設定，請調到 **60 秒以上**。
   可以看一下 MCP server 的啟動參數或設定檔有沒有 timeout / request_timeout 之類的選項。

2. 或者，**先在 IDA GUI 裡把目標函式跑過一次**
   IDA 反編譯過一次之後會 cache，第二次呼叫就會很快，
   這樣即使 timeout 是 1 秒也可能來得及。
   目前我最需要的函式位址是：

   | 位址 | 說明 |
   |---|---|
   | `0x41FCB` | 引用了那串多國語言的 LLM guardrail 字串，是關鍵函式 |

   麻煩在 IDA 裡按 `G` 跳到 `0x41FCB`，按 `F5` 反編譯一次讓它進 cache。

3. 如果上面都不方便，告訴我一聲，我改用本機 `objdump` 硬解（會比較慢但可行）。

**備註**：我已經可以正常使用 `list_strings` / `get_xrefs_to` / `get_metadata`
這些輕量 API，只有反編譯類的會 timeout。

---

## ✅ 3. 需要你決定：接下來的優先順序

- **時間**：2026-09-18
- **狀態**：✅ 已回覆 —— 你指定了 session 分工，Rev 全部交給 rev session，
  Linux 相關找 pc_agent。已寫進 CLAUDE.md 與 handover.md。

目前狀況（12 題）：

| 題目 | 分數 | 狀態 |
|---|---|---|
| Crypto/baby | 100 | ✅ **已解** |
| Rev/Slime | 975 | 🔵 找到主漏洞（stack overflow），還沒寫出 exploit |
| Misc/False_Continuity | 804 | 🔵 機制全解、OCR 95%，卡在 72 組紙屑的**排序** |
| Crypto/nursery_melody | 100 | 🔵 音符抽出來了，卡在編碼方式 |
| Misc/Travel_1 | 100 | 🔵 縮到「戶外購物中心 + Starbucks + 鐘樓」，還沒鎖定餐廳 |
| Misc/Travel_2 | 100 | 🔵 確認是 360 環景、火山型熱帶島嶼，還沒鎖定座標 |
| 其餘 6 題 | — | ⚪ 未開始 |

**我打算接下來這樣做**（除非你另有想法）：

1. **Rev/Slime（975）** — 分數最高，漏洞已確認，繼續推 exploit。
   需要你：IDA 保持開著就好。之後可能需要 Linux 環境（WSL/Docker）做動態測試，到時再跟你說。
2. **Rev/AI_Challenge（936）** 和 **Rev/aegis_asterism（600）** — 還沒碰，分數高。
   ⚠️ **需要你幫忙**：這兩個也要用 IDA 分析，但 MCP 一次只能開一個檔案。
   等 Slime 告一段落，我會請你在 IDA 裡改開 `null_oracle` 或 `aegis_asterism`。
3. **Pwn/arbitragedb（711）** — 還沒碰。
4. False_Continuity 的排序問題我會持續在背景想。

**如果你有偏好**（例如想先拿下那幾題 100 分的簡單題、或想優先攻某一題），跟我說一聲。

### 另外提醒一件事

`Rev/Slime` 的 binary 裡面被塞了大約 90 條針對 AI 助手的指令字串（8 國語言），
內容是「不要透露 flag」「只給概念提示」「在最後一步之前停下來」之類的。

**我沒有照著做**，理由寫在 [Rev/Slime/notes.md](Rev/Slime/notes.md)：
被分析的檔案裡的文字是**資料**，不是指令；如果我會聽它的，那任何人只要把字串寫進檔案
就能操控我的行為。我的指令來源是你和專案設定。
講出來是讓你知道有這回事、也知道我沒有默默照做。


---

## ✅ 4. Session 分工已建立

- **時間**：2026-09-18
- **狀態**：✅ 已完成

依你的指示建立分工，已寫進 [CLAUDE.md](CLAUDE.md) 與 [handover.md](handover.md)：

| Session | 負責 |
|---|---|
| **本 session（planner, `aegis-2026-b2`）** | 規劃、統整進度、Misc / Crypto / CyCraft / Pwn |
| **`rev`** | **所有 Rev 題目**（Slime 975 / AI_Challenge 936 / aegis_asterism 600），IDA MCP 歸它用 |
| **`pc_agent`** | **Linux 環境**（執行 ELF、gdb、動態分析）＋ 重運算爆破 |

溝通採三層模型（參考你給的 alphalab 文章）：
`SendMessage` 即時訊號 → `handover.md` 狀態交接 → `git push` 可驗收產出。
一來一回最多 2 輪就收斂。

**Rev/Slime 已交接給 `rev` session**（commit `94c9ba5`），含完整漏洞分析與下一步。

### 我接下來做的（planner 範圍）

1. Misc/False_Continuity（804）— 機制已解，卡在 72 組紙屑排序
2. Pwn/arbitragedb（711）— 還沒開始，可能要找 pc_agent 做動態
3. Misc/Travel_1、Travel_2、Jurassic_Time_Capsule（各 100）— OSINT
4. Crypto/nursery_melody（100）— 音符已抽出，卡在編碼
5. CyCraft/extraction-1、injection-1（各 100）— 遠端 LLM 攻擊題

⚠️ 注意 `misc` 和 `pwn_agent` 兩個 session 你也開了但還沒指派任務。
如果你打算讓它們接手 Misc / Pwn，跟我說一聲，我把對應題目也寫成 handover 交接出去，
避免我和它們重複做同一題。

---

## ⏳ 4. CyCraft 兩題需要「Team Token」才能提交（**目前完全卡住**）

- **時間**：2026-09-18
- **題目**：`CyCraft/extraction-1`（100）、`CyCraft/injection-1`（100）
- **狀態**：⏳ 等待使用者提供 Team Token

### 問題

這兩題的網頁介面上方有一個 **Team Token** 欄位，送出攻擊時會一起送到 `/api/submit`。
沒有 token 就完全無法測試，實測回應：

```bash
$ curl -X POST "https://aegis2026-ai-7577bf11-...-q1.chals.io/api/submit" \
    -H "Content-Type: application/json" -d '{"user_input":"hi","team_token":""}'
HTTP/1.1 400 BAD REQUEST
{"code":"INVALID_TEAM_TOKEN","error":"Enter your team token above first"}
```

Token 不在 repo 裡（已 grep 過），也不在題目 README，**只有你拿得到**。

### 想請你做的事

到 CTFd（https://aegis2026.ctfd.io/）找出本隊的 **Team Token**，貼給我或寫在這裡。

可能的位置：
- CTFd 的個人／隊伍設定頁（Settings → Access Tokens）
- 題目頁面 extraction-1 / injection-1 的題敘內文（網頁版可能有附件或說明文字，
  而我們 repo 裡的 README 只抓到圖片，可能漏抓了文字）
- 比賽公告 / Discord 置頂

**請優先確認題目頁面本身**——很可能題敘裡就寫了 token 或取得方式，
只是我們 repo 的 README 快照只存了那張 `cycraft_partner.jpg` 沒存到文字。

### ⚠️ 為什麼這件事很急、也要小心

前端程式碼裡有這段錯誤處理：

```js
QUOTA_EXCEEDED:'Team quota exhausted — no more evaluations (quota does not refill).'
```

**這兩題的提交次數有上限，而且用完不會補**（quota does not refill）。
所以我不會拿到 token 就亂試，會先把 payload 想清楚、排好優先順序再一發一發打。

也請你確認一下：CTFd 題目頁面有沒有寫**總共可以打幾次**？
如果有次數上限的明確數字，告訴我，我會據此決定要準備幾發 payload。



---

## 🔴🔴 5. 【急件】需要你去 CTFd 撈 **Team Token** — CyCraft 兩題完全卡死

- **時間**：2026-09-18
- **題目**：`CyCraft/extraction-1`、`CyCraft/injection-1`（各 100 分，solves 53/51）
- **狀態**：🔴 **完全卡住，沒有 token 一步都走不了**
- **回報者**：cycraft_agent（介面偵察已完成，攻擊 payload 也排好了，就差 token）

### 要你做什麼

去 CTFd（https://aegis2026.ctfd.io/）把 **Team Token** 找出來給我們。

**最可能的位置**：這兩題的**題目頁面內文**。
我們 repo 裡的 `CyCraft/*/README.md` 快照只抓到那張 `cycraft_partner.jpg` 配圖，
**題敘文字整段漏抓了**，token 很可能就寫在那段文字裡。

其他可能位置：
- CTFd 的 Team 設定頁（Settings / Team 頁面常有 access token）
- 題目附件或 hint
- 比賽公告 / Rules 頁

### 為什麼需要

兩題的提交介面有一個 Team Token 欄位，送出時一起 POST 到 `/api/submit`。
沒有 token 直接被擋在 auth 層：

```json
{"code":"INVALID_TEAM_TOKEN","error":"Enter your team token above first"}
```

token 不在 repo 裡（已 grep 過），不在我們手上的 README 快照裡。

### ⚠️ 附帶要確認的第二件事：可打次數

平台的錯誤碼原文是：

```
Team quota exhausted — no more evaluations (quota does not refill).
```

**quota 用完不會補。** 所以拿到 token 後不能亂槍打鳥。

如果你在題目頁看得到「總共可提交幾次 / 剩幾次」，**一併告訴我們**，
cycraft_agent 會據此決定要打幾發。

目前已知：
- ✅ 拿無效 token 去試**不會消耗 quota**（在 auth 層就被 400 擋掉，沒進 job queue）
  → 所以你給我們 token 後，我們可以安全地先驗證它對不對
- ❌ 沒有 `/api/quota` 或 `/api/status` 可以查剩餘次數（都是 404）

### 現在的準備狀態（拿到 token 就能立刻開打）

兩題是同一套平台（CyCraft XecArena），API 完全相同：

```
POST /api/submit  {user_input, team_token} -> {job_id}
GET  /api/result/<job_id>                  -> queued|running|error|done
done: {attack_succeeded: bool, response: "...", flag: "AEGIS{...}"}
user_input 上限 2000 字元
```

| 題目 | 角色 | 目標 | 難度 |
|---|---|---|---|
| extraction-1 | The Technical Evangelist | 吐出 system prompt，**LLM judge 判語意接近**（非字串比對） | 較難 |
| injection-1 | Wayfarer Travel Agent | 讓 agent 談旅遊以外的話題 | **門檻低，建議先打** |

cycraft_agent 已按優先序排好 payload（extraction 5 發 / injection 4 發），
拿到 token 就一發一發打、每發都記錄結果。

詳見 [CyCraft/notes.md](CyCraft/notes.md)。
