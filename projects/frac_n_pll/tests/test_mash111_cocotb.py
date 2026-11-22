# Container-ready cocotb verification bench for projects/frac_n_pll/design/mash111.sv checking reset, bit-exact match against model/pll_loop.py::mash111_sequence across multiple fractional inputs, dither range [-3, +4], DC mean accuracy, and 3rd-order in-band noise shaping (catches broken/mash_order_one.patch).
import math
import sys
from pathlib import Path
import numpy as np
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge
from cocotb_run import run

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
MODEL = ROOT / "model" if (ROOT / "model").is_dir() else ROOT.parents[1] / "model"
sys.path.insert(0, str(MODEL))
from pll_loop import mash111_sequence

W = 20


def _to_signed(val, bits):
    raw = int(val) & ((1 << bits) - 1)
    return raw - (1 << bits) if raw >= (1 << (bits - 1)) else raw


async def _reset_mash(dut, frac_val):
    dut.frac_in.value = frac_val
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert _to_signed(dut.dither_out.value, 4) == 0, "dither_out must reset to 0"
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1


@cocotb.test()
async def mash111_bit_exact_and_mean(dut):
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    cases = [(1 << W) // 7, 1 << (W - 2), (1 << W) - 1]
    n_steps = 2048
    for frac_val in cases:
        ref = mash111_sequence(frac_val, n_steps, width=W, order=3)
        await _reset_mash(dut, frac_val)
        got = np.empty(n_steps, dtype=np.int32)
        for idx in range(n_steps):
            await RisingEdge(dut.clk)
            await ReadOnly()
            sample = _to_signed(dut.dither_out.value, 4)
            assert -3 <= sample <= 4, f"dither_out {sample} outside [-3, +4] at cycle {idx}"
            assert sample == int(ref[idx]), f"frac_in={frac_val} cycle {idx}: got {sample}, expected {int(ref[idx])}"
            got[idx] = sample
            await FallingEdge(dut.clk)
        mean_err = abs(float(np.mean(got)) - frac_val / float(1 << W))
        assert mean_err < 5e-3, f"frac_in={frac_val}: DC mean error {mean_err:.5f} exceeds 5e-3"


@cocotb.test()
async def mash111_third_order_noise_shaping(dut):
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    frac_val = 13107
    n_steps = 4096
    await _reset_mash(dut, frac_val)
    got = np.empty(n_steps, dtype=np.float64)
    for idx in range(n_steps):
        await RisingEdge(dut.clk)
        await ReadOnly()
        got[idx] = float(_to_signed(dut.dither_out.value, 4))
        await FallingEdge(dut.clk)
    assert np.min(got) < 0 and np.max(got) > 1, f"3rd-order dither range collapsed to [{np.min(got)}, {np.max(got)}]"
    x = got - np.mean(got)
    psd = np.abs(np.fft.rfft(x * np.hanning(n_steps))) ** 2
    freqs = np.fft.rfftfreq(n_steps, d=1.0)
    lo = float(np.mean(psd[(freqs >= 0.005) & (freqs <= 0.03)]))
    hi = float(np.mean(psd[(freqs >= 0.25) & (freqs <= 0.45)]))
    shaping_db = 10.0 * math.log10(hi / max(lo, 1e-30))
    dut._log.info(f"mash111 hi/lo shaping: {shaping_db:.1f} dB, min={int(np.min(got))}, max={int(np.max(got))}")
    assert shaping_db > 50.0, f"insufficient 3rd-order noise shaping: {shaping_db:.1f} dB (expected > 50 dB)"


def test_mash111_rtl():
    run("mash111", [DESIGN / "mash111.sv"], __file__, parameters={"W": W})
