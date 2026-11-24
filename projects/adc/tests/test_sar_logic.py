# Drives sar_logic with a model front end (sampled input, DAC level, top-plate trim shift and a comparator offset in LSB): after reset the logic must run 8 calibration frames with cal high, the DAC held at 0x80 and a 7-bit SAR search on the trim code in each, average them into the trim it then holds (rails stay at 0 and 127 when the offset is out of range, and comparator noise averages down), deliver no code while calibrating, and then convert a coherent -0.5 dBFS sine 1024 times at ENOB 8.0 +- 0.1 with any offset inside the trim range; each sample takes 2 sampling cycles and 8 trials with the comparator clocked in the low half, m_tlast marks every 64th delivered sample, and a sample that finds the previous one still waiting is dropped and sets the sticky overflow flag without touching the waiting word; the calibration and conversion are also run on the IHP cell netlist (make logic first) with each corner's SDF delays, recording the switching each corner's power report reads, and m_tvalid's clock-to-output delay in that run must match STA's arrival to 1 ps (the cell models' step is cut from 10 ps to 100 fs, and Icarus skips their setup and hold checks, which STA covers).
import math, os, random
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, Edge, FallingEdge, First, RisingEdge, ReadOnly, Timer
from cocotb.utils import get_sim_time
from cocotb_run import run
from adc_spectrum import spectrum, coherent_bin

DESIGN = Path(__file__).resolve().parents[1] / "design"
BUILD = DESIGN.parent / "build"
FS, N, K = 1e6, 1024, 31
LO, HI = 0.2, 1.0
LSB = (HI - LO) / 256
STEP = 0.136
FRAMES, MID = 8, 63

class Front:
    def __init__(self, dut, vin, offset=0.0, noise=0.0, seed=1):
        self.dut, self.vin, self.offset, self.noise, self.rng = dut, vin, offset, noise, random.Random(seed)
        self.held = 0.6
        cocotb.start_soon(self.sampler())
        cocotb.start_soon(self.comparator())

    async def sampler(self):
        while True:
            await FallingEdge(self.dut.samp)
            self.held = LO + int(self.dut.dac.value) * LSB if self.dut.cal.value else self.vin(cocotb.utils.get_sim_time("ns") * 1e-9)

    async def comparator(self):
        while True:
            await RisingEdge(self.dut.comp_clk)
            shift = (int(self.dut.trim.value) - MID) * STEP
            v = (self.held - LO) / LSB - int(self.dut.dac.value) - shift + self.offset + self.rng.gauss(0, self.noise)
            self.dut.comp_out.value = int(v > 0)

async def start(dut, ready=1):
    cocotb.start_soon(Clock(dut.clk, 100, "ns").start())
    dut.comp_out.value = 0
    dut.m_tready.value = ready
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

async def restart(dut):
    await FallingEdge(dut.clk)
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1

async def calibrate(dut):
    frames, dacs, last = 0, set(), None
    while True:
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.m_tvalid.value:
            return frames, dacs, None
        samp = int(dut.samp.value)
        if dut.cal.value:
            dacs.add(int(dut.dac.value))
            frames += last == 1 and samp == 0
        last = samp
        if not dut.cal.value and frames:
            return frames, dacs, int(dut.trim.value)

def expected_trim(offset):
    return min(127, max(0, MID + math.floor(offset / STEP)))

async def tone_codes(dut, n=N, k=K):
    codes = []
    while len(codes) < n + 2:
        await RisingEdge(dut.clk)
        await ReadOnly()
        if dut.m_tvalid.value and dut.m_tready.value:
            codes.append(int(dut.m_tdata.value))
    return codes[2:]

def tone(k=K, n=N):
    fin = k * FS / n
    coherent_bin(FS, n, fin)
    amp = (HI - LO) / 2 * 10 ** (-0.5 / 20)
    return lambda t: 0.6 + amp * math.sin(2 * math.pi * fin * t)

@cocotb.test()
async def ideal_quantizer_scores_eight_bits(dut):
    await start(dut)
    Front(dut, tone())
    frames, dacs, trim = await calibrate(dut)
    assert trim == MID, f"trim {trim} with no offset, expected {MID}"
    r = spectrum(await tone_codes(dut), K)
    dut._log.info(f"ideal quantizer: {r}")
    assert 7.9 <= r["enob"] <= 8.1, f"ideal quantizer ENOB {r['enob']:.3f}, expected 8.0 +- 0.1"

@cocotb.test()
async def calibration_frames_hold_the_dac_and_deliver_nothing(dut):
    await start(dut)
    Front(dut, lambda t: 0.6, offset=1.75)
    frames, dacs, trim = await calibrate(dut)
    assert trim is not None, "a code was delivered before calibration ended"
    assert frames == FRAMES, f"{frames} calibration frames, expected {FRAMES}"
    assert dacs == {0x80}, f"dac during calibration {sorted(dacs)}, expected only 0x80"

@cocotb.test()
async def calibration_cancels_offsets_inside_the_range(dut):
    front = None
    await start(dut)
    for offset in (-8.0, -4.19, -2.0, 0.07, 1.75, 4.19, 8.0):
        if front is None:
            front = Front(dut, tone(5, 128))
        front.offset = offset
        await restart(dut)
        frames, dacs, trim = await calibrate(dut)
        assert abs(trim - expected_trim(offset)) <= 1, f"offset {offset} LSB: trim {trim}, expected {expected_trim(offset)}"
        x = await tone_codes(dut, 128, 5)
        residual = sum(x) / len(x) - 127.5
        dut._log.info(f"offset {offset} LSB: trim {trim}, residual offset {residual:.3f} LSB")
        assert abs(residual) <= 0.25, f"offset {offset} LSB leaves {residual:.3f} LSB after calibration"

@cocotb.test()
async def trim_stops_at_the_rails(dut):
    await start(dut)
    front = Front(dut, lambda t: 0.6)
    for offset, rail in ((12.0, 127), (-12.0, 0)):
        front.offset = offset
        await restart(dut)
        frames, dacs, trim = await calibrate(dut)
        assert trim == rail, f"offset {offset} LSB: trim {trim}, expected the rail {rail}"
        await tone_codes(dut, 4, 1)

@cocotb.test()
async def averaging_shrinks_comparator_noise(dut):
    await start(dut)
    front = Front(dut, lambda t: 0.6, offset=1.75, seed=7)
    frames, dacs, quiet = await calibrate(dut)
    front.noise = 2 * STEP
    errors = []
    for _ in range(12):
        await restart(dut)
        frames, dacs, trim = await calibrate(dut)
        errors.append(trim - quiet)
    rms = math.sqrt(sum(e * e for e in errors) / len(errors))
    dut._log.info(f"trim minus the noiseless trim with 2-step comparator noise over 12 calibrations: {errors}, rms {rms:.2f} steps")
    assert rms <= 1.0, f"averaged trim error {rms:.2f} steps rms, more than one step"

@cocotb.test()
async def sample_timing_and_frames(dut):
    await start(dut)
    Front(dut, lambda t: 0.6)
    await calibrate(dut)
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
    Front(dut, lambda t: 0.6)
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

@cocotb.test()
async def clock_to_output_matches_sta(dut):
    corner = next(c for c in ("slow", "typ", "fast") if c.upper() in os.environ)
    rise, fall = [float(v) for v in (BUILD / f"clock_to_output_{corner}.txt").read_text().split()[1:]]
    await start(dut)
    Front(dut, lambda t: 0.6)
    seen = {}
    while len(seen) < 2:
        await RisingEdge(dut.clk)
        edge = get_sim_time("ps")
        fired = await First(Edge(dut.m_tvalid), Timer(20, "ns"))
        if isinstance(fired, Edge):
            seen.setdefault(int(dut.m_tvalid.value), (get_sim_time("ps") - edge) / 1000)
    dut._log.info(f"{corner}: m_tvalid rise {seen[1]:.4f} ns, fall {seen[0]:.4f} ns after clk; STA {rise:.4f} and {fall:.4f} ns")
    assert abs(seen[1] - rise) <= 0.001 and abs(seen[0] - fall) <= 0.001, "the gate run is not timed by the SDF"

def fine(name):
    cells = Path(os.environ["PDK_ROOT"]) / os.environ["PDK"] / "libs.ref/sg13g2_stdcell/verilog"
    text = (cells / name).read_text()
    assert "`timescale 1ns/10ps" in text
    (BUILD / name).write_text(text.replace("`timescale 1ns/10ps", "`timescale 1ns/100fs"))
    return BUILD / name

def test_sar_logic():
    run("sar_logic", [DESIGN / "sar_logic.sv"], __file__, defines={"COCOTB_TEST_FILTER": "^(?!clock_to_output)"})

@pytest.mark.parametrize("corner", ["slow", "typ", "fast"])
def test_sar_logic_gates(corner):
    run("sar_logic", [BUILD / "sar_logic_cells.v", fine("sg13g2_udp.v"), fine("sg13g2_stdcell.v"), Path(__file__).parent / "sdf.v"], __file__, sim="icarus", waves=True,
        defines={"SDF": f'"{BUILD / f"sar_logic_{corner}_sim.sdf"}"', "TOP": "sar_logic", corner.upper(): 1, "COCOTB_TEST_FILTER": "ideal_quantizer_scores_eight_bits|clock_to_output_matches_sta"},
        build_args=["-gspecify", "-ginterconnect", "-Tmax", "-s", "sdf"])
