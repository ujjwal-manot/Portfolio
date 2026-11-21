# Sends 64-sample frames through fifo_bridge between clocks with random phase and 350 ppm offset, with and without metastability injection, and checks reset, data, tlast and AXI-Stream stability.
import os
import random
from collections import deque
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer
from cocotb_run import run

DESIGN = Path(__file__).resolve().parents[1] / "design"
METASTABLE = os.getenv("METASTABLE") == "1"
SOURCES = [DESIGN / f for f in ("sync2.sv", "reset_sync.sv", "async_fifo.sv", "skid_buffer.sv", "fifo_bridge.sv")]

async def frames(dut, s_period, m_period, count, s_rate, m_rate):
    cocotb.start_soon(Clock(dut.s_clk, s_period * 1000, "ps").start())
    await Timer(random.randrange(1, m_period * 1000), "ps")
    cocotb.start_soon(Clock(dut.m_clk, m_period * 1000 + m_period * 350 // 2000 * 2, "ps").start())
    dut.s_tvalid.value = dut.m_tready.value = 0
    dut.rst_n.value = 0
    await Timer(3 * max(s_period, m_period) + 7, "ns")
    assert not dut.s_tready.value and not dut.m_tvalid.value, "bridge handshakes while in reset"
    dut.rst_n.value = 1
    words = [(random.getrandbits(8), i % 64 == 63) for i in range(64 * count)]
    expected = deque()

    async def source():
        for data, last in words:
            while True:
                await FallingEdge(dut.s_clk)
                if random.random() < s_rate:
                    break
                dut.s_tvalid.value = 0
            dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = 1, data, last
            while True:
                await Timer(1, "ns")
                if dut.s_tready.value:
                    break
                await FallingEdge(dut.s_clk)
            expected.append((data, last))
        await FallingEdge(dut.s_clk)
        dut.s_tvalid.value = 0

    cocotb.start_soon(source())
    got, stalled, waiting = 0, 0, None
    while got < len(words):
        await FallingEdge(dut.m_clk)
        if waiting is not None:
            now = (int(dut.m_tvalid.value), int(dut.m_tdata.value), int(dut.m_tlast.value))
            assert now == waiting, f"word {got} changed while m_tready was low: {waiting} -> {now}"
        ready = random.random() < m_rate
        dut.m_tready.value = ready
        await Timer(1, "ns")
        if dut.m_tvalid.value:
            word = (1, int(dut.m_tdata.value), int(dut.m_tlast.value))
            if ready:
                assert expected, "bridge produced a word that was never sent"
                want = expected.popleft()
                assert word[1:] == (want[0], int(want[1])), f"word {got}: got {word[1:]}, expected {want}"
                got, waiting = got + 1, None
            else:
                stalled, waiting = stalled + 1, word
        else:
            waiting = None
    await Timer(10 * max(s_period, m_period), "ns")
    assert not expected and not dut.m_tvalid.value, "words left inside the bridge"
    assert stalled > 0, "m_tready never stalled a valid word, so stability was not tested"
    if METASTABLE:
        late = int(dut.fifo.w_to_r.late_bits.value) + int(dut.fifo.r_to_w.late_bits.value)
        dut._log.info(f"metastability injection delayed {late} pointer bits")
        assert late > 0, "injection never delayed a bit, so it was not tested"

@cocotb.test()
async def adc_clock_to_cpu_clock(dut):
    await frames(dut, 100, 20, 100, 1.0, 0.5)

@cocotb.test()
async def fast_source_slow_sink(dut):
    await frames(dut, 20, 100, 100, 0.9, 0.7)

@cocotb.test()
async def near_equal_clocks(dut):
    await frames(dut, 37, 41, 200, 0.8, 0.8)

def test_fifo_bridge():
    run("fifo_bridge", SOURCES, __file__)

def test_fifo_bridge_metastable():
    run("fifo_bridge", SOURCES, __file__, defines={"METASTABLE": 1}, sim="icarus")
