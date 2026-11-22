# Runs the filter firmware on the cpu with 4 frames of samples, once as plain RV32I and once built for the custom-0 multiply-accumulate (MAC_FIRMWARE, checked against the model with mac on): outputs must match a Python reference and each frame must fit in 3200 cycles.
import math, os, random, re, subprocess
from pathlib import Path
import cocotb
import pytest
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer
from cocotb_run import build, run
from lockstep import RANDOM_SEED, RANDOM_START, RESET_SYNC, Lockstep, hex_file

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
SOURCES = [HERE.parent / "design" / "cpu.sv", RESET_SYNC, HERE / "cpu_board.sv"]
RESULT, FRAMES, BUDGET = 0x10000100, 4, 3200
NAME = "filter_mac" if os.getenv("MAC_FIRMWARE") else "filter"

def symbols():
    text = subprocess.run(["riscv64-unknown-elf-nm", BUILD / f"{NAME}.elf"], capture_output=True, text=True, check=True).stdout
    return {name: int(addr, 16) for addr, name in re.findall(r"^([0-9a-f]+) \w (\w+)$", text, re.M)}

def samples():
    rng = random.Random(1)
    return [min(255, max(0, round(128 + 100 * math.sin(2 * math.pi * 3 * i / 64) + rng.gauss(0, 6)))) for i in range(64 * FRAMES)]

def reference(codes):
    h, ys = [0] * 8, []
    for c in codes:
        h = [c ^ 0xFF] + h[:7]
        ys.append(sum(k * v for k, v in zip((1, 3, 5, 7, 7, 5, 3, 1), h)) >> 5)
    return ys, [sum(y > 160 for y in ys[f * 64:(f + 1) * 64]) for f in range(FRAMES)]

async def feed(dut, codes, gap):
    rng = random.Random(2)
    i = 0
    while i < len(codes):
        await FallingEdge(dut.clk)
        valid = rng.random() >= gap
        dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = valid, codes[i], i % 64 == 63
        await Timer(1, "ns")
        if valid and dut.s_tready.value:
            i += 1
    await FallingEdge(dut.clk)
    dut.s_tvalid.value = 0

async def filter_run(dut, gap):
    codes, sym = samples(), symbols()
    lock = Lockstep(dut, (BUILD / f"{NAME}.bin").read_bytes(), NAME, mac=NAME == "filter_mac")
    memory = {}
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    cocotb.start_soon(feed(dut, codes, gap))
    for cycle in range(200000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        lock.tick(cycle)
        strobe, addr, data = int(dut.dmem_wstrb.value), int(dut.dmem_addr.value), int(dut.dmem_wdata.value)
        for b in range(4):
            if strobe >> b & 1:
                memory[(addr & ~3) + b] = data >> 8 * b & 0xFF
        if strobe and addr == RESULT:
            break
    else:
        raise AssertionError("firmware never finished")
    word = lambda a: sum(memory.get(a + b, 0) << 8 * b for b in range(4))
    ys, events = reference(codes)
    assert [memory.get(sym["out"] + i) for i in range(64 * FRAMES)] == ys, "filter outputs differ from the reference"
    assert [word(sym["events"] + 4 * f) for f in range(FRAMES)] == events
    frame_cycles = [word(sym["frame_cycles"] + 4 * f) for f in range(FRAMES)]
    dut._log.info(f"{NAME} gap {gap}: events {events}, frame cycles {frame_cycles}, {lock.retired} instructions in {cycle} cycles, IPC {lock.retired / cycle:.3f}")
    return frame_cycles

@cocotb.test()
async def full_speed_stream(dut):
    frame_cycles = await filter_run(dut, 0.0)
    assert max(frame_cycles) <= BUDGET, f"a frame took {max(frame_cycles)} cycles, budget {BUDGET}"

@cocotb.test()
async def stream_with_gaps(dut):
    await filter_run(dut, 0.7)

@pytest.mark.parametrize("name", ["filter", "filter_mac"])
def test_filter(name):
    run("cpu_board", SOURCES, __file__, build_args=RANDOM_START, defines={"MAC_FIRMWARE": 1} if name == "filter_mac" else {}, plusargs=[f"+program={hex_file(BUILD / f'{name}.bin')}", *RANDOM_SEED])
