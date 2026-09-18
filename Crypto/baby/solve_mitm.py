#!/usr/bin/env python3
"""
AEGIS 2026 / Crypto / baby  -- meet-in-the-middle recovery of a,b

Algebra (verified against a small simulation):
  m1 = a * r^137   * s^73331
  m2 = b * r^1337  * s^7331
  m3 = 1 * r^13337 * s^731
  c_i = m_i ^ e_i mod n     e=(65537, 77417, 54139)

Let A=[137*e1,1337*e2,13337*e3], B=[73331*e1,7331*e2,731*e3].
The integer kernel (k1,k2,k3) of [A;B] kills both r and s, so

  R := c1^k1 * c2^k2 * c3^k3  ==  a^ea * b^eb   (mod n)
  with ea = e1*k1 = -44313921371852279837
       eb = e2*k2 = +447695944096188393529

a,b are each in [2^24, 2^25).  Meet in the middle:
  a^ea * b^eb = R   <=>   a^(-ea_abs)  = R * b^(-eb)
  i.e.  pow(a, |ea|, n)^-1 * pow(b, eb, n) == R
  =>    pow(b, eb, n) == R * pow(a, |ea|, n)   (mod n)

Build table of pow(a,|ea|,n) -> a for all a, then scan b.
Store only the low 64 bits of each residue as the dict key (collisions are
re-verified exactly).

Finally key = sha256(str(a*b)).digest(), AES-CBC decrypt.
"""
import sys, time, pickle
from math import gcd
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent

def load():
    d = {}
    for line in (HERE / "output.txt").read_text().strip().split("\n"):
        k, v = line.split("=", 1)
        d[k] = v
    n = int(d["n"]); e = eval(d["e"]); c = eval(d["c"])
    return n, e, c, bytes.fromhex(eval(d["iv"])), bytes.fromhex(eval(d["ct"]))

def kernel(e1, e2, e3):
    A = [137 * e1, 1337 * e2, 13337 * e3]
    B = [73331 * e1, 7331 * e2, 731 * e3]
    x1 = A[1] * B[2] - A[2] * B[1]
    x2 = -(A[0] * B[2] - A[2] * B[0])
    x3 = A[0] * B[1] - A[1] * B[0]
    g = gcd(gcd(abs(x1), abs(x2)), abs(x3))
    return x1 // g, x2 // g, x3 // g

def pw(base, exp, m):
    return pow(base, exp, m) if exp >= 0 else pow(pow(base, -exp, m), -1, m)

LO, HI = 1 << 24, 1 << 25
MASK = (1 << 64) - 1

def main():
    n, (e1, e2, e3), (c1, c2, c3), iv, ct = load()
    k1, k2, k3 = kernel(e1, e2, e3)
    ea, eb = e1 * k1, e2 * k2
    R = pw(c1, k1, n) * pw(c2, k2, n) % n * pw(c3, k3, n) % n
    abs_ea = abs(ea)            # ea is negative
    assert ea < 0 and eb > 0

    # ---- side 1: table of a^|ea| -> a
    t0 = time.time()
    tab = {}
    for a in range(LO, HI):
        tab[pow(a, abs_ea, n) & MASK] = a
        if (a - LO) % (1 << 20) == 0:
            print(f"[a] {a-LO}/{HI-LO}  {time.time()-t0:.0f}s", flush=True)
    print(f"[a] table built: {len(tab)} entries, {time.time()-t0:.0f}s", flush=True)

    # ---- side 2: scan b, need pow(b,eb,n) == R * pow(a,|ea|,n)
    # rearranged: pow(b,eb,n) * R^-1 == pow(a,|ea|,n)
    Rinv = pow(R, -1, n)
    t0 = time.time()
    for b in range(LO, HI):
        want = pow(b, eb, n) * Rinv % n
        a = tab.get(want & MASK)
        if a is not None and pow(a, abs_ea, n) == want:
            print(f"FOUND a={a} b={b}", flush=True)
            decrypt(a, b, iv, ct)
            return
        if (b - LO) % (1 << 20) == 0:
            print(f"[b] {b-LO}/{HI-LO}  {time.time()-t0:.0f}s", flush=True)
    print("no solution found")

def decrypt(a, b, iv, ct):
    from Crypto.Cipher import AES
    key = sha256(str(a * b).encode("ascii")).digest()
    pt = AES.new(key, AES.MODE_CBC, iv=iv).decrypt(ct)
    print("PLAINTEXT:", pt)

if __name__ == "__main__":
    main()
