# Checks the digital LDO controller on its own: inside the fine window it holds, between the fine and coarse comparators its count moves one unit per clock and P more units are turned on or off while there (the proportional kick), beyond the coarse ones the count moves BIG units, and it stops at 0 and N with the thermometer output always matching the units it drives; then against a rail model (2 nF, units of fixed current at the weakest and the strongest corner, a load drawing in proportion to the rail as the cpu's switched capacitance does, the four comparators sampled at the clock) it must settle from an empty rail and after load steps within 300 cycles and then ripple by no more than 15 mV.
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly, FallingEdge
from cocotb_run import run

HERE = Path(__file__).resolve().parent
N, BIG, P = 128, 8, 1

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
    kick = P if lo and not hi and not far_lo else -P if hi and not lo and not far_hi else 0
    assert drive == max(0, min(N, count + kick)), f"drives {drive} units with count {count} and kick {kick}"
    assert int(dut.on.value) == (1 << drive) - 1, f"thermometer {int(dut.on.value):#x} for {drive} units"
    await FallingEdge(dut.clk)
    return drive

@cocotb.test()
async def steps_and_limits(dut):
    await start(dut)
    assert [await clock(dut, 1, 0, 1, 0) for _ in range(3)] == [8, 16, 24]
    assert [await clock(dut, 1, 0, 0, 0) for _ in range(2)] == [26, 27]
    assert [await clock(dut, 0, 0, 0, 0) for _ in range(2)] == [26, 26]
    assert [await clock(dut, 0, 1, 0, 0) for _ in range(2)] == [24, 23]
    assert [await clock(dut, 0, 1, 0, 1) for _ in range(4)] == [16, 8, 0, 0]
    for _ in range(20):
        await clock(dut, 1, 0, 1, 0)
    assert await clock(dut, 1, 0, 1, 0) == N
    assert await clock(dut, 1, 0, 0, 0) == N

async def rail(dut, unit_a, load_a, v, cycles, cap_f=2e-9, period_s=20e-9, vset=1.0, fine=0.01, coarse=0.05):
    history = []
    for _ in range(cycles):
        drive = await clock(dut, int(v < vset - fine), int(v > vset + fine), int(v < vset - coarse), int(v > vset + coarse))
        v = max(0.0, v + (drive * unit_a - load_a * v / vset) * period_s / cap_f)
        history.append(v)
    return v, history

async def regulate(dut, unit_a):
    await start(dut)
    v = 0.0
    for load in (6e-3, 2e-3, 10e-3, 0.5e-3, 0.2e-3):
        v, history = await rail(dut, unit_a, load, v, 600)
        settled = history[300:]
        assert max(abs(x - 1.0) for x in settled) <= 0.015, f"unit {unit_a * 1e3:.2f} mA, load {load * 1e3:g} mA: rail {min(settled):.4f} to {max(settled):.4f} after 300 cycles"

@cocotb.test()
async def regulates_with_the_weakest_units(dut):
    await regulate(dut, 12e-3 / N)

@cocotb.test()
async def regulates_with_the_strongest_units(dut):
    await regulate(dut, 2.9 * 12e-3 / N)

def test_dldo_ctrl():
    run("dldo_ctrl", [HERE.parent / "design" / "dldo_ctrl.sv"], __file__, parameters={"N": N, "BIG": BIG, "P": P})
