# Checks the clock stretch logic on its own: the code is the count of reached taps (a bubble moves it by one), a code under threshold swallows the next cpu edge and then every other one until HOLD clocks after the last low code, so each cpu period is 20 or 40 ns, never a runt pulse (every cpu high phase is the full 10 ns), and with enable low no edge is ever swallowed; whether stretching keeps the cpu inside its timing on a real droop is checked against the transistor loop and detector, not here.
import random
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, Timer
from cocotb.utils import get_sim_time
from cocotb_run import run

HERE = Path(__file__).resolve().parent
NT, HOLD = 64, 2

def taps(code, bubble=None):
    q = 0
    for k in range(1, NT + 1):
        reached = k <= code and k != bubble
        q |= (int(reached) if k % 2 == 0 else int(not reached)) << (k - 1)
    return q

async def start(dut, enable=1, threshold=40):
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.enable.value, dut.threshold.value, dut.q.value = enable, threshold, taps(60)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

async def watch(dut, edges, highs):
    while True:
        await RisingEdge(dut.clk_cpu)
        rise = get_sim_time("ns")
        edges.append(rise)
        await FallingEdge(dut.clk_cpu)
        highs.append(get_sim_time("ns") - rise)

async def run_codes(dut, codes):
    for c in codes:
        await RisingEdge(dut.clk)
        await Timer(3, "ns")
        dut.q.value = taps(c)

@cocotb.test()
async def code_counts_taps(dut):
    await start(dut)
    for c in [0, 1, 2, 17, 40, 63, 64] + random.Random(1).sample(range(NT + 1), 20):
        dut.q.value = taps(c)
        await Timer(1, "ns")
        assert int(dut.code.value) == c, f"code {int(dut.code.value)} for {c} taps"
    dut.q.value = taps(30, bubble=12)
    await Timer(1, "ns")
    assert int(dut.code.value) == 29, f"a bubble gives {int(dut.code.value)}, not 29"

@cocotb.test()
async def droop_doubles_period(dut):
    await start(dut)
    edges, highs = [], []
    cocotb.start_soon(watch(dut, edges, highs))
    await run_codes(dut, [60] * 5 + [30] * 4 + [60] * 8)
    periods = [round(b - a) for a, b in zip(edges, edges[1:])]
    assert set(periods) <= {20, 40}, f"periods {periods}"
    assert periods.count(40) == 3, f"periods {periods}: four low codes and a hold of {HOLD} should swallow three edges"
    assert all(round(h) == 10 for h in highs), f"cpu high phases {highs}"

@cocotb.test()
async def first_low_code_swallows_next_edge(dut):
    await start(dut)
    edges, highs = [], []
    cocotb.start_soon(watch(dut, edges, highs))
    await run_codes(dut, [60] * 3)
    await RisingEdge(dut.clk)
    seen = get_sim_time("ns")
    await Timer(3, "ns")
    dut.q.value = taps(39)
    await RisingEdge(dut.clk)
    await Timer(1, "ns")
    assert edges[-1] <= seen, f"edge at {edges[-1]} ns after a low code seen at {seen} ns"

@cocotb.test()
async def disabled_never_swallows(dut):
    await start(dut, enable=0)
    edges, highs = [], []
    cocotb.start_soon(watch(dut, edges, highs))
    await run_codes(dut, [60] * 3 + [0] * 6 + [60] * 3)
    assert {round(b - a) for a, b in zip(edges, edges[1:])} == {20}

def test_clock_stretch():
    run("clock_stretch", [HERE.parent / "design" / "clock_stretch.sv"], __file__, parameters={"NT": NT, "HOLD": HOLD})
