# Runs every riscv-arch-test rv32i_m/I test on the cpu (on a 2 MB board, since jal-01 alone is 1.7 MB of code) in lockstep with cpu_model.py, then rebuilds its signature (the words from begin_signature to end_signature in the image, overwritten by every store the cpu made) and requires it to equal, word for word, the signature Spike wrote for the same source.
import os, re, subprocess
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import build, run
from lockstep import RANDOM_SEED, RANDOM_START, RESET_SYNC, Lockstep, hex_file

HERE = Path(__file__).resolve().parent
ARCH = HERE.parent / "build" / "arch"
SOURCES = [HERE.parent / "design" / "cpu.sv", RESET_SYNC, HERE / "cpu_board.sv"]
NAMES = sorted(p.stem for p in ARCH.glob("*.bin"))
RESULT, WORDS = 0x10000100, 1 << 19

def signature_range(name):
    text = subprocess.run(["riscv64-unknown-elf-nm", ARCH / f"{name}.elf"], capture_output=True, text=True, check=True).stdout
    sym = {n: int(a, 16) for a, n in re.findall(r"^([0-9a-f]+) \w (\w+)$", text, re.M)}
    return sym["begin_signature"], sym["end_signature"]

@cocotb.test()
async def signature(dut):
    name = os.environ["PROGRAM"]
    image = (ARCH / f"{name}.bin").read_bytes()
    lock = Lockstep(dut, image, name, size=4 * WORDS)
    memory = bytearray(image) + bytearray(4 * WORDS - len(image))
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    for cycle in range(400000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        lock.tick(cycle)
        strobe, addr, data = int(dut.dmem_wstrb.value), int(dut.dmem_addr.value), int(dut.dmem_wdata.value)
        if strobe and addr == RESULT:
            break
        if addr < 4 * WORDS:
            for b in range(4):
                if strobe >> b & 1:
                    memory[(addr & ~3) + b] = data >> 8 * b & 0xFF
    else:
        raise AssertionError(f"{name}: no result after 400000 cycles")
    begin, end = signature_range(name)
    ours = [f"{int.from_bytes(memory[a:a + 4], 'little'):08x}" for a in range(begin, end, 4)]
    spike = (ARCH / f"{name}.sig").read_text().split()
    differ = [i for i, (o, s) in enumerate(zip(ours, spike)) if o != s]
    assert len(ours) == len(spike) and not differ, f"{name}: signature differs from Spike at words {differ[:8]} of {len(spike)}"
    dut._log.info(f"{name}: signature of {len(ours)} words matches Spike, {lock.retired} instructions in {cycle} cycles")

@pytest.fixture(scope="module")
def runner():
    return build("cpu_board", SOURCES, __file__, parameters={"WORDS": WORDS}, build_args=RANDOM_START)

def test_found_the_tests():
    assert len(NAMES) == 39

@pytest.mark.parametrize("name", NAMES)
def test_arch(runner, name):
    os.environ["PROGRAM"] = name
    run("cpu_board", SOURCES, __file__, parameters={"WORDS": WORDS}, build_args=RANDOM_START, plusargs=[f"+program={hex_file(ARCH / f'{name}.bin')}", *RANDOM_SEED], runner=runner, results=str(ARCH / f"{name}.result.xml"))
