# Runs every riscv-dv random program in build/dv on the cpu (on a 2 MB board) in lockstep with cpu_model.py, which is itself checked against Spike on the same programs, and each must reach its end and write 1 to tohost.
import os, re, subprocess
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import build, run
from lockstep import RANDOM_SEED, RANDOM_START, RESET_SYNC, Lockstep, hex_file

HERE = Path(__file__).resolve().parent
DV = HERE.parent / "build" / "dv"
SOURCES = [HERE.parent / "design" / "cpu.sv", RESET_SYNC, HERE / "cpu_board.sv"]
NAMES = sorted(p.stem for p in DV.glob("*.bin") if not p.stem.endswith("_spike"))
WORDS = 1 << 19

def tohost(name):
    text = subprocess.run(["riscv64-unknown-elf-nm", DV / f"{name}.elf"], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"^([0-9a-f]+) . tohost$", text, re.M).group(1), 16)

@cocotb.test()
async def lockstep(dut):
    name = os.environ["PROGRAM"]
    lock = Lockstep(dut, (DV / f"{name}.bin").read_bytes(), name, size=4 * WORDS)
    end = tohost(name)
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
        if int(dut.dmem_wstrb.value) and int(dut.dmem_addr.value) == end:
            assert int(dut.dmem_wdata.value) == 1, f"{name} wrote {int(dut.dmem_wdata.value)} to tohost"
            dut._log.info(f"{name}: pass, {lock.retired} instructions in {cycle} cycles")
            return
    raise AssertionError(f"{name}: no write to tohost after 400000 cycles")

@pytest.fixture(scope="module")
def runner():
    return build("cpu_board", SOURCES, __file__, parameters={"WORDS": WORDS}, build_args=RANDOM_START)

def test_found_the_programs():
    assert len(NAMES) >= 30

@pytest.mark.parametrize("name", NAMES)
def test_dv(runner, name):
    os.environ["PROGRAM"] = name
    run("cpu_board", SOURCES, __file__, parameters={"WORDS": WORDS}, build_args=RANDOM_START, plusargs=[f"+program={hex_file(DV / f'{name}.bin')}", *RANDOM_SEED], runner=runner, results=str(DV / f"{name}.result.xml"))
