# Container-ready cocotb randomized dual-clock verification bench for Cummings SNUG-2002 FIFO1 (fifo1.v): runs slow-writer, fast-writer, and near-equal asynchronous clocks with ppm skew, proving zero loss, duplication, reordering, or overflow beyond 16 entries (catches broken/wrong_full_bit.patch).
import random
from collections import deque
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, Timer
from cocotb_run import run

HERE = Path(__file__).resolve().parent
SOURCES = [HERE / name for name in ("fifomem.v", "sync_r2w.v", "sync_w2r.v", "rptr_empty.v", "wptr_full.v", "fifo1.v")]
DEPTH = 16


async def _traffic(dut, w_period, r_period, words, w_rate, r_rate, seed):
    rng = random.Random(seed)
    ppm = rng.choice((-1, 1)) * rng.randrange(100, 1001, 2)
    dut._log.info(f"rclk runs {ppm} ppm off nominal")
    cocotb.start_soon(Clock(dut.wclk, w_period, "ns").start())
    await Timer(rng.randrange(1, r_period * 1000), "ps")
    cocotb.start_soon(Clock(dut.rclk, r_period * (1_000_000 + ppm), "fs").start())
    dut.winc.value = 0
    dut.rinc.value = 0
    dut.wdata.value = 0
    dut.wrst_n.value = 0
    dut.rrst_n.value = 0
    await Timer(3 * max(w_period, r_period), "ns")
    dut.wrst_n.value = 1
    dut.rrst_n.value = 1
    expected = deque()
    stats = {"full": 0, "empty": 0, "read": 0}

    async def writer():
        sent = 0
        while sent < words:
            await FallingEdge(dut.wclk)
            en = rng.random() < w_rate
            data = rng.getrandbits(8)
            dut.winc.value = int(en)
            dut.wdata.value = data
            stats["full"] += int(dut.wfull.value)
            if en and not int(dut.wfull.value):
                expected.append(data)
                assert len(expected) <= DEPTH, f"wrote past full: {len(expected)} words in {DEPTH}-deep FIFO1"
                sent += 1
                if sent == words // 2:
                    await FallingEdge(dut.wclk)
                    dut.winc.value = 0
                    await Timer(40 * max(w_period, r_period), "ns")
        await FallingEdge(dut.wclk)
        dut.winc.value = 0

    cocotb.start_soon(writer())
    while stats["read"] < words:
        await FallingEdge(dut.rclk)
        en = rng.random() < r_rate
        dut.rinc.value = int(en)
        stats["empty"] += int(bool(int(dut.rempty.value)) and stats["read"] > 0)
        if en and not int(dut.rempty.value):
            assert expected, "FIFO1 claims non-empty when nothing is queued"
            got, want = int(dut.rdata.value), expected.popleft()
            assert got == want, f"word {stats['read']}: got {got:#04x}, expected {want:#04x}"
            stats["read"] += 1
    await FallingEdge(dut.rclk)
    dut.rinc.value = 0
    await Timer(10 * max(w_period, r_period), "ns")
    assert int(dut.rempty.value) == 1 and not expected, "words left over or rempty low at end"
    assert stats["full"] > 0 or w_period > r_period, "test never reached wfull"
    assert stats["empty"] > 0, "test never drained to rempty"


@cocotb.test()
async def slow_writer_fast_reader(dut):
    await _traffic(dut, 100, 21, 2000, 1.0, 0.3, 101)


@cocotb.test()
async def fast_writer_slow_reader(dut):
    await _traffic(dut, 21, 100, 2000, 0.9, 1.0, 102)


@cocotb.test()
async def similar_clocks(dut):
    await _traffic(dut, 37, 41, 4000, 0.6, 0.6, 103)


def test_cummings_fifo1():
    run("fifo1", SOURCES, __file__, parameters={"DSIZE": 8, "ASIZE": 4})
