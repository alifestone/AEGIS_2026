# Pwn/arbitragedb — 靜態分析筆記

> 分析環境：Windows + objdump/readelf（本機無法執行 ELF）。
> 以下位址均為**檔案偏移 / PIE 基底相對位址**，實際執行需加上 PIE base。

## 1. 保護機制

```
ELF 64-bit PIE, dynamically linked, stripped
FLAGS   = BIND_NOW          → Full RELRO（GOT 唯讀，不能改 GOT）
FLAGS_1 = NOW PIE           → PIE 開啟，需 leak
GNU_STACK = RW（無 E）      → NX 開啟
__stack_chk_fail 有 import  → Canary 開啟
```

libc：**Ubuntu GLIBC 2.43-2ubuntu2.3**（很新，`GNU C Library ... stable release version 2.43.`）
編譯器：GCC (Ubuntu 13.3.0-6ubuntu2~24.04)

**Full RELRO + PIE + NX + Canary 全開** → 需要 info leak + ROP，不能改 GOT。

## 2. 指令介面

`main` @ `0x6a03`：`fgets(buf, 0x1008, stdin)` 進 `0x1010` 的 stack buffer，
prompt 為 `adb> `，dispatch @ `0x6b07`：

| 指令 | handler | 說明 |
|---|---|---|
| `QUIT` | — | 離開 |
| `IMPORT ...` | `0x4988` | **漏洞在這**（見下） |
| `FILECHECK <name>` | `0x41a9` | 讀 `.chk` 檔算 HMAC |
| 其餘 | `0x67f8` | SELECT 查詢（`SELECT 1` / `sys_imports` / `sys_tables` / `FROM <table>` …） |

啟動時 `argc` 必須為 2，argv[1] 是 state 目錄（否則印 `internal`）。

## 3. seccomp（重要：決定 exploit 形態）

`0x30e5` 安裝 seccomp BPF。**若環境變數 `ADB_NO_SECCOMP` 存在則整個跳過**
（`getenv` @ `0x3103`，遠端當然沒有，本地測試可用它關掉）。

allowlist（`SECCOMP_RET_ALLOW = 0x7fff0000`），預設動作 `0x50001`
= `SECCOMP_RET_ERRNO | EPERM`（**不是 KILL**，syscall 只會回 -EPERM）：

```
0   read          1   write         3   close        5   fstat
8   lseek         12  brk           15  rt_sigreturn
60  exit          231 exit_group
257 openat        262 newfstatat
```

→ **沒有 execve / execveat，沒有 mmap / mprotect。**
→ 題目說「RCE」，但實際只能做 **open + read + write 的 ROP chain（ORW）**
   把 `/home/arbitragedb/flag` 讀出來印到 stdout。不能拿 shell。
→ 沒有 mprotect ⇒ **不能跳去 shellcode**，必須純 ROP（或 SROP，`rt_sigreturn` 有開）。
→ `open`(2) **沒開**，只有 `openat`(257)。用 `openat(AT_FDCWD=-100, path, 0, 0)`。

## 4. 主漏洞：IMPORT 的 heap overflow（clamp 後用 max 當 memcpy 長度）

### 4.1 IMPORT 前半是安全的

`0x4988` handler：

```c
sscanf(line, "IMPORT %63s FORMAT ADB1 SIZE %ld", name, &size);   // 0x4a0a
if (ret != 2 || size < 0 || size > 0x4000) → "import" 錯誤       // 0x4a1e~0x4a3c
buf = malloc(size);                                              // 0x4a5c
fread(buf, 1, size, stdin);  必須剛好讀滿 size                    // 0x4aa3
if (size <= 0x11 || memcmp(buf, "ADB1", 4) != 0) → 錯誤          // 0x4ae0~0x4afc
off = 0x10;   // 跳過 16 byte header
```

接著解三個 LEB128 varint（decoder @ `0x44bb`，bounded、最多 10 bytes，安全）：

```c
varint(buf+off, size-off, &adv, &A);   off += adv;   // 0x4b65  → A
B = parse_rec(buf+off, size-off, &adv);              // 0x4bbc  → B（0x4566）
varint(buf+off, size-off, &adv, &C);   off += adv;   // 0x4bfe  → C
if (off >= size || C > 0x80) → 錯誤                  // 0x4c32~0x4c49
handle(name, buf+off, size-off, B, C);               // 0x4c94  → 0x4604
```

### 4.2 漏洞在 `0x4604`

參數：`rdi`=name, `rsi`=payload, `rdx`=**remaining = size-off**, `rcx`=B, `r8`=C

```c
alloc = B + 0x18;                      // 0x4624
if (alloc > 0x1000) alloc = 0x1000;    // 0x4630  ← 配置量被 clamp 到 0x1000
p = malloc(alloc);                     // 0x4649
memset(p, 0, alloc);

copylen = C;                           // 0x4672
if (remaining >= copylen)              // 0x467a  cmp remaining, copylen / jae
    copylen = remaining;               // 0x4684  ← 取「較大者」，不是較小者！
memcpy(p, payload, copylen);           // 0x469e  ★ HEAP OVERFLOW
```

**`alloc` 被 clamp 到 0x1000，但 `copylen` 取的是 `max(remaining, C)`。**
`remaining` 完全由攻擊者控制（IMPORT SIZE 最大 0x4000），只要讓
`remaining > 0x1000`，就能溢出 heap chunk 最多約 **0x3000 bytes 的任意內容**。

### 4.3 觸發條件（全部可滿足）

- `size` 上限 0x4000 → `remaining` 可達約 0x3fe0
- `C <= 0x80` 的檢查**不影響 copylen**，因為走的是 `remaining` 那條路
- `B` 只影響 `alloc`，設小一點（例如 0）讓 `alloc = 0x18`，溢出更多
- 溢出內容 = payload 尾段，**完全可控、無 bad char 限制**（是 fread 讀進來的 raw binary）

### 4.4 溢出後發生什麼

`0x4604` 後續會把資料搬進 **BSS 的全域陣列**（不是 heap）：
- import 記錄表 @ `0x1ee5d70`（stride 0x78，上限 16 筆，counter @ `0x1ee64f8`）
- sys_imports 表 @ `0x1ee4170`（stride 0x38，上限 128 筆，counter @ `0x1ee5d70`）
- 結尾 `free(p)`（`0x497b`）

所以溢出目標是**同一 heap arena 裡相鄰 chunk 的 metadata**，
之後的 `free(p)` / 後續 `malloc` 就是 glibc 2.43 的 heap exploitation。

## 5. 其他已檢查、確認安全的路徑

- **FILECHECK**（`0x41a9`）：路徑驗證器 `0x40e7` 要求檔名長度**剛好 0x44**，
  前 64 字元必須是 hex（`isxdigit` 等價檢查），後綴必須是 `.chk`
  → **無法 path traversal**。檔案大小限制 0x1000 進 0x1010 buffer，安全。
  用 `openat(dirfd, ...)` 相對於啟動時存的 state 目錄 fd（`0x1ee6500`）。
- **varint decoder**（`0x44bb`）：有 bounds check（`>= len` 或 `> 9` 就 fail），安全。
- **SELECT** 查詢路徑：目前看是 whole-string `strcmp`/`strcasestr` 比對固定字串，
  沒有動態格式字串。`printf` 的 format 都是 rodata 常數 → 無 format string bug。
- `formal_state/` 下的檔案（TSV / .bti / .adb / .chk）都是**啟動時讀的正常資料**，
  `.bti` 內容只是 `generated covering index placeholder`，不是二進位結構。
  遠端我們無法改這些檔案 → **攻擊面只有 stdin 的指令**，parser fuzzing 方向可以收掉。

## 6. Exploit 路線（待 pc_agent 動態驗證）

1. **Leak**：需要 PIE base + libc base。候選管道是把溢出寫進相鄰 chunk 後，
   透過 `SELECT ... sys_imports`（`0x54ce`）把 BSS/heap 內容印出來。
   → 待動態確認 `sys_imports` 印了哪些欄位、能不能印出指標。
2. **Control flow**：Full RELRO 不能改 GOT；沒有 mprotect 不能放 shellcode。
   → 目標是劫持 **stack return address**（heap overflow → 某個指標 → 寫 stack），
     或 glibc 2.43 的 house-of-* / tcache poisoning 打 `__libc_argv` / 環境。
3. **Final payload**：ORW ROP chain
   ```
   openat(AT_FDCWD, "/home/arbitragedb/flag", O_RDONLY, 0)
   read(fd, buf, 0x100)
   write(1, buf, 0x100)
   ```
   （`rt_sigreturn` 有開 → SROP 是備案，可以一次設好所有暫存器）

## 7. 給 pc_agent 的動態分析需求

見 status.md / SendMessage 內容。重點：
- 用 `ADB_NO_SECCOMP=1` 先在無 seccomp 下驗證 crash 與 leak，再開 seccomp 驗證 ORW
- 跑法：`./arbitragedb formal_state`（argv[1] 必須是 state 目錄）
- 用題目附的 libc/ld：`patchelf --set-interpreter ./ld-linux-x86-64.so.2 --set-rpath . arbitragedb`
