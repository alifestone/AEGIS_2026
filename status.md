# AEGIS 2026 — 解題進度

> 比賽時間：2026/09/17 10:00 – 2026/09/19 19:00 ｜ 平台：https://aegis2026.ctfd.io/
> FLAG 形式：`AEGIS{printable_ascii+}`
>
> **這個檔案是與 `pc_agent` 的共用狀態檔。** 每次更新後立刻
> `git pull --rebase origin main` → `git add` → `git commit` → `git push origin main`。
> 委派任務給 pc_agent 前先 push，收到結果後寫回這裡再 push。

狀態定義：`未開始` / `進行中` / `卡關` / `已解`

---

## 總覽

| # | 題目 | 分類 | 狀態 | Flag |
|---|------|------|------|------|
| 1 | baby | Crypto | 未開始 | — |
| 2 | nursery_melody | Crypto | 未開始 | — |
| 3 | extraction-1 | CyCraft | 未開始 | — |
| 4 | injection-1 | CyCraft | 未開始 | — |
| 5 | False_Continuity | Misc | 未開始 | — |
| 6 | Jurassic_Time_Capsule | Misc | 未開始 | — |
| 7 | Travel_1 | Misc | 未開始 | — |
| 8 | Travel_2 | Misc | 未開始 | — |
| 9 | arbitragedb | Pwn | 未開始 | — |
| 10 | AI_Challenge | Rev | 未開始 | — |
| 11 | Slime | Rev | 未開始 | — |
| 12 | aegis_asterism | Rev | 未開始 | — |

已解：0 / 12

---

## Crypto

### baby
- **狀態**：未開始
- **進展／卡點**：—
- **Flag**：—
- **可用 skill**：`offensive-crypto-attacks`

### nursery_melody
- **狀態**：未開始
- **進展／卡點**：—
- **Flag**：—
- **可用 skill**：`offensive-crypto-attacks`

---

## CyCraft

### extraction-1
- **狀態**：未開始
- **進展／卡點**：純遠端 LLM 攻擊題（prompt extraction），只有 HTTPS endpoint 無附件；
  資料夾內 jpg 僅為題敘配圖。
- **Flag**：—
- **可用 skill**：`offensive-ai-security`

### injection-1
- **狀態**：未開始
- **進展／卡點**：純遠端 LLM 攻擊題（prompt injection），同上。
- **Flag**：—
- **可用 skill**：`offensive-ai-security`

---

## Misc

### False_Continuity
- **狀態**：未開始
- **進展／卡點**：—
- **Flag**：—

### Jurassic_Time_Capsule
- **狀態**：未開始
- **進展／卡點**：⚠️ **提交次數上限 10 次**，題敘明示 EXIF 座標不是真正埋藏地點。
  務必推演到高信心再提交。
- **提交紀錄**：0 / 10（每次提交都要記在這裡：提交值 + 結果）
- **Flag**：—
- **可用 skill**：`offensive-osint`

### Travel_1
- **狀態**：未開始
- **進展／卡點**：OSINT。⚠️ flag 格式只取 **Plus Code**（不含地名）。
- **Flag**：—
- **可用 skill**：`offensive-osint`、`offensive-osint-methodology`

### Travel_2
- **狀態**：未開始
- **進展／卡點**：OSINT。⚠️ 經緯度**截斷**至小數 4 位（truncate，不是四捨五入）。
- **Flag**：—
- **可用 skill**：`offensive-osint`、`offensive-osint-methodology`

---

## Pwn

### arbitragedb
- **狀態**：未開始
- **進展／卡點**：zip 內附 `arbitragedb`、`libc.so.6`、`ld-linux-x86-64.so.2` 與
  `formal_state/`（TSV tables + index + mvcc）。目標 RCE，flag 在遠端
  `/home/arbitragedb/flag` → 必須是 **remote exploit**，不是本地讀檔。
- **Flag**：—
- **可用 skill**：`offensive-exploit-development`、`offensive-basic-exploitation`、
  `offensive-mitigations`、`offensive-crash-analysis`、`offensive-shellcode`、`offensive-toctou`

---

## Rev

### AI_Challenge
- **狀態**：未開始
- **進展／卡點**：`null_oracle` ELF 被剝除 section header，一般工具解析會失敗，
  需靠 program header / 動態段還原。題敘指明**只有 Level 6 是真 flag**。
- **Flag**：—
- **可用 skill**：`offensive-bug-identification`、`offensive-vuln-classes`

### Slime
- **狀態**：未開始
- **進展／卡點**：static-pie、stripped ELF，本體 3.6MB；配合遠端 `nc 36.226.134.123 2828`
  的存檔／金幣機制，屬 game-save tampering 方向。⚠️ 題敘明文禁止 DDoS，連線請節制。
- **Flag**：—

### aegis_asterism
- **狀態**：未開始
- **進展／卡點**：—
- **Flag**：—

---

## 委派給 pc_agent 的任務紀錄

| 時間 | 題目 | 任務內容 | 狀態 | 結果 |
|------|------|----------|------|------|
| — | — | — | — | — |

> 委派格式提醒：題目路徑 / 輸入檔位置 / 完整指令或腳本 / 預期輸出格式與時限。
