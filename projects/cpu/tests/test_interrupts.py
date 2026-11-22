# Runs firmware/interrupts.S on the cpu in lockstep with cpu_model.py while the timer fires every 300 cycles and 16 stream samples arrive after random gaps, each held until it is taken: the firmware must sum every sample, exactly one external interrupt must be taken per sample and at least 8 timer interrupts, at least twice with both pending, and the core must spend cycles asleep in wfi; a second run starts mtime 2000 cycles short of 2^32, so the timer works across the carry into its high word.
import random
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer
from cocotb_run import run
from lockstep import RANDOM_SEED, RANDOM_START, RESET_SYNC, Lockstep, hex_file

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
SOURCES = [HERE.parent / "design" / "cpu.sv", RESET_SYNC, HERE / "cpu_board.sv"]
RESULT, SUM, SAMPLES = 0x10000100, 0x10000104, 16

async def feed(dut, codes):
    rng = random.Random(3)
    for code in codes:
        for _ in range(rng.randrange(50, 400)):
            await FallingEdge(dut.clk)
        dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = 1, code, 0
        while True:
            await Timer(1, "ns")
            ready = dut.s_tready.value
            await FallingEdge(dut.clk)
            if ready:
                break
        dut.s_tvalid.value = 0

async def workout(dut, mtime0):
    rng = random.Random(4)
    codes = [rng.randrange(256) for _ in range(SAMPLES)]
    lock = Lockstep(dut, (BUILD / "interrupts.bin").read_bytes(), "interrupts", mtime0)
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    dut.core.mtime.value = mtime0
    cocotb.start_soon(feed(dut, codes))
    asleep, total = 0, None
    for cycle in range(100000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        lock.tick(cycle)
        asleep += int(dut.sleep.value)
        if int(dut.dmem_wstrb.value):
            addr, data = int(dut.dmem_addr.value), int(dut.dmem_wdata.value)
            total = data if addr == SUM else total
            if addr == RESULT:
                assert data == 1, f"firmware reports failure {data}"
                break
    else:
        raise AssertionError("firmware never finished")
    dut._log.info(f"{lock.retired} instructions in {cycle} cycles, {asleep} asleep, interrupts taken {lock.taken}, {lock.both} taken with both pending")
    assert total == sum(codes), f"firmware summed {total}, samples sum to {sum(codes)}"
    assert lock.taken[11] == SAMPLES and lock.taken[7] >= 8, f"interrupts taken {lock.taken}"
    assert lock.both >= 2, "the timer and the stream were pending together fewer than twice, so priority went barely tested"
    assert asleep > 0, "the core never slept in wfi"

@cocotb.test()
async def interrupts(dut):
    await workout(dut, 0)

@cocotb.test()
async def timer_wraps(dut):
    await workout(dut, (1 << 32) - 2000)

def test_interrupts():
    run("cpu_board", SOURCES, __file__, build_args=RANDOM_START, plusargs=[f"+program={hex_file(BUILD / 'interrupts.bin')}", *RANDOM_SEED])
