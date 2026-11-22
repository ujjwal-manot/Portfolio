# Runs CoreMark (build/coremark, PERFORMANCE_RUN seeds) on each cpu variant in lockstep with cpu_model.py, requires CoreMark's own check ("Correct operation validated") and no error, and logs the timed ticks (mcycle), CoreMark per MHz, CPI over the whole run and the branch and mispredict counts, for the BTB size, 2-bit versus gshare and forwarding trade-offs.
import os, re
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import build, run
from lockstep import RANDOM_SEED, RANDOM_START, RESET_SYNC, Lockstep, hex_file

HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build" / "coremark"
SOURCES = [HERE.parent / "design" / "cpu.sv", RESET_SYNC, HERE / "cpu_board.sv"]
RESULT, PUTCHAR = 0x10000100, 0x10000108
VARIANTS = {"btb16": {}, "btb0": {"BTB": 0}, "btb4": {"BTB": 4}, "btb64": {"BTB": 64},
            "gshare16": {"GSHARE": 1}, "gshare64": {"BTB": 64, "GSHARE": 1}, "no_forwarding": {"FORWARD": 0}}

@cocotb.test()
async def coremark(dut):
    name = os.environ["VARIANT"]
    lock = Lockstep(dut, (BUILD / "coremark.bin").read_bytes(), name)
    text = []
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    await ClockCycles(dut.clk, 2)
    for cycle in range(5000000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        lock.tick(cycle)
        if int(dut.dmem_wstrb.value):
            addr = int(dut.dmem_addr.value)
            if addr == PUTCHAR:
                text.append(chr(int(dut.dmem_wdata.value) & 0xFF))
            elif addr == RESULT:
                break
    else:
        raise AssertionError(f"{name}: CoreMark did not finish in 5000000 cycles")
    out = "".join(text)
    dut._log.info(f"{name} CoreMark output:\n{out}")
    assert "Correct operation validated" in out and "ERROR" not in out and "Errors detected" not in out, f"{name}: CoreMark did not validate"
    ticks = int(re.search(r"Total ticks\s*:\s*(\d+)", out).group(1))
    iterations = int(re.search(r"Iterations\s*:\s*(\d+)", out).group(1))
    branches, mispredicts = int(dut.core.branches.value), int(dut.core.mispredicts.value)
    dut._log.info(f"RESULT {name}: ticks {ticks}, iterations {iterations}, CoreMark/MHz {iterations * 1e6 / ticks:.4f}, "
                  f"CPI {cycle / lock.retired:.4f} ({lock.retired} instructions in {cycle} cycles), branches {branches}, mispredicts {mispredicts}")

@pytest.mark.parametrize("name", VARIANTS)
def test_coremark(name):
    os.environ["VARIANT"] = name
    run("cpu_board", SOURCES, __file__, parameters=VARIANTS[name], defines={f"VARIANT_{name}": 1}, build_args=RANDOM_START,
        plusargs=[f"+program={hex_file(BUILD / 'coremark.bin')}", *RANDOM_SEED])
