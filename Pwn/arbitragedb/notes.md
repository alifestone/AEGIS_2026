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

---

## 8. ★ Leak 管道：`SELECT ... sys_imports` 是 arbitrary read primitive

### 8.1 import 記錄結構（stride 0x78，BSS @ `0x1ee5d70 + 8`）

從 `sub_4604`（寫入）與 `sub_54ce`（列印）交叉比對得出：

| offset | 內容 | 在 sys_imports 怎麼被印出來 |
|---|---|---|
| `+0x00` | batch_id | `int:%ld` |
| `+0x08` | table_name char[0x18] | `%s`（`sub_1b40` 複製，上限 0x100） |
| `+0x20` | accepted_rows | `int:%ld` |
| `+0x28` | **sample 長度** | 傳給 encoder 當 len（encoder 內再 cap 到 0x100） |
| `+0x30` | inline sample buffer（0x20 bytes） | 當 `+0x50` 為 0 時的 fallback 來源 |
| `+0x50` | **sample 指標** | **非 0 就當成來源位址讀取** ★ |
| `+0x58` | aux 指標（0x80 的 chunk） | — |
| `+0x60`/`+0x68`/`+0x70` | payload ptr / remaining / C | — |

### 8.2 列印邏輯（`sub_54ce` @ `0x5604`~`0x563f`）

```c
len = rec[0x28];
src = rec[0x50] ? rec[0x50] : rec + 0x30;     // 0x5613 test/je
hex_encode(src, len, out, 0x280);             // sub_1c10
printf("ROW int:%ld %s int:%ld %s", rec[0], table_name, rec[0x20], "blob:<len>:<hex>");
```

encoder `sub_1c10`：`if (len > 0x100) len = 0x100;`（`0x1c4a`）然後
`hex(src, len)` → `blob:%zu:%s`。**沒有任何指標合法性檢查。**

### 8.3 這給了什麼

**控制 `rec[0x50]`（來源位址）+ `rec[0x28]`（長度）⇒ 每次可讀任意位址 0x100 bytes
並以 hex 印出來。** 這正是 PIE + Full RELRO 需要的 leak 原語。

而 `+0x50` / `+0x28` 都落在 heap overflow 可覆寫的範圍內
（記錄本身在 BSS，但 `+0x50` 存的是**指向 heap 的指標**，見下）。

### 8.4 免費的 heap leak（不用溢出就有）

`sub_4604` 的 `0x47ed` 分支：**當 `B != C` 時**會走
```c
q = malloc(0x520);  aux = malloc(0x80);
memcpy(q, payload, min(copylen, 0x80));
rec[0x50] = q;        // 0x485e  ← 存入 heap 指標
rec[0x28] = 0x20;     // 0x486a  ← 長度固定 0x20
rec[0x58] = aux;
free(q);              // 0x4889  ★ q 被 free 了，但 rec[0x50] 還指著它 → UAF
```

⚠️ **注意 `0x4889` 的 `free(q)`：`rec[0x50]` 變成 dangling pointer（UAF）。**
之後 `SELECT ... sys_imports` 會把這塊已釋放的 chunk 內容 hex 印出來
→ **tcache/fastbin 的 fd/key 指標會被直接印出來 ⇒ 免費的 heap base leak**
（glibc 2.43 有 tcache key 與 pointer mangling，印出來的是
 `mangled_fd = (chunk_addr >> 12) ^ next`，仍可推回 heap base）

這條路**不需要任何溢出**，只要送一個 `B != C` 的合法 IMPORT 再 `SELECT ... sys_imports`。
**請 pc_agent 優先驗證這點**，這是整條 exploit 最省事的起點。

### 8.5 完整 exploit 草案

1. **heap leak**：IMPORT（`B != C`）→ `SELECT 1 FROM sys_imports` → 讀 freed chunk 的 fd
   → 解 mangling 得 heap base
2. **libc leak**：用 heap overflow 覆寫某筆記錄的 `+0x50` / `+0x28`
   → 指向有 libc 指標的位置（例如 main_arena / stdout FILE 結構 / `__libc_argv`）
   → 再 `SELECT ... sys_imports` 印出來 → libc base
   （也可先讓 chunk 進 unsorted bin，其 fd/bk 直接指向 main_arena）
3. **PIE leak**：同法讀 BSS 裡存的程式指標，或從 stdout FILE 的 vtable 推回
4. **劫持控制流**：glibc 2.43 tcache poisoning（注意 pointer mangling + tcache key）
   → 目標是 stack return address（沒有 mprotect 不能放 shellcode，GOT 唯讀）
5. **ORW ROP**：`openat(-100, "/home/arbitragedb/flag", 0, 0)` → `read` → `write(1,...)`
   備案：`rt_sigreturn` 有開 → SROP 一次設好所有暫存器

---

## 9. 數量限制與 heap grooming 空間

- **import 記錄上限 16 筆**（`0x46a3`：`cmp $0xf` / `ja`），counter @ `0x1ee64f8`
- **sys_imports 記錄上限 128 筆**（`0x48a8`：`cmp $0x7f`），counter @ `0x1ee5d70`
- 兩者都**只增不減、沒有清除機制** → 一個連線裡最多 16 次有效 IMPORT

含意：
- 16 筆記錄足夠做 heap grooming（每次 IMPORT 可控制 `malloc(min(B+0x18,0x1000))`
  的大小，等於能自由挑 tcache bin）
- 超過 16 筆之後 `sub_4604` 會跳過記錄建立，但**前半的 malloc/memcpy 仍會執行**
  → 溢出原語在用完 16 筆之後**仍然可用**（只是不再新增可讀的記錄）
- 每次 IMPORT 結束都會 `free(p)`（`0x497b`）與 `free(q)`（`0x4889`，B!=C 時）
  → 可自由把 chunk 餵進 tcache / fastbin，這是 tcache poisoning 的基礎

## 10. 目前仍待動態驗證的假設（給 Linux 環境）

| # | 假設 | 為什麼重要 | 怎麼驗 |
|---|---|---|---|
| 1 | B!=C 分支的 `free(q)` 造成的 UAF 能透過 sys_imports 印出 tcache fd/key | 免費 heap leak，整條 exploit 的起點 | 送合法 B!=C 的 IMPORT → `SELECT 1 FROM sys_imports`，看 blob hex |
| 2 | 溢出能覆寫到下一筆記錄的 `+0x50`/`+0x28` 或相鄰 chunk header | 決定能否升級成 arbitrary read | gen_poc.py + gdb 看 heap 佈局 |
| 3 | 能讓某 chunk 進 unsorted bin 讓 fd/bk 指向 main_arena | libc leak | 配置 > 0x410 的 chunk 再 free |
| 4 | glibc 2.43 的 tcache poisoning 是否仍可行（mangling + key 檢查） | 決定劫持手法 | 實機測試 |

**注意**：`alloc = min(B+0x18, 0x1000)`，所以單次最大只能配 0x1000；
要進 unsorted bin（需 > tcache 上限 0x410）是做得到的（B 設 0x400 左右）。
