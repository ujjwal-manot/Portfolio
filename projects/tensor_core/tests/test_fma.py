# Checks the fused multiply-add cell bit for bit against SoftFloat (helpers/fp_ref.py: f32_mulAdd on the widened inputs, and for MX blocks the scaled product in FP64 rounded to odd, then to FP32): every E4M3 and every E5M2 code pair against seven accumulators (both zeros, plus and minus one, the smallest FP32 subnormal, a value near the FP32 maximum, and minus the product so the sum cancels to an exact zero), 100000 random BF16 pairs with random FP32 accumulators, and BF16 products that overflow FP32 or land in its subnormal range, with both block scales at 127 (a scale of one); then every E2M1 pair at block scales chosen to overflow, land subnormal and stay normal, 50000 random MXFP8 cases with random scales in both formats, and a scale of 255 (NaN).
import random
from pathlib import Path
import cocotb
from cocotb.triggers import Timer
from cocotb_run import run
from fp_ref import widen, mul_add, scaled_mul_add, BF16, E4M3, E5M2, E2M1

DESIGN = Path(__file__).resolve().parents[1] / "design"
FIXED = [0x00000000, 0x80000000, 0x3F800000, 0xBF800000, 0x00000001, 0x7F000000]

async def check(dut, fmt, a, b, c, xa=127, xb=127):
    dut.fmt.value, dut.a.value, dut.b.value, dut.c.value, dut.xa.value, dut.xb.value = fmt, a, b, c, xa, xb
    await Timer(1, "ns")
    want = mul_add(widen(fmt, a), widen(fmt, b), c) if (xa, xb) == (127, 127) else scaled_mul_add(fmt, a, b, xa, xb, c)
    got = int(dut.y.value)
    assert got == want, f"format {fmt}: {a:#x} x {b:#x} x 2^({xa} + {xb} - 254) + {c:#010x} gave {got:#010x}, SoftFloat {want:#010x}"

async def every_pair(dut, fmt):
    for a in range(256):
        for b in range(256):
            product = mul_add(widen(fmt, a), widen(fmt, b), 0)
            for c in FIXED + [product ^ 0x80000000]:
                await check(dut, fmt, a, b, c)

@cocotb.test()
async def every_e4m3_pair(dut):
    await every_pair(dut, E4M3)

@cocotb.test()
async def every_e5m2_pair(dut):
    await every_pair(dut, E5M2)

@cocotb.test()
async def random_bf16(dut):
    rng = random.Random(1)
    for _ in range(100000):
        await check(dut, BF16, rng.getrandbits(16), rng.getrandbits(16), rng.getrandbits(32))

@cocotb.test()
async def bf16_range_edges(dut):
    rng = random.Random(2)
    for _ in range(20000):
        big, small = rng.randrange(0x7E00, 0x7F80), rng.randrange(0x0001, 0x0200)
        for a, b in ((big, big), (small, small), (small, rng.randrange(0x3000, 0x4000)), (big | 0x8000, big)):
            await check(dut, BF16, a, b, rng.choice(FIXED + [rng.getrandbits(32)]))

@cocotb.test()
async def every_e2m1_pair_at_edge_scales(dut):
    for xa, xb in ((127, 127), (254, 254), (254, 130), (0, 0), (0, 104), (10, 120), (200, 60)):
        for a in range(16):
            for b in range(16):
                for c in FIXED:
                    await check(dut, E2M1, a, b, c, xa, xb)

@cocotb.test()
async def random_mxfp8(dut):
    rng = random.Random(3)
    for _ in range(50000):
        fmt = rng.choice((E4M3, E5M2))
        await check(dut, fmt, rng.getrandbits(8), rng.getrandbits(8), rng.choice(FIXED + [rng.getrandbits(32)] * 3), rng.randrange(255), rng.randrange(255))

@cocotb.test()
async def nan_scale(dut):
    await check(dut, E4M3, 0x38, 0x38, 0x3F800000, 255, 127)
    await check(dut, E2M1, 0x2, 0x2, 0x3F800000, 127, 255)

def test_fma():
    run("fma", [DESIGN / "fma.sv"], __file__)
