# Checks the fused multiply-add cell bit for bit against SoftFloat's f32_mulAdd on the widened inputs (helpers/fp_ref.py): every E4M3 and every E5M2 code pair against seven accumulators (both zeros, plus and minus one, the smallest FP32 subnormal, a value near the FP32 maximum, and minus the product so the sum cancels to an exact zero), 100000 random BF16 pairs with random FP32 accumulators, and BF16 products that overflow FP32 or land in its subnormal range.
import random
from pathlib import Path
import cocotb
from cocotb.triggers import Timer
from cocotb_run import run
from fp_ref import widen, mul_add, BF16, E4M3, E5M2

DESIGN = Path(__file__).resolve().parents[1] / "design"
FIXED = [0x00000000, 0x80000000, 0x3F800000, 0xBF800000, 0x00000001, 0x7F000000]

async def check(dut, fmt, a, b, c):
    dut.fmt.value, dut.a.value, dut.b.value, dut.c.value = fmt, a, b, c
    await Timer(1, "ns")
    want, got = mul_add(widen(fmt, a), widen(fmt, b), c), int(dut.y.value)
    assert got == want, f"format {fmt}: {a:#x} x {b:#x} + {c:#010x} gave {got:#010x}, SoftFloat {want:#010x}"

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

def test_fma():
    run("fma", [DESIGN / "fma.sv"], __file__)
