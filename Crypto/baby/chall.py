from hashlib import sha256
from secrets import randbelow, token_bytes

from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from Crypto.Util.number import getPrime, GCD


def rsa_gen():
    while True:
        p = getPrime(1024)
        q = getPrime(1024)
        if p == q:
            continue
        phi = (p - 1) * (q - 1)
        e1 = 65537
        e2 = 77417
        e3 = 54139
        if GCD(e1, phi) == 1 and GCD(e2, phi) == 1 and GCD(e3, phi) == 1:
            break
    return p * q, e1, e2, e3


def key_gen():
    lo = 1 << 24
    a = lo + randbelow(lo)
    b = lo + randbelow(lo)

    return max(a, b), min(a, b)


def nonce_gen(n):
    while True:
        nonce = getPrime(n.bit_length() - 1)
        if GCD(nonce, n) == 1:
            break
    return nonce


def generate_challenge(flag, n, e1, e2, e3):
    a, b = key_gen()
    r = nonce_gen(n)
    s = nonce_gen(n)

    m1 = a * pow(r, 137, n) * pow(s, 73331, n) % n
    m2 = b * pow(r, 1337, n) * pow(s, 7331, n) % n
    m3 = 1 * pow(r, 13337, n) * pow(s, 731, n) % n
    c1 = pow(m1, e1, n)
    c2 = pow(m2, e2, n)
    c3 = pow(m3, e3, n)

    k = a*b
    key = sha256(str(k).encode("ascii")).digest()
    iv = token_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv=iv)
    ct = cipher.encrypt(pad(flag, AES.block_size))

    print(f"Generated challenge with a={a}, b={b}")
    return c1, c2, c3, iv.hex(), ct.hex()


def main():
    from secret import FLAG

    n, e1, e2, e3 = rsa_gen()
    c1, c2, c3, iv, ct = generate_challenge(FLAG, n, e1, e2, e3)

    e = (e1, e2, e3)
    c = (c1, c2, c3)
    with open("output.txt", "w") as f:
        f.write(f"{n=}\n")
        f.write(f"{e=}\n")
        f.write(f"{c=}\n")
        f.write(f"{iv=}\n")
        f.write(f"{ct=}\n")


if __name__ == "__main__":
    main()
