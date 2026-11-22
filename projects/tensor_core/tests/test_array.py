# Runs GEMMs on the 8x8 array in both dataflows (output stationary: WS=0, weight stationary: WS=1) and checks every C element bit for bit against the same FMA chain done in order k = 0 to K-1 from C's starting value with SoftFloat (helpers/fp_ref.py), for BF16, E4M3, E5M2 and MX blocks of E4M3, E5M2 and E2M1 with random shared exponents, and writes the cycles each GEMM took from start to idle to the log.
import os, random
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, ReadOnly
from cocotb_run import run
from fp_ref import widen, mul_add, scaled_mul_add, BF16, E4M3, E5M2, E2M1

DESIGN = Path(__file__).resolve().parents[1] / "design"
MAXM, MAXK, MAXN = 32, 64, 32
A, B, C, XA, XB = range(5)
CASES = [(BF16, 0, 16, 32, 16), (E4M3, 0, 8, 64, 16), (E5M2, 0, 16, 16, 8), (E4M3, 1, 16, 64, 8), (E5M2, 1, 8, 32, 16), (E2M1, 1, 16, 64, 16)]

def element(rng, fmt):
    if fmt == BF16:
        return rng.choice([rng.getrandbits(16), 0x3F80 ^ rng.getrandbits(8), rng.randrange(0x3800, 0x4800) | rng.getrandbits(1) << 15])
    return rng.getrandbits(4 if fmt == E2M1 else 8)

def reference(fmt, mx, a, b, xa, xb, c, m, k, n):
    out = [row[:] for row in c]
    for i in range(m):
        for j in range(n):
            acc = c[i][j]
            for kk in range(k):
                if mx:
                    acc = scaled_mul_add(fmt, a[i][kk], b[kk][j], xa[i][kk // 32], xb[kk // 32][j], acc)
                else:
                    acc = mul_add(widen(fmt, a[i][kk]), widen(fmt, b[kk][j]), acc)
            out[i][j] = acc
    return out

async def write(dut, sel, addr, data):
    await FallingEdge(dut.clk)
    dut.we.value, dut.sel.value, dut.addr.value, dut.wdata.value = 1, sel, addr, data
    await FallingEdge(dut.clk)
    dut.we.value = 0

@cocotb.test()
async def gemms(dut):
    rng = random.Random(int(os.environ["SEED"]))
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.we.value = dut.start.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    for fmt, mx, m, k, n in CASES:
        a = [[element(rng, fmt) for _ in range(k)] for _ in range(m)]
        b = [[element(rng, fmt) for _ in range(n)] for _ in range(k)]
        c = [[rng.choice([0, 0x3F800000, rng.getrandbits(32) & 0xBFFFFFFF]) for _ in range(n)] for _ in range(m)]
        xa = [[rng.randrange(110, 140) for _ in range(MAXK // 32)] for _ in range(m)]
        xb = [[rng.randrange(110, 140) for _ in range(n)] for _ in range(MAXK // 32)]
        for i in range(m):
            for kk in range(k):
                await write(dut, A, i * MAXK + kk, a[i][kk])
            for j in range(n):
                await write(dut, C, i * MAXN + j, c[i][j])
            for kb in range(MAXK // 32):
                await write(dut, XA, i * (MAXK // 32) + kb, xa[i][kb])
        for kk in range(k):
            for j in range(n):
                await write(dut, B, kk * MAXN + j, b[kk][j])
        for kb in range(MAXK // 32):
            for j in range(n):
                await write(dut, XB, kb * MAXN + j, xb[kb][j])
        await FallingEdge(dut.clk)
        dut.fmt.value, dut.mx.value, dut.m.value, dut.k.value, dut.n.value, dut.start.value = fmt, mx, m, k, n, 1
        await FallingEdge(dut.clk)
        dut.start.value, cycles = 0, 1
        while True:
            await RisingEdge(dut.clk)
            await ReadOnly()
            if not dut.busy.value:
                break
            cycles += 1
        want = reference(fmt, mx, a, b, xa, xb, c, m, k, n)
        await FallingEdge(dut.clk)
        for i in range(m):
            for j in range(n):
                dut.sel.value, dut.addr.value = C, i * MAXN + j
                await ReadOnly()
                got = int(dut.rdata.value)
                assert got == want[i][j], f"format {fmt} mx {mx} {m}x{k}x{n}: C[{i}][{j}] {got:#010x}, SoftFloat chain {want[i][j]:#010x}"
                await FallingEdge(dut.clk)
        dut._log.info(f"WS={os.environ['WS']} format {fmt} mx {mx} M {m} K {k} N {n}: {cycles} cycles")

def test_output_stationary():
    os.environ["WS"], os.environ["SEED"] = "0", "11"
    run("tensor_core", [DESIGN / "fma.sv", DESIGN / "tensor_core.sv"], __file__, parameters={"WS": 0, "MAXM": MAXM, "MAXK": MAXK, "MAXN": MAXN})

def test_weight_stationary():
    os.environ["WS"], os.environ["SEED"] = "1", "12"
    run("tensor_core", [DESIGN / "fma.sv", DESIGN / "tensor_core.sv"], __file__, parameters={"WS": 1, "MAXM": MAXM, "MAXK": MAXK, "MAXN": MAXN})
