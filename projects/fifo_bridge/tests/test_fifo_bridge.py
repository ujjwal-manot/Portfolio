# Sends 64-sample frames through fifo_bridge between clocks with random phase and an exact 350 ppm offset, with and without metastability injection, resets it in the middle of traffic (every other reset with the bridge full, so both output registers hold a word), feeds it like the ADC (a 50 kHz full-scale sine at 1 MS/s, samples dropped when not ready) and finds how long the CPU can pause before samples are lost.
import math
import os
import random
from collections import deque
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer
import cocotb.utils
from cocotb_run import run

DESIGN = Path(__file__).resolve().parents[1] / "design"
METASTABLE = os.getenv("METASTABLE") == "1"
SOURCES = [DESIGN / f for f in ("sync2.sv", "reset_sync.sv", "async_fifo.sv", "skid_buffer.sv", "fifo_bridge.sv")]

async def frames(dut, s_period, m_period, count, s_rate, m_rate):
    cocotb.start_soon(Clock(dut.s_clk, s_period * 1000, "ps").start())
    await Timer(random.randrange(1, m_period * 1000), "ps")
    cocotb.start_soon(Clock(dut.m_clk, m_period * 1_000_350, "fs").start())
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

async def drive(dut, rate, send):
    while True:
        await FallingEdge(dut.s_clk)
        dut.s_tvalid.value = random.random() < rate
        dut.s_tdata.value, dut.s_tlast.value = send(), 0

async def drain(dut, rate, got):
    while True:
        await FallingEdge(dut.m_clk)
        dut.m_tready.value = random.random() < rate
        await Timer(1, "ns")
        if dut.m_tvalid.value and dut.m_tready.value:
            got.append((int(dut.m_tdata.value), int(dut.m_tlast.value)))

@cocotb.test()
async def reset_during_traffic(dut):
    cocotb.start_soon(Clock(dut.s_clk, 100_000, "ps").start())
    await Timer(random.randrange(1, 20_000), "ps")
    cocotb.start_soon(Clock(dut.m_clk, 20_007_000, "fs").start())
    dut.s_tvalid.value = dut.m_tready.value = 0
    dut.rst_n.value = 0
    await Timer(307, "ns")
    dut.rst_n.value = 1
    for i in range(20):
        got = []
        tasks = [cocotb.start_soon(drive(dut, 0.9, lambda: random.getrandbits(8))), cocotb.start_soon(drain(dut, 0.3, got))]
        await Timer(random.randrange(1, 4_000_000), "ps")
        if i % 2 == 0:
            tasks[1].cancel()
            dut.m_tready.value = 0
            while dut.s_tready.value:
                await FallingEdge(dut.s_clk)
        dut.rst_n.value = 0
        for task in tasks:
            task.cancel()
        dut.s_tvalid.value = dut.m_tready.value = 0
        await Timer(1, "ns")
        assert not dut.s_tready.value and not dut.m_tvalid.value, "bridge handshakes right after reset asserts"
        await Timer(random.randrange(1_000, 400_000), "ps")
        assert not dut.s_tready.value and not dut.m_tvalid.value, "bridge handshakes while in reset"
        dut.rst_n.value = 1
        frame = [(random.getrandbits(8), int(i == 63)) for i in range(64)]
        got = []
        sink = cocotb.start_soon(drain(dut, 0.7, got))
        for data, last in frame:
            await FallingEdge(dut.s_clk)
            dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = 1, data, last
            await Timer(1, "ns")
            while not dut.s_tready.value:
                await FallingEdge(dut.s_clk)
                await Timer(1, "ns")
        await FallingEdge(dut.s_clk)
        dut.s_tvalid.value = 0
        await Timer(3000, "ns")
        sink.cancel()
        assert got == frame, f"after reset got {len(got)} words, first {got[:3]}, expected the fresh 64-word frame"

async def adc(dut, count, accepted, dropped):
    phase = random.random() * 2 * math.pi
    for k in range(count):
        for _ in range(9):
            await FallingEdge(dut.s_clk)
            dut.s_tvalid.value = 0
        await FallingEdge(dut.s_clk)
        sample = (round(127.5 + 127.5 * math.sin(2 * math.pi * 50e3 * k * 1e-6 + phase)), int(k % 64 == 63))
        dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = 1, *sample
        await Timer(1, "ns")
        (accepted if dut.s_tready.value else dropped).append(sample)
    await FallingEdge(dut.s_clk)
    dut.s_tvalid.value = 0

async def cpu(dut, got, pause_at, pause_us):
    while True:
        await FallingEdge(dut.m_clk)
        now = cocotb.utils.get_sim_time("us")
        dut.m_tready.value = not pause_at <= now < pause_at + pause_us
        await Timer(1, "ns")
        if dut.m_tvalid.value and dut.m_tready.value:
            got.append((int(dut.m_tdata.value), int(dut.m_tlast.value)))

async def adc_run(dut, count, pause_us):
    dut.s_tvalid.value = dut.m_tready.value = 0
    dut.rst_n.value = 0
    await Timer(307, "ns")
    dut.rst_n.value = 1
    accepted, dropped, got = [], [], []
    sink = cocotb.start_soon(cpu(dut, got, cocotb.utils.get_sim_time("us") + 20 + random.random(), pause_us))
    await adc(dut, count, accepted, dropped)
    await Timer(3, "us")
    sink.cancel()
    assert got == accepted, f"CPU got {len(got)} samples, the bridge accepted {len(accepted)}"
    return len(dropped)

@cocotb.test()
async def adc_samples_to_cpu(dut):
    cocotb.start_soon(Clock(dut.s_clk, 100_000, "ps").start())
    await Timer(random.randrange(1, 20_000), "ps")
    cocotb.start_soon(Clock(dut.m_clk, 20_007_000, "fs").start())
    assert await adc_run(dut, 256, 0) == 0, "the ADC lost samples with the CPU always ready"

@cocotb.test()
async def cpu_pause_limit(dut):
    cocotb.start_soon(Clock(dut.s_clk, 100_000, "ps").start())
    await Timer(random.randrange(1, 20_000), "ps")
    cocotb.start_soon(Clock(dut.m_clk, 20_007_000, "fs").start())
    lost = {pause: await adc_run(dut, 60, pause) for pause in range(14, 23)}
    dut._log.info(f"samples lost per CPU pause in us: {lost}")
    assert lost[16] == 0, "a 16 us CPU pause lost samples, but plan.md promises 16 us"
    assert any(lost.values()), "no pause filled the bridge, so the depth limit was never reached"

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
