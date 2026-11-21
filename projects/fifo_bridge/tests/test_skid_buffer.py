# Checks the skid buffer never loses or reorders words, runs at full rate, and keeps s_ready registered.
import random
from collections import deque
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, Timer
from cocotb_run import run

DESIGN = Path(__file__).resolve().parents[1] / "design"

async def start(dut):
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_valid.value = dut.m_ready.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

async def stream(dut, words, valid_rate, ready_rate):
    expected, sent, got, hold = deque(), 0, 0, None
    while got < words:
        await FallingEdge(dut.clk)
        if hold is None and sent < words and random.random() < valid_rate:
            hold = random.getrandbits(9)
        ready = random.random() < ready_rate
        dut.s_valid.value, dut.s_data.value, dut.m_ready.value = hold is not None, hold or 0, ready
        await Timer(1, "ns")
        if hold is not None and dut.s_ready.value:
            expected.append(hold)
            sent, hold = sent + 1, None
        if dut.m_valid.value and ready:
            assert int(dut.m_data.value) == expected.popleft(), f"word {got} wrong"
            got += 1
    return got

@cocotb.test()
async def random_backpressure(dut):
    await start(dut)
    assert await stream(dut, 20000, 0.7, 0.6) == 20000

@cocotb.test()
async def full_rate_without_bubbles(dut):
    await start(dut)
    dut.m_ready.value = dut.s_valid.value = 1
    accepted = 0
    for _ in range(200):
        await FallingEdge(dut.clk)
        accepted += int(dut.s_ready.value)
    assert accepted == 200, f"only {accepted} of 200 cycles accepted a word"

@cocotb.test()
async def s_ready_does_not_follow_m_ready(dut):
    await start(dut)
    dut.s_valid.value, dut.s_data.value = 1, 5
    for _ in range(500):
        await FallingEdge(dut.clk)
        before = int(dut.s_ready.value)
        dut.m_ready.value = random.random() < 0.5
        await Timer(1, "ns")
        assert int(dut.s_ready.value) == before, "s_ready changed in the same cycle as m_ready"

def test_skid_buffer():
    run("skid_buffer", [DESIGN / "skid_buffer.sv"], __file__)
