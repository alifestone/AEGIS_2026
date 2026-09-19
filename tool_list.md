# Introduction
To AI Agent: 如果需要可以使用以下工具。如果沒有找到該工具請問我

> 註：本機可能尚未預先安裝，使用前請先依照各工具說明進行下載與環境配置。

---

# Tool List

## 1. OWASP CVE Lite CLI
- **官方連結**：
  - [CyberSecurityNews 介紹](https://cybersecuritynews.com/owasp-cve-lite-cli-tool/amp/)
  - [GitHub: OWASP/cve-lite-cli](https://github.com/OWASP/cve-lite-cli)
- **工具功能（可以做到哪些事）**：
  - **本地優先的相依套件掃描**：專為 JavaScript / TypeScript 專案設計，支援 `npm`、`pnpm`、`Yarn`、`Bun` 的 Lockfile。比對 Google OSV（Open Source Vulnerabilities）開源漏洞資料庫。
  - **隱私與高安全性**：全流程於本機執行，無需上傳程式碼、環境變數或機密金鑰至外部雲端，支援離線快取資料庫。
  - **可直接執行的修復建議**：不只列出 CVE，更針對直接與間接相依性進行解析，直接提供排序好的更新修復指令（如 `npm install <pkg>@<ver>`）。
  - **開發流程前置檢測**：適合作為 push 或 CI/CD 流程前的終端自檢工具，降低反饋延遲。
- **使用方法**：
  ```bash
  # 1. 全域安裝或使用 npx 直接執行
  npm install -g cve-lite-cli
  # 或免安裝直接跑：npx cve-lite-cli

  # 2. 針對目標專案進行弱點掃描
  cve-lite /path/to/project --verbose

  # 3. 若在當前專案目錄下直接執行：
  cve-lite .
  ```

---

## 2. Claude-Red
- **官方連結**：
  - [GitHub: SnailSploit/Claude-Red](https://github.com/SnailSploit/Claude-Red)
- **工具功能（可以做到哪些事）**：
  - **AI 紅隊專屬技能庫（Agent Skills）**：由紅隊資安團隊 SnailSploit 所維護，以結構化 `SKILL.md` 注入專家級攻擊與滲透思維，使 AI Agent（如 Claude / Antigravity）化身情境感知型攻擊助手。
  - **涵蓋廣泛的進攻性資安領域**：
    - **Web 漏洞利用**：SQLi、SSRF、CSRF、Path Traversal、原型污染（Prototype Pollution）、XSS 攻擊鏈組合。
    - **二進位與 Pwn 逆向**：Stack Overflow、Heap Exploitation / Shaping、ROP 鏈建構、Format String 格式化字串、`ret2libc`。
    - **EDR / 防毒規避**：Direct Syscalls、API Unhooking、AMSI Bypass、ETW Patching。
    - **網路與 C2**：C2 通訊協定設計、DNS Tunneling、ICMP 資料外洩、Domain Fronting。
    - **雲端與容器逃逸**：Kubernetes (K8s) Breakout、雲端 IMDS 元數據濫用、IAM 權限列舉與提權。
- **使用方法**：
  - 本身並非傳統獨立執行檔，而是一組 **Skill 知識/操作模組**。
  - 將 repository 內容或特定領域的 `SKILL.md` 配置在 Agent 的技能目錄下（例如 `.claude/skills/` 或支援 Agent Skill 的工作區環境）。
  - 在與 AI 互動中提問對應的安全主題（如「分析此二進位檔案的 ROP Gadgets」或「構造進階原型污染 PoC」），AI 會自動載入對應技能並採取標準紅隊手法引導與驗證。

---

## 3. Agentic Bug Hunter
- **官方連結**：
  - [GitHub: Awarexone/Agentic-Bug-Hunter](https://github.com/Awarexone/Agentic-Bug-Hunter)
  - [CyberSecurityNews 報導](https://cybersecuritynews.com/bughunter-bug-bounty-toolkit/)
- **工具功能（可以做到哪些事）**：
  - **端到端自主漏洞獵捕（Bug Bounty Workflow）**：自動化串聯目標資訊收集（Recon）、攻擊面枚舉、弱點挖掘、利用驗證（PoC Validation）到報告生成全流程。
  - **直出合規賞金報告**：可自動生成符合 HackerOne、Bugcrowd、Intigriti、Immunefi 格式的專業通報報告。
  - **獵捕記憶（Hunt Memory）**：具備長期跨階段記憶，能記錄目標歷史資產特徵、攻擊路徑，支援中斷後隨時無縫繼續。
  - **多領域支援**：涵蓋傳統 Web2、Web3 / 智能合約審計、以及針對大型語言模型（LLM）應用的安全檢驗。
  - **靈活的模型切換**：可作為 Claude Code 的外掛使用，也可獨立以 CLI 運作；支援切換至本地開源模型（如 Ollama），達成零額外 API 成本與完全離線工作。
- **使用方法**：
  ```bash
  # 1. 複製專案庫並安裝依賴
  git clone https://github.com/Awarexone/Agentic-Bug-Hunter.git
  cd Agentic-Bug-Hunter
  pip install -r requirements.txt

  # 2. 設定 API 金鑰或本地 Ollama 模型環境
  export ANTHROPIC_API_KEY="your-api-key"
  # 或使用本機 Ollama 服務

  # 3. 執行 CLI 工具啟動獵捕流程
  bughunter --target example.com --mode recon
  bughunter --target example.com --mode hunt
  ```

---

## 4. Pentest-Swarm-AI
- **官方連結**：
  - [GitHub: Armur-Ai/Pentest-Swarm-AI](https://github.com/Armur-Ai/Pentest-Swarm-AI)
- **工具功能（可以做到哪些事）**：
  - **群體智慧滲透測試（Swarm Intelligence）**：採用分散式協同機制（Stigmergy），不同專長的小型 Agent 透過 PostgreSQL + `pgvector` 黑板非同步溝通，以帶有衰減特性的「資訊素權重」自發聚集在最有價值的攻擊路徑上。
  - **湧現式攻擊鏈（Emergent Attack Chains）**：不需寫死線性工作流，偵察 Agent 發現端點會觸發分類 Agent，進而喚醒對應 Exploit Agent 動態組合漏洞利用鏈。
  - **資安工具原生編排**：整合 ProjectDiscovery 系列（Nuclei、Subfinder、HTTPX、Katana）與 Nmap，支援橋接 SQLMap、Metasploit 等傳統工具。
  - **雙層範圍護欄（Scope Guard）**：內建雙層 Target Scope 檢驗機制，確保自主代理人不超出測試授權範圍。
  - **應用場景**：支援 Bug Bounty 自動打靶、CTF 競賽解題、持續性外部攻擊面管理（EASM）。
- **使用方法**：
  ```bash
  # 1. 準備 PostgreSQL (需啟用 pgvector) 及 Go 環境，複製專案並編譯
  git clone https://github.com/Armur-Ai/Pentest-Swarm-AI.git
  cd Pentest-Swarm-AI
  go build -o pentest-swarm

  # 2. 編輯配置檔 config.yaml（設定目標白名單範圍、LLM 後端如 Claude / Ollama、資料庫連線）
  # 3. 啟動 Swarm 代理群對目標進行自主滲透
  ./pentest-swarm run --scope scope.txt
  ```

---

## 5. Nuclei 及相關生態 (Nuclei / Nuclei-MCP / Nuclei-Templates)
- **官方連結**：
  - [GitHub: projectdiscovery/nuclei](https://github.com/projectdiscovery/nuclei)
  - [GitHub: addcontent/nuclei-mcp](https://github.com/addcontent/nuclei-mcp)
  - [GitHub: projectdiscovery/nuclei-templates](https://github.com/projectdiscovery/nuclei-templates)
- **工具功能（可以做到哪些事）**：
  - **超高速、基於 YAML 模板的弱點掃描**：全球社群廣泛使用的開源掃描引擎，藉由社群共同維護的數千個 YAML 模板（nuclei-templates），快速檢測已知 CVE、零日漏洞、敏感檔案暴露、未授權存取與錯誤設定。
  - **多協定支援與並行處理**：基於 Go 語言的高並發設計，支援 HTTP、DNS、TCP、SSL、Websocket、Headless 瀏覽器等多元協定。
  - **Nuclei-MCP 整合 AI Agent**：透過 Model Context Protocol（MCP）將 Nuclei 的掃描功能封裝為標準工具介面，讓 AI Agent 能在對話或自主執行過程中主動觸發掃描、篩選模板、即時剖析目標資產與風險。
- **使用方法**：
  - **原生 Nuclei CLI**：
    ```bash
    # 1. 安裝 Nuclei
    go install -v github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
    # 或至 GitHub Releases 下載預編譯檔案

    # 2. 更新最新漏洞模板
    nuclei -ut

    # 3. 基本掃描與進階過濾
    # 掃描單一目標，限定高危與嚴重漏洞
    nuclei -u https://example.com -severity critical,high

    # 針對特定 CVE 模板目錄掃描
    nuclei -u https://example.com -t cves/2024/

    # 批次目標掃描並輸出 JSON 格式報告
    nuclei -l targets.txt -json-export results.json
    ```
  - **Nuclei-MCP（給 AI 工具如 Claude Desktop / Antigravity / Cursor 等使用）**：
    - 在對應的 MCP 設定檔（例如 `claude_desktop_config.json` 或 `mcp_config.json`）中註冊：
      ```json
      {
        "mcpServers": {
          "nuclei": {
            "command": "node",
            "args": ["/path/to/nuclei-mcp/build/index.js"]
          }
        }
      }
      ```
    - 配置完成後，AI Agent 即可直接在交談中呼叫 `nuclei_scan` 等工具指令自主執行掃描。

---

## 6. Open-Kritt
- **官方連結**：
  - [GitHub: Kritt-ai/open-kritt](https://github.com/Kritt-ai/open-kritt)
  - [官方網站: kritt.ai](https://kritt.ai)
- **工具功能（可以做到哪些事）**：
  - **任務拆解式 AI 程式碼審查（Decomposed Workflow）**：由獲取逾 150 萬美元賞金的頂尖黑客團隊 Blockian 開源，為避免「整包程式碼丟給 LLM」導致的嚴重幻覺與雜訊，將資安審查拆解為微型聚焦任務（Focused Tasks），並派發給多個 Agent 並行剖析。
  - **自動化驗證與 PoC 生成（Automated Verification）**：具備強大的後處理驗證機制，能自動撰寫測試腳本並執行 PoC 驗證，有效確認漏洞真實性，大幅剔除假警報（False Positives）。
  - **自託管資安研究基礎架構**：定位為「可客製化資安基礎設施」，使用者可依需求建立專屬的審計 Playbook 與審查管線，針對大型 Codebase 進行持續且深入的安全挖掘。
- **使用方法**：
  ```bash
  # 1. 複製專案並進行本地自託管部屬（建議使用 Docker）
  git clone https://github.com/Kritt-ai/open-kritt.git
  cd open-kritt
  docker-compose up -d

  # 2. 設定 LLM API 金鑰與目標專案程式碼路徑
  # 3. 定義或套用審查 Playbook，啟動平行審計管線進行程式碼掃描、自動驗證與產出 PoC 報告
  ```
---

## 7. Pwn / Exploit 開發工具鏈（`linux_agent` 專用，Arch Linux）

> **背景**：本賽事 Pwn 題附件皆為 Linux ELF，Windows 本機無法執行。
> `linux_agent`（Arch Linux）是團隊唯一能做動態分析的環境，以下清單即為它而寫。
> 分析範圍嚴格限制在題目給定的主機與 endpoint。

### 7.1 各題實際架構（先確認架構再裝工具）

planner 於 2026-09-19 用 `file` 實際檢查過附件，**三題架構不同，工具不能通用**：

| 題目 | 分數 | 架構 | 關鍵差異 |
|---|---|---|---|
| `Pwn/arbitragedb` | 100 | x86-64 dynamic PIE | 附 libc 2.43，需換 libc 測試 |
| `Pwn/aegis_factory` | 996 | x86-64 **static-pie, stripped** | 無符號、無動態連結，gadget 搜尋為主力 |
| `Pwn/Pool93` | 676 | ⚠️ **PowerPC64 big-endian** | **不是 x86**，必須 qemu 模擬 |
| `Pwn/SimpleHttpServer` | 740 | 無附件（純遠端） | 只有 `nc 0.cloud.chals.io 14627` |

⚠️ **`Pool93` 最容易踩坑**：`file` 顯示 `ELF 64-bit MSB ... 64-bit PowerPC`，
一般 x86 的 gdb / pwntools 預設設定都不適用。附件內已自帶 `qemu-user` deb 與 Dockerfile。

### 7.2 核心四件組（所有 Pwn 題都需要）

```bash
# 基礎
sudo pacman -S --needed python python-pip gdb base-devel

# pwntools —— exploit 腳本框架（remote()/ELF()/ROP()/cyclic()）
sudo pacman -S --needed python-pwntools     # 或 pipx install pwntools

# pwndbg —— GDB 增強，heap 題必備（heap/bins/tcache 指令）
git clone https://github.com/pwndbg/pwndbg && cd pwndbg && ./setup.sh
#（替代品：GEF `bata24/gef` 或 pwngdb，擇一即可，不要同時裝）

# ROP gadget 搜尋
sudo pacman -S --needed ropgadget
pip install --user ropper            # ropper 的搜尋語法比 ROPgadget 好用

# one_gadget —— 找 libc 內一發 execve("/bin/sh") 的位址
gem install one_gadget               # 需要 ruby：pacman -S ruby
```

### 7.3 題型專用

```bash
# ── arbitragedb：seccomp 分析（該題只放行 ORW，沒有 execve/mmap/mprotect）
gem install seccomp-tools            # seccomp-tools dump ./arbitragedb
sudo pacman -S --needed libseccomp

# ── arbitragedb：換 libc 測試（附件 libc 2.43 與系統版本不同）
sudo pacman -S --needed patchelf
# patchelf --set-interpreter ./ld-linux-x86-64.so.2 --set-rpath . ./arbitragedb
# 或直接：./ld-linux-x86-64.so.2 --library-path . ./arbitragedb formal_state

# ── Pool93：PowerPC64 模擬（⚠️ 必要，否則跑不起來）
sudo pacman -S --needed qemu-user qemu-user-static docker docker-compose
sudo systemctl start docker && sudo usermod -aG docker $USER   # 需重新登入生效

# 最省事：附件自帶完整 Docker 環境，直接跑起本地靶機（埠 4496）
#   cd 2026_pwn_guest && ./run.sh
# 跨架構除錯：
#   qemu-ppc64 -g 1234 ./pool93        # 一個終端
#   gdb ./pool93 -ex 'target remote :1234'   # 另一個終端

# ── aegis_factory：stripped static-pie，需要反編譯器補符號
sudo pacman -S --needed ghidra        # 免費反編譯器（AUR 亦可）
sudo pacman -S --needed radare2       # 或 rizin + cutter
```

### 7.4 輔助

```bash
sudo pacman -S --needed strace ltrace ltrace xxd binutils elfutils
pip install --user angr               # 符號執行（重運算，本機 Windows 沒有）
# checksec 由 pwntools 提供：pwn checksec ./binary
```

### 7.5 一句話版本

**`pwntools` + `pwndbg` + `ropper`/`ROPgadget` + `one_gadget` 是通用四件組；
`seccomp-tools` 專治 arbitragedb 的 ORW 限制；`qemu-user` + `docker` 專治 Pool93 的 PowerPC。**

### 7.6 注意事項

- **不要在 Windows 本機跑題目 ELF**——這是使用者明確表達過顧慮的事項
  （見 requirement.md 第 9 項），改由 `linux_agent` 在它自己的環境執行。
- 遠端連線請**節制頻率**。`Rev/Slime` 題敘明文禁止 DDoS，其餘題目亦同理。
- 攻擊範圍限制在題目給定的 host/port，**不得外溢**到 CTFd 平台或任何其他主機。
