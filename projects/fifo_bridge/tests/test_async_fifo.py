# Random traffic through async_fifo across unrelated clocks (random phase, random offset of 100 to 1000 ppm either way, as between two free-running oscillators), with and without metastability injection; every word must come out once, in order, the FIFO must never hold more than 16 words (DEPTH_LOG2 = 4), and it must run empty after data starts (the writer pauses halfway).
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
DEPTH = 16

async def traffic(dut, w_period, r_period, words, w_rate, r_rate):
    ppm = random.choice((-1, 1)) * random.randrange(100, 1001, 2)
    dut._log.info(f"r_clk runs {ppm} ppm off nominal")
    cocotb.start_soon(Clock(dut.w_clk, w_period, "ns").start())
    await Timer(random.randrange(1, r_period * 1000), "ps")
    cocotb.start_soon(Clock(dut.r_clk, r_period * (1_000_000 + ppm), "fs").start())
    dut.w_en.value = dut.r_en.value = 0
    dut.w_rst_n.value = dut.r_rst_n.value = 0
    await Timer(3 * max(w_period, r_period), "ns")
    dut.w_rst_n.value = dut.r_rst_n.value = 1
    expected, stats = deque(), {"full": 0, "empty": 0, "read": 0}

    async def writer():
        sent = 0
        while sent < words:
            await FallingEdge(dut.w_clk)
            en = random.random() < w_rate
            data = random.getrandbits(9)
            dut.w_en.value, dut.w_data.value = en, data
            stats["full"] += int(dut.w_full.value)
            if en and not dut.w_full.value:
                expected.append(data)
                assert len(expected) <= DEPTH, f"wrote past full: {len(expected)} words held in a {DEPTH}-word FIFO"
                sent += 1
                if sent == words // 2:
                    await FallingEdge(dut.w_clk)
                    dut.w_en.value = 0
                    await Timer(40 * max(w_period, r_period), "ns")
        await FallingEdge(dut.w_clk)
        dut.w_en.value = 0

    cocotb.start_soon(writer())
    while stats["read"] < words:
        await FallingEdge(dut.r_clk)
        en = random.random() < r_rate
        dut.r_en.value = en
        stats["empty"] += int(dut.r_empty.value) and stats["read"] > 0
        if en and not dut.r_empty.value:
            assert expected, "FIFO says it has data but nothing was written"
            got, want = int(dut.r_data.value), expected.popleft()
            assert got == want, f"word {stats['read']}: got {got:#x}, expected {want:#x}"
            stats["read"] += 1
    await Timer(10 * max(w_period, r_period), "ns")
    assert dut.r_empty.value == 1 and not expected, "words left over or FIFO not empty at the end"
    assert stats["full"] > 0 or w_period > r_period, "test never filled the FIFO, so it proves nothing about full"
    assert stats["empty"] > 0, "test never emptied the FIFO"
    if METASTABLE:
        late = int(dut.w_to_r.late_bits.value) + int(dut.r_to_w.late_bits.value)
        dut._log.info(f"metastability injection delayed {late} pointer bits")
        assert late > 0, "injection never delayed a bit, so it was not tested"

@cocotb.test()
async def slow_writer_fast_reader(dut):
    await traffic(dut, 100, 21, 20000, 1.0, 0.3)

@cocotb.test()
async def fast_writer_slow_reader(dut):
    await traffic(dut, 21, 100, 20000, 0.9, 1.0)

@cocotb.test()
async def similar_clocks(dut):
    await traffic(dut, 37, 41, 40000, 0.6, 0.6)

def test_async_fifo():
    run("async_fifo", [DESIGN / "sync2.sv", DESIGN / "async_fifo.sv"], __file__)

def test_async_fifo_metastable():
    run("async_fifo", [DESIGN / "sync2.sv", DESIGN / "async_fifo.sv"], __file__, defines={"METASTABLE": 1}, sim="icarus")
