# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Context

這是一場名為 AEGIS 的 Catch The Flag 比賽
時間: 2026/09/17 10:00 - 2026/09/19 19:00
網址: https://aegis2026.ctfd.io/
FLAG 形式為：AEGIS{printable_ascii+}

這不是軟體專案，而是 CTF 解題工作區：沒有 build / lint / test，也沒有 git。
每一次「執行」都是針對單一題目的解題腳本或工具指令。

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

解壓縮與中間產物請放進 scratchpad 目錄，不要污染題目資料夾。

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
