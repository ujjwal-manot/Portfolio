# Reference RV32I model: runs one instruction per step and reports what it retired, for lockstep checks against the cpu.
M = 0xFFFFFFFF


def sx(v, bits):
    v &= (1 << bits) - 1
    return v - (1 << bits) if v >> (bits - 1) else v


class Cpu:
    def __init__(self, image, base=0, size=0x10000, io_read=lambda addr: 0):
        self.ram = bytearray(size)
        self.ram[:len(image)] = image
        self.base, self.pc, self.x, self.io_read = base, base, [0] * 32, io_read

    def load(self, addr, n):
        off = addr - self.base
        if 0 <= off < len(self.ram):
            return int.from_bytes(self.ram[off:off + n], "little")
        return self.io_read(addr & ~3) >> (8 * (addr & 3)) & ((1 << 8 * n) - 1)

    def step(self):
        pc, i = self.pc, self.load(self.pc, 4)
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
        elif op == 0x67:
            value, nxt = pc + 4, (a + imm_i) & ~1
        elif op == 0x63:
            sa, sb = sx(a, 32), sx(b, 32)
            if [a == b, a != b, 0, 0, sa < sb, sa >= sb, a < b, a >= b][f3]:
                nxt = pc + imm_b
        elif op == 0x03:
            n = 1 << (f3 & 3)
            value = self.load((a + imm_i) & M, n)
            if f3 < 4:
                value = sx(value, 8 * n)
        elif op == 0x23:
            addr, n = (a + imm_s) & M, 1 << f3
            data = b & ((1 << 8 * n) - 1)
            off = addr - self.base
            if 0 <= off < len(self.ram):
                self.ram[off:off + n] = data.to_bytes(n, "little")
            store = (addr, data, n)
        elif op in (0x13, 0x33):
            y = b if op == 0x33 else imm_i & M
            sh, alt = y & 31, f7 == 0x20
            value = [a - y if op == 0x33 and alt else a + y, a << sh, int(sx(a, 32) < sx(y, 32)), int(a < y),
                     a ^ y, sx(a, 32) >> sh if alt else a >> sh, a | y, a & y][f3]
        elif op != 0x0F:
            raise ValueError(f"unknown instruction {i:#010x} at {pc:#x}")
        if value is None or rd == 0:
            rd, value = 0, 0
        self.x[rd] = value = value & M if rd else 0
        self.pc = nxt & M
        return pc, i, rd, value, store
