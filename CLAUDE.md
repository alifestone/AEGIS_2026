# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

這是一場名為 AEGIS 的 Catch The Flag 比賽
時間: 2026/09/17 10:00 - 2026/09/19 19:00
網址: https://aegis2026.ctfd.io/
FLAG 形式為：AEGIS{printable_ascii+}

這不是軟體專案，而是 CTF 解題工作區：沒有 build / lint / test。
每一次「執行」都是針對單一題目的解題腳本或工具指令。

本工作區**有 git**，remote 為 `https://github.com/alifestone/AEGIS_2026.git`，工作分支為 `main`。
這個 repo 是與 `pc_agent` 協作的同步媒介，push 規則見下方 Progress tracking。

## Repository layout

```
<Category>/<Challenge_Name>/
    README.md          # 題目 metadata（points、solves、challenge ID、connection、description）
    <attachments>      # 官方附件，維持原始檔名（含 hash suffix）不要改名
```

Category 為 `Rev` / `Misc` / `Pwn` / `Crypto` / `CyCraft`，共 12 題。
[README.md](README.md) 是全部題目的總表 + 完整題敘快照，改動題目時同步更新它。

每題資料夾的 README.md 是**官方題敘的唯一真實來源**，不要覆寫題敘內容；
解題筆記、payload、腳本另外新增檔案（例如 `solve.py`、`notes.md`）放在同一題資料夾內。

## Progress tracking (required)

所有解題進度必須記錄進 [status.md](status.md)，這是 CLAUDE.md 的硬性要求。
每題至少記錄：題名 / 分類 / 狀態（未開始・進行中・卡關・已解）/ 目前進展或卡點 / 取得的 flag。
每次在某題上有實質推進（找到關鍵線索、寫出 exploit、拿到 flag、確認某方向死路）就更新，不要等到全部做完才寫。

### 與 pc_agent 協作：push to main（硬性要求）

`status.md` 同時是與 `pc_agent` 的**共用狀態檔**——對方看不到本機檔案，只能透過 GitHub remote 同步。
因此每次更新 status.md 後要立刻 commit + push 到 `main`，否則 pc_agent 會拿到過期狀態並重複做白工。

```bash
cd 'D:\其他\資安\aegis_2026'
git pull --rebase origin main     # 先拉，避免蓋掉 pc_agent 的進度
git add status.md <本次相關檔案>
git commit -m "status: <題名> — <這次的進展>"
git push origin main
```

規則：
- **先 pull --rebase 再 push**：pc_agent 也會寫同一個檔案，直接 push 會衝突或覆蓋對方進度。
- 委派任務給 pc_agent **之前**先 push，確保對方讀到的題目檔案與 status 是最新的。
- 收到 pc_agent 回報結果後，把結果寫進 status.md 再 push 一次。
- commit 訊息用 `status:` / `solve:` / `notes:` 前綴 + 題名，方便雙方掃 log 對進度。
- flag 一拿到就 commit + push，這是避免雙方重複解題最關鍵的一步。

## Environment constraints

Windows 11 + Git Bash（Bash tool）與 PowerShell 並存。要注意：

- 路徑含中文（`D:\其他\資安\aegis_2026`）——Bash 中一律用引號包住路徑。
- **可用**：`python`(3.14, `C:\Python314`)、`file`、`unzip`、`xxd`、`curl`、
  mingw64 binutils（`strings` / `objdump` / `readelf` / `gdb`）、Pillow。
- **不存在**：`nc`、`7z`、`binwalk`、`pwntools`、`pycryptodome`、`z3`、`angr`。
  需要時先 `python -m pip install pwntools pycryptodome` 再用；
  遠端連線（`nc host port`）沒有 netcat，改用 Python socket 或 pwntools `remote()`。
- 附件內的 ELF 是 Linux x86-64，在此環境**無法直接執行**。動態分析需要 WSL / Docker；
  靜態分析走 IDA Pro MCP（`mcp__github_com_mrexodia_ida-pro-mcp__*`）或 `objdump`。
- **重運算一律外包給 `pc_agent`**：本機沒有 GPU／算力有限，凡是需要 CUDA 或長時間
  大量運算的工作（GPU hashcat／john 爆破、大規模 brute-force、z3 / angr 符號執行、
  ML 或 LLM 本地推論、長時間 fuzzing 等），不要在本機硬跑，改用 `SendMessage`
  把任務交給 `pc_agent`（先用 `ListAgents` 確認名稱）。交付時要附上：題目路徑、
  輸入檔位置、要跑的完整指令／腳本、預期輸出格式與時限，並把結果寫回 status.md。

解壓縮與中間產物請放進 scratchpad 目錄，不要污染題目資料夾。

## Tooling

### 外部工具清單

[tool_list.md](tool_list.md) 列出本次比賽可使用的外部工具（OWASP CVE Lite CLI、Claude-Red、
Agentic Bug Hunter、Pentest-Swarm-AI、Nuclei 生態、Open-Kritt），含官方連結、功能說明與安裝指令。
**遇到需要外部工具的情境時先查 tool_list.md**，裡面有的就照它的安裝方式裝起來再用；
清單裡沒有、又確實需要的工具，先問使用者，不要自行擴張安裝範圍。

注意 tool_list.md 內多數工具**本機尚未預裝**，使用前要依各條目的說明先配置環境。
其中 Nuclei / Agentic Bug Hunter / Pentest-Swarm-AI 偏向對外網站掃描，與本賽事
題型（Rev / Pwn / Crypto 為主）關聯較低，且掃描行為須嚴格限制在題目給定的
endpoint 範圍內，不要掃到 CTFd 平台本身或任何非題目主機。

### Claude-Red offensive skills（已安裝，77 個）

`~/.claude/skills/` 下已安裝 Claude-Red 技能庫，可直接用 Skill tool 呼叫。對應本賽事題型：

- **Pwn/arbitragedb** → `offensive-exploit-development`、`offensive-basic-exploitation`、
  `offensive-mitigations`、`offensive-crash-analysis`、`offensive-shellcode`、`offensive-toctou`
- **Rev/Slime、Rev/AI_Challenge** → `offensive-bug-identification`、`offensive-vuln-classes`、
  `offensive-fuzzing`
- **Crypto** → `offensive-crypto-attacks`（padding oracle、hash length extension、RSA、弱 PRNG）
- **CyCraft/extraction-1、injection-1** → `offensive-ai-security`（LLM prompt extraction / injection）
- **Misc/Travel_1、Travel_2、Jurassic_Time_Capsule** → `offensive-osint`、`offensive-osint-methodology`

技能庫原始 repo 保留在 `~/.claude/skills/claude-red/`，78 個技能中 `offensive-file-upload`
與 `offensive-rce` 兩個未安裝（被權限機制擋下），需要時再處理。

這些 skill 是**方法論參考**，不是自動化 exploit；套用時仍要針對題目實際狀況驗證。
攻擊範圍嚴格限制在 AEGIS 題目給定的主機與 endpoint，不得外溢到其他目標。

## Challenge-specific notes

- **Rev/Slime** — static-pie、stripped ELF，本體 3.6MB；配合遠端 `nc 36.226.134.123 2828`
  的存檔／金幣機制，屬於 game-save tampering 方向。題敘明文禁止 DDoS，攻擊遠端請節制連線頻率。
- **Rev/AI_Challenge** — `null_oracle` ELF 被剝除 section header（`no section header`），
  一般工具解析會失敗，需靠 program header / 動態段還原。題敘指明只有 Level 6 是真 flag。
- **Pwn/arbitragedb** — zip 內附 `arbitragedb`、`libc.so.6`、`ld-linux-x86-64.so.2`
  與 `formal_state/` 資料庫狀態（TSV tables + index + mvcc）。目標是 RCE，flag 在遠端
  `/home/arbitragedb/flag`，因此必須是 remote exploit，不是本地讀檔。
- **Misc/Jurassic_Time_Capsule** — **提交次數上限 10 次**，且題敘明示 EXIF 座標
  「不是真正的埋藏地點」。務必先在 status.md 推演到高信心再提交，每次提交都記錄下來。
- **Misc/Travel_1 / Travel_2** — OSINT，flag 格式嚴格：Travel_1 只取 Plus Code
  （不含地名），Travel_2 經緯度**截斷**至小數 4 位（truncate，不是四捨五入）。
- **CyCraft/extraction-1 / injection-1** — 純遠端 LLM 攻擊題（prompt extraction /
  prompt injection），只有 HTTPS endpoint 無附件，資料夾內的 jpg 只是題敘配圖。

## Flag handling

提交前確認格式為 `AEGIS{...}`，內容為 printable ASCII。
拿到 flag 立刻寫進該題 status.md 條目，避免重複解題。

## 與使用者溝通（硬性要求）

**任何需要使用者處理的請求，一律用中文寫進 [requirement.md](requirement.md)，不要只在 session 輸出。**
原因：直接輸出在對話裡的內容會被後續訊息洗掉，使用者會漏看。

適用情境包含但不限於：
- 需要使用者開啟／切換 IDA Pro MCP 載入的目標檔案
- 需要安裝工具、套件、或開啟某個 MCP server
- 需要使用者到 CTFd 平台提交 flag、或回報提交結果
- 需要使用者提供帳密、網路存取、或任何本 agent 無法自行取得的資訊

格式：每則請求標上時間與題目，寫清楚「要做什麼」與「為什麼需要」，
處理完的項目標記為已完成但保留紀錄，不要直接刪除。
