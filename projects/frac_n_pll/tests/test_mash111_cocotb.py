# Container-ready cocotb verification benches for projects/frac_n_pll RTL blocks (mash111.sv and pfd_div.sv): checks MASH-111 bit-exact sequence, bounds [-3, +4], DC mean, 3rd-order noise shaping (catches broken/mash_order_one.patch), programmable modulus division n_int + dither_in, and dead-zone-free PFD overlap pulses.
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


@cocotb.test()
async def pfd_div_modulus_and_deadzone_free_pulses(dut):
    cocotb.start_soon(Clock(dut.vco_clk, 4, "ns").start())
    dut.ref_clk.value = 0
    dut.n_int.value = 8
    dut.dither_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.vco_clk, 2)
    await ReadOnly()
    assert int(dut.pfd_up.value) == 0 and int(dut.pfd_dn.value) == 0 and int(dut.div_clk.value) == 0
    await FallingEdge(dut.vco_clk)
    dut.rst_n.value = 1

    for dither in (-2, 0, 3):
        dut.n_int.value = 8
        dut.dither_in.value = dither & 0xF
        expected_mod = 8 + dither
        saw_reload = False
        for _ in range(40):
            await RisingEdge(dut.vco_clk)
            await ReadOnly()
            if int(dut.eff_div.value) == expected_mod:
                saw_reload = True
                break
            await FallingEdge(dut.vco_clk)
        assert saw_reload, f"pfd_div failed to load eff_div={expected_mod}"

    await FallingEdge(dut.vco_clk)
    dut.ref_clk.value = 1
    up_cycles, dn_cycles, overlap_cycles = 0, 0, 0
    for _ in range(16):
        await RisingEdge(dut.vco_clk)
        await ReadOnly()
        u, d = int(dut.pfd_up.value), int(dut.pfd_dn.value)
        up_cycles += u
        dn_cycles += d
        overlap_cycles += int(u == 1 and d == 1)
        await FallingEdge(dut.vco_clk)
        dut.ref_clk.value = 0
    assert up_cycles >= 1 and overlap_cycles >= 1 and dn_cycles >= 1


def test_mash111_rtl():
    run("mash111", [DESIGN / "mash111.sv"], __file__, parameters={"W": W}, defines={"COCOTB_TEST_FILTER": "mash111_"})


def test_pfd_div_rtl():
    run("pfd_div", [DESIGN / "pfd_div.sv"], __file__, parameters={"DIV_W": 10, "MIN_DIV": 2}, defines={"COCOTB_TEST_FILTER": "pfd_div_modulus_and_deadzone_free_pulses"})
