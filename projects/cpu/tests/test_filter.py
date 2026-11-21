# Runs the filter firmware on the cpu with 4 frames of samples: outputs must match a Python reference and each frame must fit in 3200 cycles.
import math, random, re, subprocess
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge, Timer
from cocotb_run import build, run
from cpu_model import Cpu

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
SOURCES = [HERE.parent / "design" / "cpu.sv", HERE / "cpu_board.sv"]
RESULT, FRAMES, BUDGET = 0x10000100, 4, 3200

def symbols():
    text = subprocess.run(["riscv64-unknown-elf-nm", BUILD / "filter.elf"], capture_output=True, text=True, check=True).stdout
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
    model = Cpu((BUILD / "filter.bin").read_bytes(), io_read=lambda addr: int(dut.retire_rd_data.value))
    memory = {}
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    cocotb.start_soon(feed(dut, codes, gap))
    retired = 0
    for cycle in range(200000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.retire_valid.value:
            got = tuple(int(s.value) for s in (dut.retire_pc, dut.retire_instr, dut.retire_rd, dut.retire_rd_data))
            want = model.step()[:4]
            assert got == want, f"instruction {retired}: cpu {[hex(x) for x in got]}, model {[hex(x) for x in want]}"
            retired += 1
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
    dut._log.info(f"gap {gap}: events {events}, frame cycles {frame_cycles}, {retired} instructions in {cycle} cycles, IPC {retired / cycle:.3f}")
    return frame_cycles

@cocotb.test()
async def full_speed_stream(dut):
    frame_cycles = await filter_run(dut, 0.0)
    assert max(frame_cycles) <= BUDGET, f"a frame took {max(frame_cycles)} cycles, budget {BUDGET}"

@cocotb.test()
async def stream_with_gaps(dut):
    await filter_run(dut, 0.7)

def test_filter():
    run("cpu_board", SOURCES, __file__, plusargs=[f"+program={hex_file()}"])

def hex_file():
    image = (BUILD / "filter.bin").read_bytes()
    image += bytes(-len(image) % 4)
    path = BUILD / "filter.hex"
    path.write_text("\n".join(f"{int.from_bytes(image[i:i + 4], 'little'):08x}" for i in range(0, len(image), 4)) + "\n")
    return path
