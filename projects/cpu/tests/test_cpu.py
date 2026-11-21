# Runs every rv32ui test on the cpu in lockstep with cpu_model.py: each retired instruction must match, and the test must report pass.
import os
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import build, run
from cpu_model import Cpu

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
SOURCES = [HERE.parent / "design" / "cpu.sv", HERE / "cpu_board.sv"]
NAMES = sorted(p.stem for p in (BUILD / "rv32ui").glob("*.bin") if not p.stem.endswith("_spike"))
RESULT = 0x10000100

def hex_file(name):
    image = (BUILD / "rv32ui" / f"{name}.bin").read_bytes()
    path = BUILD / "rv32ui" / f"{name}.hex"
    image += bytes(-len(image) % 4)
    path.write_text("\n".join(f"{int.from_bytes(image[i:i + 4], 'little'):08x}" for i in range(0, len(image), 4)) + "\n")
    return path

@cocotb.test()
async def lockstep(dut):
    name = os.environ["PROGRAM"]
    model = Cpu((BUILD / "rv32ui" / f"{name}.bin").read_bytes())
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    retired = 0
    for cycle in range(100000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.retire_valid.value:
            got = tuple(int(s.value) for s in (dut.retire_pc, dut.retire_instr, dut.retire_rd, dut.retire_rd_data))
            want = model.step()[:4]
            assert got == want, f"{name} instruction {retired}: cpu {[hex(x) for x in got]}, model {[hex(x) for x in want]}"
            retired += 1
        if int(dut.dmem_wstrb.value) and int(dut.dmem_addr.value) == RESULT:
            code = int(dut.dmem_wdata.value)
            assert code == 1, f"{name} failed test case {code >> 1}"
            dut._log.info(f"{name}: pass, {retired} instructions in {cycle} cycles")
            return
    raise AssertionError(f"{name}: no result after 100000 cycles")

@pytest.fixture(scope="module")
def runner():
    return build("cpu_board", SOURCES, __file__)

def test_found_the_tests():
    assert len(NAMES) >= 38

@pytest.mark.parametrize("name", NAMES)
def test_rv32ui(runner, name):
    os.environ["PROGRAM"] = name
    run("cpu_board", SOURCES, __file__, plusargs=[f"+program={hex_file(name)}"], runner=runner, results=str(BUILD / f"{name}.result.xml"))
