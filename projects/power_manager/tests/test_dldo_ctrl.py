# Checks the digital LDO controller on its own: inside the fine window it holds, between the fine and coarse comparators its count moves one unit per clock and P more units are turned on or off while there, beyond the coarse ones the count moves BIG units and PB more are turned on or off (the proportional kicks, distinct values here so each shows), and it stops at 0 and N with the thermometer output always matching the units it drives; whether it regulates is checked against the transistor switch array, comparators and decoupling in the loop simulation (tests/make_loop.py), not here.
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, FallingEdge
from cocotb_run import run

HERE = Path(__file__).resolve().parent
N, BIG, P, PB = 128, 2, 2, 8

async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.lo.value = dut.hi.value = dut.far_lo.value = dut.far_hi.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

async def clock(dut, lo, hi, far_lo, far_hi):
    dut.lo.value, dut.hi.value, dut.far_lo.value, dut.far_hi.value = lo, hi, far_lo, far_hi
    await RisingEdge(dut.clk)
    await ReadOnly()
    count, drive = int(dut.count.value), int(dut.drive.value)
    kick = PB if far_lo and not far_hi else -PB if far_hi and not far_lo else P if lo and not hi else -P if hi and not lo else 0
    assert drive == max(0, min(N, count + kick)), f"drives {drive} units with count {count} and kick {kick}"
    assert int(dut.on.value) == (1 << drive) - 1, f"thermometer {int(dut.on.value):#x} for {drive} units"
    await FallingEdge(dut.clk)
    return drive

@cocotb.test()
async def steps_and_limits(dut):
    await start(dut)
    assert [await clock(dut, 1, 0, 1, 0) for _ in range(3)] == [10, 12, 14]
    assert [await clock(dut, 1, 0, 0, 0) for _ in range(2)] == [9, 10]
    assert [await clock(dut, 0, 0, 0, 0) for _ in range(2)] == [8, 8]
    assert await clock(dut, 0, 0, 1, 1) == 8
    assert [await clock(dut, 0, 1, 0, 0) for _ in range(2)] == [5, 4]
    assert [await clock(dut, 0, 1, 0, 1) for _ in range(4)] == [0, 0, 0, 0]
    for _ in range(70):
        await clock(dut, 1, 0, 1, 0)
    assert await clock(dut, 1, 0, 1, 0) == N
    assert await clock(dut, 1, 0, 0, 0) == N

def test_dldo_ctrl():
    run("dldo_ctrl", [HERE.parent / "design" / "dldo_ctrl.sv"], __file__, parameters={"N": N, "BIG": BIG, "P": P, "PB": PB})
