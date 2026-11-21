# Runs every rv32ui test and every rv32mi machine-mode test (but breakpoint and pmpaddr, which test the optional debug triggers and PMP this cpu leaves out) on the cpu in lockstep with cpu_model.py (tests/lockstep.py: instructions, stores and interrupts), and the test must report pass.
import os
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import build, run
from lockstep import Lockstep, hex_file

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
SOURCES = [HERE.parent / "design" / "cpu.sv", HERE / "cpu_board.sv"]
SKIP = {"breakpoint", "pmpaddr"}
NAMES = sorted(f"{s}/{p.stem}" for s in ("rv32ui", "rv32mi") for p in (BUILD / s).glob("*.bin") if not p.stem.endswith("_spike") and p.stem not in SKIP)
RESULT = 0x10000100

@cocotb.test()
async def lockstep(dut):
    name = os.environ["PROGRAM"]
    lock = Lockstep(dut, (BUILD / f"{name}.bin").read_bytes(), name)
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    for cycle in range(100000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        lock.tick(cycle)
        if int(dut.dmem_wstrb.value) and int(dut.dmem_addr.value) == RESULT:
            code = int(dut.dmem_wdata.value)
            assert code == 1, f"{name} failed test case {code >> 1}"
            dut._log.info(f"{name}: pass, {lock.retired} instructions in {cycle} cycles")
            return
    raise AssertionError(f"{name}: no result after 100000 cycles")

@pytest.fixture(scope="module")
def runner():
    return build("cpu_board", SOURCES, __file__)

def test_found_the_tests():
    assert len(NAMES) >= 52

@pytest.mark.parametrize("name", NAMES)
def test_isa(runner, name):
    os.environ["PROGRAM"] = name
    run("cpu_board", SOURCES, __file__, plusargs=[f"+program={hex_file(BUILD / f'{name}.bin')}"], runner=runner, results=str(BUILD / f"{name}.result.xml"))
