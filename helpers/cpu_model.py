# Reference RV32I model with machine mode (Zicsr, the machine CSRs Spike has with --priv=m and no PMP or triggers, mcountinhibit stopping mcycle and minstret, traps for illegal instructions, ecall, ebreak and misaligned accesses and jump targets, mret, wfi as a hint, and interrupts taken when the caller says the hardware took one): runs one retired instruction per step, carrying on into the handler when an instruction traps, and reports what it retired, for lockstep checks against the cpu and Spike.
M = 0xFFFFFFFF
MSTATUS, MISA, MIE, MTVEC, MSCRATCH, MEPC, MCAUSE, MTVAL, MIP = 0x300, 0x301, 0x304, 0x305, 0x340, 0x341, 0x342, 0x343, 0x344
MCYCLE, MINSTRET, MCYCLEH, MINSTRETH, MCOUNTINHIBIT = 0xB00, 0xB02, 0xB80, 0xB82, 0x320
SHADOW = {0xC00: MCYCLE, 0xC02: MINSTRET, 0xC80: MCYCLEH, 0xC82: MINSTRETH}
MIE_MASK = 0x888


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class Trap(Exception):
    def __init__(self, cause, tval=0):
        self.cause, self.tval = cause, tval & M


class Cpu:
    def __init__(self, image, base=0, size=0x10000, io_read=lambda addr: 0, ids=None):
        self.ram = bytearray(size)
        self.ram[:len(image)] = image
        self.base, self.pc, self.x, self.io_read = base, base, [0] * 32, io_read
        self.csr = {MSTATUS: 0x1800, MISA: 0x40000100, MIE: 0, MTVEC: 0, MSCRATCH: 0, MEPC: 0, MCAUSE: 0, MTVAL: 0, MIP: 0,
                    MCYCLE: 0, MINSTRET: 0, MCYCLEH: 0, MINSTRETH: 0, MCOUNTINHIBIT: 0, 0xF11: 0, 0xF12: 0, 0xF13: 0, 0xF14: 0, 0xF15: 0, **(ids or {})}
        self.count = 0

    def load(self, addr, n):
        off = addr - self.base
        if 0 <= off < len(self.ram):
            return int.from_bytes(self.ram[off:off + n], "little")
        return self.io_read(addr & ~3) >> (8 * (addr & 3)) & ((1 << 8 * n) - 1)

    def counter(self, low, high):
        return self.csr[high] << 32 | self.csr[low]

    def set_counter(self, low, high, value):
        self.csr[low], self.csr[high] = value & M, value >> 32 & M

    def read_csr(self, addr):
        return self.csr[SHADOW.get(addr, addr)]

    def write_csr(self, addr, value):
        if addr >> 10 == 3 or addr not in self.csr:
            raise Trap(2)
        value &= M
        if addr == MSTATUS:
            value = value & 0x88 | 0x1800
        elif addr == MIE:
            value &= MIE_MASK
        elif addr == MCOUNTINHIBIT:
            value &= 5
        elif addr == MTVEC:
            value &= ~2
        elif addr == MEPC:
            value &= ~3
        elif addr == MIP or addr in (MISA, 0xF11, 0xF12, 0xF13, 0xF14, 0xF15):
            return
        self.csr[addr] = value

    def enter(self, cause, tval, epc):
        s = self.csr[MSTATUS]
        self.csr[MSTATUS] = (s & ~0x88) | (s & 8) << 4 | 0x1800
        self.csr[MEPC], self.csr[MCAUSE], self.csr[MTVAL] = epc, cause, tval
        base, vectored = self.csr[MTVEC] & ~3, self.csr[MTVEC] & 1
        self.pc = base + 4 * (cause & 0x7FFFFFFF) if vectored and cause >> 31 else base

    def interrupt(self, cause):
        self.enter(cause | 1 << 31, 0, self.pc)

    def step(self):
        for _ in range(64):
            pc = self.pc
            try:
                result = self.execute(pc)
            except Trap as t:
                self.enter(t.cause, t.tval, pc)
                continue
            for bit, (low, high) in ((1, (MCYCLE, MCYCLEH)), (4, (MINSTRET, MINSTRETH))):
                if not self.wrote_counter.get(low) and not self.csr[MCOUNTINHIBIT] & bit:
                    self.set_counter(low, high, self.counter(low, high) + 1)
            return result
        raise RuntimeError(f"64 traps in a row at {self.pc:#x}")

    def execute(self, pc):
        self.wrote_counter = {}
        i = self.load(pc, 4)
        op, rd, f3, rs1, rs2, f7 = i & 0x7F, i >> 7 & 31, i >> 12 & 7, i >> 15 & 31, i >> 20 & 31, i >> 25
        a, b = self.x[rs1], self.x[rs2]
        imm_i = sx(i >> 20, 12)
        imm_s = sx(f7 << 5 | rd, 12)
        imm_b = sx((i >> 31) << 12 | (i >> 7 & 1) << 11 | (i >> 25 & 0x3F) << 5 | (i >> 8 & 0xF) << 1, 13)
        imm_j = sx((i >> 31) << 20 | (i >> 12 & 0xFF) << 12 | (i >> 20 & 1) << 11 | (i >> 21 & 0x3FF) << 1, 21)
        nxt, value, store = pc + 4, None, None
        if op == 0x37:
            value = i & 0xFFFFF000
        elif op == 0x17:
            value = pc + (i & 0xFFFFF000)
        elif op == 0x6F:
            value, nxt = pc + 4, pc + imm_j
        elif op == 0x67 and f3 == 0:
            value, nxt = pc + 4, (a + imm_i) & ~1
        elif op == 0x63 and f3 not in (2, 3):
            sa, sb = sx(a, 32), sx(b, 32)
            if [a == b, a != b, 0, 0, sa < sb, sa >= sb, a < b, a >= b][f3]:
                nxt = pc + imm_b
        elif op == 0x03 and f3 in (0, 1, 2, 4, 5):
            n, addr = 1 << (f3 & 3), (a + imm_i) & M
            if addr % n:
                raise Trap(4, addr)
            value = self.load(addr, n)
            if f3 < 4:
                value = sx(value, 8 * n)
        elif op == 0x23 and f3 < 3:
            addr, n = (a + imm_s) & M, 1 << f3
            if addr % n:
                raise Trap(6, addr)
            data = b & ((1 << 8 * n) - 1)
            off = addr - self.base
            if 0 <= off < len(self.ram):
                self.ram[off:off + n] = data.to_bytes(n, "little")
            store = (addr, data, n)
        elif op == 0x13 and (f3 not in (1, 5) or f7 in (0, 0x20) and not (f3 == 1 and f7)) or op == 0x33 and (f7 == 0 or f7 == 0x20 and f3 in (0, 5)):
            y = b if op == 0x33 else imm_i & M
            sh, alt = y & 31, f7 == 0x20
            value = [a - y if op == 0x33 and alt else a + y, a << sh, int(sx(a, 32) < sx(y, 32)), int(a < y),
                     a ^ y, sx(a, 32) >> sh if alt else a >> sh, a | y, a & y][f3]
        elif op == 0x0F:
            pass
        elif op == 0x73 and f3 == 0:
            if i == 0x00000073:
                raise Trap(11)
            if i == 0x00100073:
                raise Trap(3, pc)
            if i == 0x30200073:
                s = self.csr[MSTATUS]
                self.csr[MSTATUS] = (s & ~0x88) | (s >> 4 & 8) | 0x80 | 0x1800
                nxt = self.csr[MEPC]
            elif i != 0x10500073:
                raise Trap(2, i)
        elif op == 0x73 and f3 != 4:
            addr, src = i >> 20, rs1 if f3 & 4 else a
            writes = f3 & 3 == 1 or rs1 != 0
            if writes and (addr >> 10 == 3 or addr not in self.csr and addr not in SHADOW):
                raise Trap(2, i)
            if addr not in self.csr and addr not in SHADOW:
                raise Trap(2, i)
            old = self.read_csr(addr)
            if writes:
                new = [0, src, old | src, old & ~src][f3 & 3]
                self.write_csr(addr, new)
                self.wrote_counter = {MCYCLE: addr in (MCYCLE, MCYCLEH), MINSTRET: addr in (MINSTRET, MINSTRETH)}
            value = old
        else:
            raise Trap(2, i)
        if nxt & 3:
            raise Trap(0, nxt)
        if value is None or rd == 0:
            rd, value = 0, 0
        self.x[rd] = value = value & M if rd else 0
        self.pc = nxt & M
        return pc, i, rd, value, store
