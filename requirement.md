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
