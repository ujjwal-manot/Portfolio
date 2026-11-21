# Drives sar_logic with an ideal comparator and DAC: a coherent -0.5 dBFS sine converted 1024 times must score ENOB 8.0 +- 0.1, each sample takes 2 sampling cycles and 8 trials with the comparator clocked in the low half, m_tlast marks every 64th delivered sample, and a sample that finds the previous one still waiting is dropped and sets the sticky overflow flag without touching the waiting word.
import math
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, RisingEdge, ReadOnly
from cocotb_run import run
from adc_spectrum import spectrum, coherent_bin

DESIGN = Path(__file__).resolve().parents[1] / "design"
FS, N, K = 1e6, 1024, 31
LO, HI = 0.2, 1.0

async def start(dut, ready=1):
    cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    dut.comp_out.value = 0
    dut.m_tready.value = ready
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

async def sampler(dut, vin, state):
    while True:
        await FallingEdge(dut.samp)
        state["held"] = vin(cocotb.utils.get_sim_time("ns") * 1e-9)

@cocotb.test()
async def ideal_quantizer_scores_eight_bits(dut):
    fin = K * FS / N
    coherent_bin(FS, N, fin)
    amp = (HI - LO) / 2 * 10 ** (-0.5 / 20)
    state = {"held": 0.6}
    vin = lambda t: 0.6 + amp * math.sin(2 * math.pi * fin * t)
    await start(dut)
    cocotb.start_soon(sampler(dut, vin, state))
    async def front():
        while True:
            await RisingEdge(dut.comp_clk)
            dut.comp_out.value = int(state["held"] > LO + int(dut.dac.value) * (HI - LO) / 256)
    cocotb.start_soon(front())
    codes = []
    while len(codes) < N + 2:
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.m_tvalid.value and dut.m_tready.value:
            codes.append(int(dut.m_tdata.value))
    r = spectrum(codes[2:], K)
    dut._log.info(f"ideal quantizer: {r}")
    assert 7.9 <= r["enob"] <= 8.1, f"ideal quantizer ENOB {r['enob']:.3f}, expected 8.0 +- 0.1"

@cocotb.test()
async def sample_timing_and_frames(dut):
    await start(dut)
    samp, trials, delivered, lasts = [], [], 0, []
    for cycle in range(64 * 10 + 30):
        await RisingEdge(dut.clk)
        await ReadOnly()
        samp.append(int(dut.samp.value))
        if dut.m_tvalid.value and dut.m_tready.value:
            delivered += 1
            if dut.m_tlast.value:
                lasts.append(delivered)
        await FallingEdge(dut.clk)
        await ReadOnly()
        trials.append(int(dut.comp_clk.value))
    first = next(i for i in range(len(samp) - 1) if samp[i] and samp[i + 1])
    window = samp[first:first + 100]
    assert all(window[i:i + 10] == [1, 1] + [0] * 8 for i in range(0, 100, 10)), f"samp pattern {window[:20]}"
    assert all(trials[first + i:first + i + 10] == [0, 0] + [1] * 8 for i in range(0, 100, 10)), "comparator not clocked in the low half of the 8 trial cycles"
    assert lasts == [64], f"m_tlast on delivered samples {lasts}, expected only the 64th"
    assert not dut.overflow.value

@cocotb.test()
async def overflow_drops_new_samples_and_keeps_the_waiting_word(dut):
    await start(dut, ready=0)
    await RisingEdge(dut.m_tvalid)
    await ReadOnly()
    waiting = int(dut.m_tdata.value)
    assert not dut.overflow.value
    for _ in range(25):
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert dut.m_tvalid.value and int(dut.m_tdata.value) == waiting, "waiting word changed while m_tready was low"
    assert dut.overflow.value, "overflow not set after a sample was dropped"
    await FallingEdge(dut.clk)
    dut.m_tready.value = 1
    await ClockCycles(dut.clk, 30)
    assert dut.overflow.value, "overflow is not sticky"

def test_sar_logic():
    run("sar_logic", [DESIGN / "sar_logic.sv"], __file__)
