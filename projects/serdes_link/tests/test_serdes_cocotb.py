# Container-ready cocotb verification benches for projects/serdes_link RTL blocks (prbs.sv, dfe_lms.sv, bb_cdr.sv, pam4_slicer.sv): checks PRBS7/PRBS31 generator and checker, 1-tap sign-sign LMS DFE convergence (catches broken/lms_sign_flipped.patch), Alexander bang-bang CDR tracking (catches broken/cdr_gain_too_high.patch), and 3-threshold PAM4 Gray slicer (catches broken/pam4_thresholds_swapped.patch).
import os
import sys
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge
from cocotb_run import run

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
MODEL = ROOT / "model" if (ROOT / "model").is_dir() else ROOT.parents[1] / "model"
sys.path.insert(0, str(MODEL))
from link_models import dfe_lms_run, pam4_slice, prbs_generate


def _to_signed(val, bits):
    raw = int(val) & ((1 << bits) - 1)
    return raw - (1 << bits) if raw >= (1 << (bits - 1)) else raw


@cocotb.test()
async def prbs_sequence_and_checker(dut):
    order = int(os.environ.get("PRBS_ORDER", "7"))
    n_bits = 260 if order == 7 else 160
    inject_cycle = 80
    ref = prbs_generate(order=order, length=n_bits)
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.en.value = 0
    dut.rx_bit.value = 1
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    held_bit = int(dut.tx_bit.value)
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.tx_bit.value) == held_bit, "tx_bit changed while en == 0"
    await FallingEdge(dut.clk)
    dut.en.value = 1
    tx_bits = []
    for idx in range(n_bits):
        tx_b = int(dut.tx_bit.value)
        assert tx_b == ref[idx], f"PRBS{order} cycle {idx}: tx_bit {tx_b}, expected {ref[idx]}"
        tx_bits.append(tx_b)
        dut.rx_bit.value = tx_b ^ (1 if idx == inject_cycle else 0)
        await RisingEdge(dut.clk)
        await ReadOnly()
        err = int(dut.err_pulse.value)
        if order <= idx < inject_cycle:
            assert err == 0, f"PRBS{order} unexpected error at cycle {idx} after lock"
        elif idx == inject_cycle:
            assert err == 1, f"PRBS{order} failed to flag injected bit error at cycle {idx}"
        elif idx >= inject_cycle + order + 1:
            assert err == 0, f"PRBS{order} failed to re-lock at cycle {idx}"
        await FallingEdge(dut.clk)
    if order == 7:
        assert tx_bits[:127] == tx_bits[127:254], "PRBS7 period is not 127"


@cocotb.test()
async def dfe_lms_convergence_and_bit_exact(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    bits = prbs_generate(order=7, length=512)
    syms = [1 if b else -1 for b in bits]
    h1_true = 30
    samples = [64 * syms[i] + h1_true * (syms[i - 1] if i > 0 else -1) for i in range(len(syms))]
    ref = dfe_lms_run(samples, target_amp=64, flip_sign=False)
    dut.en.value = 0
    dut.sample_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.bit_out.value) == 0 and _to_signed(dut.h1_tap.value, 10) == 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.en.value = 1
    decisions = []
    for idx, samp in enumerate(samples):
        dut.sample_in.value = samp & 0x3FF
        await RisingEdge(dut.clk)
        await ReadOnly()
        got_bit = int(dut.bit_out.value)
        got_h1 = _to_signed(dut.h1_tap.value, 10)
        assert got_bit == ref["decisions"][idx], f"DFE cycle {idx}: bit_out {got_bit} != {ref['decisions'][idx]}"
        assert -127 <= got_h1 <= 127, f"DFE h1_tap out of saturation bounds: {got_h1}"
        decisions.append(got_bit)
        await FallingEdge(dut.clk)
    final_h1 = _to_signed(dut.h1_tap.value, 10)
    tail_errors = sum(1 for a, b in zip(decisions[256:], bits[256:]) if a != b)
    dut._log.info(f"DFE converged h1_tap={final_h1} (true {h1_true}), tail_errors={tail_errors}")
    assert abs(final_h1 - h1_true) <= 3, f"DFE h1_tap {final_h1} did not converge near {h1_true}"
    assert final_h1 == ref["h1_final"], f"DFE h1_tap {final_h1} != reference {ref['h1_final']}"
    assert tail_errors == 0, f"DFE had {tail_errors} bit errors in converged tail"


@cocotb.test()
async def bb_cdr_phase_and_frequency_tracking(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.en.value = 0
    dut.d_prev.value = 0
    dut.edge_mid.value = 0
    dut.d_curr.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.pi_code.value) == 0 and _to_signed(dut.freq_acc.value, 16) == 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.en.value = 1
    prbs_bits = prbs_generate(order=7, length=4001)
    tx_phase, rx_phase = 0.35, 0.0
    prev_code = 0
    pos_wraps = 0
    tail_errs = []
    for idx in range(4000):
        d_prev, d_curr = prbs_bits[idx], prbs_bits[idx + 1]
        tx_phase += 500e-6
        edge_mid = (d_prev if tx_phase > rx_phase else d_curr) if (d_prev != d_curr) else d_curr
        dut.d_prev.value = d_prev
        dut.edge_mid.value = edge_mid
        dut.d_curr.value = d_curr
        await RisingEdge(dut.clk)
        await ReadOnly()
        code = int(dut.pi_code.value)
        delta = code - prev_code
        if delta > 32:
            delta -= 64
        elif delta < -32:
            delta += 64
            pos_wraps += 1
        rx_phase += delta / 64.0
        prev_code = code
        if idx >= 1000:
            tail_errs.append(abs(tx_phase - rx_phase))
        await FallingEdge(dut.clk)
    freq_final = _to_signed(dut.freq_acc.value, 16)
    max_err = max(tail_errs)
    dut._log.info(f"bb_cdr 500ppm: max_tail_err={max_err:.4f} UI, pos_wraps={pos_wraps}, freq_acc={freq_final}")
    assert max_err < 0.2, f"CDR tail phase error {max_err:.4f} UI exceeded 0.2 UI"
    assert pos_wraps >= 2, f"CDR PI code wrapped only {pos_wraps} times over 2.0 UI drift"
    assert freq_final > 0, f"CDR freq_acc {freq_final} did not track positive ppm offset"


@cocotb.test()
async def pam4_slicer_gray_levels_and_thresholds(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.en.value = 0
    dut.sample_in.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.sym_out.value) == 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1
    dut.en.value = 1
    test_vals = list(range(-64, 65, 4))
    ref_dibits = pam4_slice([v / 64.0 for v in test_vals], thresholds=(-0.5, 0.0, 0.5))
    for val, (msb, lsb) in zip(test_vals, ref_dibits):
        dut.sample_in.value = val & 0x3FF
        await RisingEdge(dut.clk)
        await ReadOnly()
        want = (msb << 1) | lsb
        got = int(dut.sym_out.value)
        assert got == want, f"pam4_slicer sample_in={val}: sym_out={got:02b}, expected {want:02b}"
        await FallingEdge(dut.clk)


def test_prbs7_rtl():
    run("prbs", [DESIGN / "prbs.sv"], __file__, parameters={"ORDER": 7}, defines={"COCOTB_TEST_FILTER": "prbs_sequence_and_checker", "PRBS_ORDER": 7})


def test_prbs31_rtl():
    run("prbs", [DESIGN / "prbs.sv"], __file__, parameters={"ORDER": 31}, defines={"COCOTB_TEST_FILTER": "prbs_sequence_and_checker", "PRBS_ORDER": 31})


def test_dfe_lms_rtl():
    run("dfe_lms", [DESIGN / "dfe_lms.sv"], __file__, defines={"COCOTB_TEST_FILTER": "dfe_lms_convergence_and_bit_exact"})


def test_bb_cdr_rtl():
    run("bb_cdr", [DESIGN / "bb_cdr.sv"], __file__, defines={"COCOTB_TEST_FILTER": "bb_cdr_phase_and_frequency_tracking"})


def test_pam4_slicer_rtl():
    run("pam4_slicer", [DESIGN / "pam4_slicer.sv"], __file__, defines={"COCOTB_TEST_FILTER": "pam4_slicer_gray_levels_and_thresholds"})
