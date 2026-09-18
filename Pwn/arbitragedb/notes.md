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

---

## 11. 控制流劫持目標分析（靜態，回應 tcache alignment 提醒）

### 11.1 先確認哪些東西是唯讀的

```
GNU_RELRO  0x128cb8 .. 0x129000   ← 執行期唯讀
  [21] .init_array  0x128cb8      ✗ 在 RELRO 內，不能寫
  [22] .fini_array  0x128cc0      ✗ 在 RELRO 內，不能寫
  [24] .got         0x128eb8      ✗ 在 RELRO 內，BIND_NOW → 全部唯讀
  [25] .data        0x129000      ✓ 可寫（只有 0x10 bytes）
  [26] .bss         0x129020..    ✓ 可寫（約 31MB）
```

**結論：GOT / init_array / fini_array 全部打不了**（Full RELRO 名副其實）。
全域也沒有任何存在可寫記憶體的 function pointer
（掃過所有 `callq *` / `jmpq *`，除了 PLT 就只有 `0x1014` 的 `callq *%rax`，
那是 `_init` 裡的 `__gmon_start__`，執行期碰不到）。

### 11.2 Canary 狀況

掃過所有 frame >= 0x100 的函式，**全部都有 canary**（都有 `mov %fs:0x28,%rax`）：
`sub_6a03`(main, 0x1000) / `sub_41a9`(FILECHECK, 0x1000) / `sub_2e76`(0x1000) /
`sub_54ce`(0x340) / `sub_62b8`(0x340) / `sub_1cd1`(0x520) / 各 SELECT handler(0x440)…

→ 想蓋 return address 就**必須先 leak canary**。
   但我們有 arbitrary read（第 8 節），可以直接讀 TLS 的 canary
   （`fs:0x28`，位於 TCB；heap leak → 推 TLS 位址 → 讀出來），所以這條路仍然通。

### 11.3 ★ 更好的目標：stdout / stdin FILE* 在 .data，**不在 RELRO 內**

```
0x129020  stdout  FILE*   ← 可寫
0x129030  stdin   FILE*   ← 可寫
```

程式大量使用 `printf` / `puts` / `fgets` / `fflush`（`sub_6b93` 每跑完一條指令就
`fflush`），且 `main` 開頭對兩者呼叫 `setvbuf`（`0x6a50`/`0x6a6e`）。

→ **FSOP（File Stream Oriented Programming）是比蓋 return address 更乾淨的路線**：
   用 overflow / tcache poisoning 把 `0x129020` 改成指向偽造的 FILE 結構
   （偽造結構可以放在 heap 上，位址由 UAF leak 得知），
   下一次 `fflush`/`printf` 就會走我們控制的 vtable。
   **完全不需要 canary leak**。

⚠️ 但 glibc 2.43 對 FILE vtable 有 `_IO_validate_vtable` 檢查（vtable 必須落在
`__io_vtables` 區段內），所以要用 `_IO_wfile_jumps` / `_IO_str_jumps` 那類
合法 vtable 搭配 `_wide_data` 的手法，而不是隨便指一個位址。
這點需要在實機上對著這份 libc 2.43 確認可用的 gadget。

### 11.4 tcache poisoning 的對齊限制（planner 提醒，已確認需納入）

glibc 2.14+ 的 tcache：
- `e->next` 有 **pointer mangling**：`next_mangled = (chunk_addr >> 12) ^ next`
  → 要偽造 next 必須先知道 chunk 位址（heap leak，第 8.4 節可拿到）
- 有 **`e->key` double-free 檢查**
- **`tcache_get` 會檢查對齊**：取出的 chunk 必須 16-byte aligned，
  否則 `malloc(): unaligned tcache chunk detected` 直接 abort

→ 所以 tcache poisoning 的目標位址**必須 16-byte 對齊**。
  `0x129020`(stdout) 與 `0x129030`(stdin) **都是 16-byte 對齊的**，✓ 可作為目標。
  （`0x129020 % 0x10 == 0`，`0x129030 % 0x10 == 0`）
  要蓋 stack return address 的話也要挑對齊的落點，通常配合「蓋一個 16-byte 對齊的
  區域、讓 ret addr 落在其中」來處理。

### 11.5 修正後的建議路線（優先序）

1. **UAF heap leak**（第 8.4 節）→ heap base
2. **libc leak**：B≈0x400 配一個 > 0x410 的 chunk → free 進 unsorted bin
   → fd/bk 指向 main_arena → 用 UAF/arbitrary read 印出來 → libc base
3. **劫持**：二選一
   - **(推薦) FSOP**：tcache poisoning 目標 `0x129020`(stdout)，16-byte 對齊 ✓，
     改成指向 heap 上偽造的 FILE → 下次 `fflush` 觸發
   - **(備案) 蓋 return address**：需額外用 arbitrary read 撈 canary
4. **ORW ROP / SROP**：`openat(-100,"/home/arbitragedb/flag",0,0)` → `read` → `write(1)`
   （`rt_sigreturn` 有開，SROP 可一次設好暫存器，在 gadget 不足時特別好用）

---

## 12. ORW chain 已建好（`rop.py`），關鍵發現：**libc 沒有 `pop rdx`**

用題目附的 libc.so.6 掃 `.text`（vaddr `0x287c0`, size `0x197159`）：

| gadget | offset | 狀況 |
|---|---|---|
| `syscall; ret` | `0x0a0be6`, `0x0a0c05`, `0xaca80` | ✓ |
| `pop rdi; ret` | `0x11bc7a` | ✓ |
| `pop rsi; ret` | `0x05c2e7` | ✓ |
| `pop rax; ret` | `0x0e5dc7` | ✓ |
| `ret` | `0x0289fe` | ✓ |
| `mov rdx,rax; ret` | `0x146257` | ✓ |
| **`pop rdx; ret`** | — | ❌ **完全找不到** |
| `pop rdx; pop rbx/rsi/rcx/r12; ret` | — | ❌ 也都沒有 |

**沒有 `pop rdx` ⇒ `read`/`write` 的第三個參數（長度）用純 ROP 很難設。**

→ 所以 **主線改走 SROP**（`rt_sigreturn` = syscall 15，**已被 seccomp 允許**）：
   一個 sigframe 就把 rax/rdi/rsi/rdx/rip/rsp 全部一次設好，完全不需要湊 gadget。
   這也是為什麼出題者刻意在 seccomp 裡留 `rt_sigreturn` —— 應該就是預期解法。

### 12.1 SROP frame 佈局（已在 `rop.py` 裡用 assert 自我驗證）

rt_sigreturn 時 `rsp` 必須指向 **ucontext 起點**：

```
+0x00 uc_flags   +0x08 uc_link   +0x10 uc_stack(24)
+0x28 起是 sigcontext：
   +0x28 r8   +0x30 r9   +0x38 r10  +0x40 r11  +0x48 r12  +0x50 r13
   +0x58 r14  +0x60 r15  +0x68 rdi  +0x70 rsi  +0x78 rbp  +0x80 rbx
   +0x88 rdx  +0x90 rax  +0x98 rcx  +0xa0 rsp  +0xa8 rip  +0xb0 eflags
   +0xb8 csgsfs(=0x33)   ...   +0xe0 fpstate(必須 0)
有效長度 = 0xe8
```

⚠️ 我第一版寫成 0x100 是錯的（多塞了 __reserved 尾巴），
`rop.py` 現在有 `assert SIGFRAME_OFF["rip"] == 0xa8` 等檢查防止再犯。

### 12.2 chain 大小

- 單個 SROP frame = `pop rax;15`(16) + `syscall`(8) + sigframe(0xe8) = **0x100**
- ORW 三步（openat → read → write）= **0x300 bytes**
- heap overflow 可寫約 0x1fe8 → **空間綽綽有餘** ✓

### 12.3 libc 函式 offset（dynsym 實測值）

```
openat  0x127c50    read  0x128310    write  0x128dd0
syscall 0x134c70    environ 0x219de8   ← environ 可拿 stack leak
_IO_file_jumps  0x211030      _IO_wfile_jumps  0x211228
```

`__io_vtables` 合法區間約 `0x211030`–`0x2116c0`（planner 從 stride 推導，
`_IO_file_jumps` / `_IO_wfile_jumps` 是 dynsym 實測值可直接用）
→ **FSOP 成立**，`_IO_wfile_jumps` 可安全指過去。

### 12.4 還需要的一塊：把 chain 放到哪、怎麼轉進去

SROP 需要 `rsp` 指到我們的 frame。兩個候選：
1. FSOP 觸發時若能控到 `rsp`（某些 `_IO_wfile_jumps` 手法可做 stack pivot）
2. 或先用 `environ`（`0x219de8`）arbitrary read 拿 stack 位址，
   再用 overflow 蓋 return address（但需 canary leak）

→ 這一步**必須動態驗證**，是目前唯一還沒收斂的環節。

---

## 13. ★ Stack pivot 已解決（靜態）：`setcontext+0x3d` 用 **rdx**，且與 SROP 共用同一套偏移

### 13.1 FSOP pivot 路徑上的符號（dynsym 實測值）

```
setcontext          0x04be80      swapcontext   0x05bea0    makecontext 0x04a0c0
_IO_wdoallocbuf     0x092020      _IO_wsetb            0x0919c0
_IO_switch_to_wget_mode 0x092190  _IO_wfile_underflow  0x0938c0
_IO_wfile_overflow  0x094110      _IO_wfile_xsputn     0x094e40
_IO_wfile_seekoff   0x094550      _IO_wfile_sync       0x0943b0
_IO_list_all        0x213480      _IO_2_1_stdout_      0x213580
_IO_2_1_stdin_      0x2128e0      _IO_wfile_jumps      0x211228
_IO_file_jumps      0x211030
```

### 13.2 setcontext 的 pivot gadget（已逐 byte 驗證）

`setcontext` 前段是 `rt_sigprocmask`，真正有用的入口在 **`setcontext+0x3d` = `0x4bebd`**：

```asm
0x4bebd:  48 8b a2 a0 00 00 00   mov rsp,[rdx+0xa0]     ← pivot！
0x4bec4:  48 8b 9a 80 00 00 00   mov rbx,[rdx+0x80]
0x4becb:  48 8b 6a 78            mov rbp,[rdx+0x78]
0x4becf:  4c 8b 62 48            mov r12,[rdx+0x48]
0x4bed3:  4c 8b 6a 50            mov r13,[rdx+0x50]
0x4bed7:  4c 8b 72 58            mov r14,[rdx+0x58]
0x4bedb:  4c 8b 7a 60            mov r15,[rdx+0x60]
   ...（FPU / shadow-stack 檢查）...
0x4bf84:  4c 8b 92 a8 00 00 00   mov r10,[rdx+0xa8]     ← 目標 rip
0x4bf8a:  48 8b 92 88 00 00 00   mov rdx,[rdx+0x88]
0x4bfa0:  41 52                  push r10
0x4bfa2:  c3                     ret                     ← 轉移控制
   後段還有：mov rsi,[rdx+0x70]; mov rdi,[rdx+0x68]; mov rcx,[rdx+0x98];
             mov r8,[rdx+0x28]; mov r9,[rdx+0x30]
```

### 13.3 ★ 這個發現為什麼重要

**(1) 是 `rdx` 版本，不是舊版的 `rdi` 版本。**
glibc 2.29 之後 setcontext 改讀 `rdx`。所以 FSOP 觸發時**必須讓 `rdx` 指向偽造的 ucontext**，
不是 `rdi`。這點如果搞錯整條 exploit 會直接死掉，而這是很常見的踩雷點。
→ `_IO_wfile_*` 那條路線剛好會把 `_wide_data`（我們可控的指標）帶進 `rdx`，
  這正是 FSOP + setcontext 常見組合可行的原因。**待動態確認 rdx 實際落點。**

**(2) 偏移跟 SROP 的 sigframe 完全一致。**

| 欄位 | SROP sigframe | setcontext 讀的 ucontext |
|---|---|---|
| rsp | `+0xa0` | `+0xa0` ✓ |
| rip | `+0xa8` | `+0xa8` ✓ |
| rdi | `+0x68` | `+0x68` ✓ |
| rsi | `+0x70` | `+0x70` ✓ |
| rdx | `+0x88` | `+0x88` ✓ |

→ **同一份偽造結構可以同時餵給 SROP 和 setcontext**，不用寫兩套。
  `rop.py` 的 `sigframe()` 直接就能當 setcontext 的 ucontext 用。

### 13.4 更新後的完整路線

```
1. UAF leak       合法 B!=C 的 IMPORT → SELECT sys_imports → heap base        [待 Q1]
2. libc leak      B≈0x400 → unsorted bin → fd/bk 指向 main_arena → 讀出       [待 Q1]
3. 寫 payload     用 overflow 把「偽造 FILE + ucontext + ORW chain」寫進 heap
4. 劫持           tcache poisoning 改 0x129020(stdout) → 偽造 FILE
                  vtable 指 _IO_wfile_jumps(0x211228)，讓它走到 setcontext+0x3d
5. pivot          setcontext 從 rdx 讀 ucontext → rsp 落到我們的 SROP chain
6. ORW            openat(-100,"/home/arbitragedb/flag",0,0) → read → write(1)
                  （沒有 pop rdx，全部用 SROP 設暫存器）
```

**唯一還需要動態確認的**：步驟 4→5 之間 `rdx` 實際會指到哪，
以及 glibc 2.43 的 `_IO_validate_vtable` 在這條路徑上的確切檢查點。
