# Container-ready cocotb mixed-signal testbench for whole_chip covering all 4 plan.md scenarios: power-on start-up, 64-sample sensor waveform end-to-end vs model/chip_chain.py::fir8_reference, firmware DVFS switch 0 -> 3, and load-step droop with clock stretch.
import math
import os
import shutil
import sys
from pathlib import Path

import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge

HERE = Path(__file__).resolve().parent
WC = HERE.parent
ROOT = WC.parent.parent
sys.path.insert(0, str(ROOT / "helpers"))
sys.path.insert(0, str(WC / "model"))
from cocotb_run import build, run


def sources():
    proj = ROOT / "projects"
    return [
        proj / "fifo_bridge" / "design" / "sync2.sv",
        proj / "fifo_bridge" / "design" / "reset_sync.sv",
        proj / "fifo_bridge" / "design" / "async_fifo.sv",
        proj / "fifo_bridge" / "design" / "skid_buffer.sv",
        proj / "fifo_bridge" / "design" / "fifo_bridge.sv",
        proj / "adc" / "design" / "sar_logic.sv",
        proj / "cpu" / "design" / "cpu.sv",
        proj / "power_manager" / "design" / "dldo_ctrl.sv",
        WC / "design" / "whole_chip_top.sv",
        WC / "design" / "rn_analog_models.sv",
        HERE / "whole_chip_cosim_top.sv",
    ]


async def start_clocks(dut):
    cocotb.start_soon(Clock(dut.clk_adc, 100, "ns").start())
    cocotb.start_soon(Clock(dut.clk_sys, 20, "ns").start())


async def power_up_analog_and_release(dut, v_sensor_init_v=0.6):
    await start_clocks(dut)
    dut.rst_ext_n.value = 0
    dut.ldo_en.value = 0
    dut.vin_3v3_uv.value = 0
    dut.v_sensor_uv.value = int(round(v_sensor_init_v * 1e6))
    dut.i_analog_ua.value = 225
    dut.i_load_step_ua.value = 0
    await ClockCycles(dut.clk_sys, 5)
    dut.ldo_en.value = 1
    for step in range(1, 11):
        dut.vin_3v3_uv.value = step * 330_000
        await ClockCycles(dut.clk_sys, 2)
    for _ in range(150):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        if int(dut.por_ok.value) == 1:
            break
    assert int(dut.por_ok.value) == 1, "bandgap/LDO never asserted por_ok"
    await FallingEdge(dut.clk_adc)
    dut.rst_ext_n.value = 1


async def stream_frames(dut, frames_v):
    total = sum(len(f) for f in frames_v)
    adc_codes = []
    fir_outs = []
    peaks = []
    dvfs_writes = []
    vdd_at_dvfs0 = []
    stop_flag = {"done": False}
    dvfs0_cycles = {"n": 0}

    async def monitor_adc():
        while not stop_flag["done"]:
            await RisingEdge(dut.clk_adc)
            await ReadOnly()
            if int(dut.u_chip.s_tvalid.value) and int(dut.u_chip.s_tready.value):
                adc_codes.append(int(dut.u_chip.s_tdata.value))

    async def monitor_mmio():
        while not stop_flag["done"]:
            await RisingEdge(dut.u_chip.clk_cpu)
            await ReadOnly()
            if int(dut.u_chip.is_mmio.value) and int(dut.u_chip.dmem_wstrb.value) != 0:
                off = int(dut.u_chip.dmem_addr.value) & 0xF
                val = int(dut.u_chip.dmem_wdata.value)
                if off == 0x4:
                    fir_outs.append(val)
                elif off == 0x8:
                    peaks.append(val)
                elif off == 0x0:
                    dvfs_writes.append(val & 0x3)

    async def monitor_rail():
        while not stop_flag["done"]:
            await RisingEdge(dut.clk_sys)
            await ReadOnly()
            if int(dut.dvfs_state.value) == 0:
                dvfs0_cycles["n"] += 1
                if dvfs0_cycles["n"] >= 60:
                    vdd_at_dvfs0.append(int(dut.vdd_cpu_uv.value))
            else:
                dvfs0_cycles["n"] = 0

    t_adc = cocotb.start_soon(monitor_adc())
    t_mmio = cocotb.start_soon(monitor_mmio())
    t_rail = cocotb.start_soon(monitor_rail())
    flat = [v for frame in frames_v for v in frame]
    for idx, vin in enumerate(flat):
        if idx == 0 and int(dut.adc_samp.value) == 1:
            dut.v_sensor_uv.value = int(round(vin * 1e6))
            await FallingEdge(dut.adc_samp)
        else:
            await RisingEdge(dut.adc_samp)
            dut.v_sensor_uv.value = int(round(vin * 1e6))
            await FallingEdge(dut.adc_samp)
    for _ in range(500):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        if len(fir_outs) >= total and len(dvfs_writes) >= len(frames_v):
            break
    stop_flag["done"] = True
    t_adc.cancel()
    t_mmio.cancel()
    t_rail.cancel()
    return adc_codes[:total], fir_outs[:total], peaks, dvfs_writes, vdd_at_dvfs0


@cocotb.test()
async def scenario1_power_on_startup(dut):
    await start_clocks(dut)
    dut.rst_ext_n.value = 1
    dut.ldo_en.value = 0
    dut.vin_3v3_uv.value = 0
    dut.v_sensor_uv.value = 600_000
    dut.i_analog_ua.value = 225
    dut.i_load_step_ua.value = 0
    await ClockCycles(dut.clk_sys, 5)
    await ReadOnly()
    assert int(dut.por_ok.value) == 0
    assert int(dut.chip_rst_n.value) == 0

    dut.ldo_en.value = 1
    peak_ana_uv = 0
    for step in range(1, 11):
        dut.vin_3v3_uv.value = step * 330_000
        await ClockCycles(dut.clk_sys, 2)
        await ReadOnly()
        v_ana = int(dut.vdd_ana_uv.value)
        peak_ana_uv = max(peak_ana_uv, v_ana)
        if v_ana < 1_160_000:
            assert int(dut.por_ok.value) == 0, "por_ok asserted below 1.16 V floor"

    for _ in range(150):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        v_ana = int(dut.vdd_ana_uv.value)
        peak_ana_uv = max(peak_ana_uv, v_ana)
        if int(dut.por_ok.value) == 1:
            break
    assert int(dut.por_ok.value) == 1
    assert int(dut.chip_rst_n.value) == 1
    assert peak_ana_uv <= 1_320_000, f"analog start-up overshoot {peak_ana_uv} uV > 1.32 V"

    for _ in range(120):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        if int(dut.droop_alert.value) == 0 and 1_170_000 <= int(dut.vdd_cpu_uv.value) <= 1_230_000:
            break
    assert int(dut.droop_alert.value) == 0
    assert 1_170_000 <= int(dut.vdd_cpu_uv.value) <= 1_230_000

    dut.i_analog_ua.value = 0
    await ClockCycles(dut.clk_sys, 20)
    min_ana_step_uv = 2_000_000
    for step in range(1, 6):
        dut.i_analog_ua.value = step * 100
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        min_ana_step_uv = min(min_ana_step_uv, int(dut.vdd_ana_uv.value))
    for _ in range(30):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        min_ana_step_uv = min(min_ana_step_uv, int(dut.vdd_ana_uv.value))
    assert min_ana_step_uv >= 1_160_000, f"analog rail drooped to {min_ana_step_uv} uV < 1.16 V"


@cocotb.test()
async def scenario2_sensor_waveform_end_to_end(dut):
    from chip_chain import analog_chain_quantize, fir8_reference

    v_quiet = [0.6 + 0.12 * math.sin(2.0 * math.pi * 3 * i / 64.0) for i in range(64)]
    await power_up_analog_and_release(dut, v_sensor_init_v=v_quiet[0])
    adc_codes, fir_outs, peaks, dvfs_writes, _ = await stream_frames(dut, [v_quiet])

    assert int(dut.adc_overflow.value) == 0, "ADC overflow during 64-sample frame"
    assert len(adc_codes) == 64
    assert len(fir_outs) == 64
    ideal_codes = analog_chain_quantize(v_quiet)
    for idx, (got, exp) in enumerate(zip(adc_codes, ideal_codes)):
        assert abs(got - exp) <= 1, f"sample {idx}: ADC code {got} vs ideal {exp}"
    want_fir = fir8_reference(adc_codes)
    assert fir_outs == want_fir, "RTL fir_last sequence diverged from chip_chain.fir8_reference"
    assert peaks and peaks[0] == max(want_fir)
    assert int(dut.fir_last.value) == want_fir[-1]
    assert int(dut.peak_last.value) == max(want_fir)
    assert dvfs_writes and dvfs_writes[0] == 0


@cocotb.test()
async def scenario3_firmware_dvfs_switch_0_to_3(dut):
    from chip_chain import fir8_reference

    v_quiet = [0.6 + 0.12 * math.sin(2.0 * math.pi * 3 * i / 64.0) for i in range(64)]
    v_loud = [0.6 + 0.357 * math.sin(2.0 * math.pi * 2 * i / 64.0) for i in range(64)]
    await power_up_analog_and_release(dut, v_sensor_init_v=v_quiet[0])
    adc_all, fir_all, peaks, dvfs_writes, vdd_at_dvfs0 = await stream_frames(dut, [v_quiet, v_loud])

    assert dvfs_writes[:2] == [0, 3], f"expected DVFS switch [0, 3], got {dvfs_writes}"
    assert vdd_at_dvfs0, "DVFS state 0 never persisted long enough to settle at 0.90 V"
    assert 870_000 <= vdd_at_dvfs0[-1] <= 930_000, f"DVFS state 0 rail {vdd_at_dvfs0[-1]} uV outside 0.90 V"

    peak_cpu_uv = 0
    for _ in range(60):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        peak_cpu_uv = max(peak_cpu_uv, int(dut.vdd_cpu_uv.value))
    v_hi_uv = int(dut.vdd_cpu_uv.value)
    assert int(dut.dvfs_state.value) == 3
    assert 1_170_000 <= v_hi_uv <= 1_230_000, f"DVFS state 3 rail {v_hi_uv} uV outside 1.20 V"
    assert peak_cpu_uv <= 1_320_000, f"DVFS 0->3 overshoot {peak_cpu_uv} uV > 1.32 V"
    assert int(dut.adc_overflow.value) == 0
    want_all = fir8_reference(adc_all)
    assert fir_all == want_all
    assert peaks[:2] == [max(want_all[:64]), max(want_all[64:])]


@cocotb.test()
async def scenario4_load_step_droop_and_clock_stretch(dut):
    await power_up_analog_and_release(dut, v_sensor_init_v=0.6)
    for _ in range(120):
        await RisingEdge(dut.clk_sys)
        await ReadOnly()
        if int(dut.droop_alert.value) == 0 and 1_170_000 <= int(dut.vdd_cpu_uv.value) <= 1_230_000:
            break
    await ClockCycles(dut.clk_sys, 20)
    await ReadOnly()
    n_on_before = int(dut.dldo_on.value).bit_count()

    dut.i_load_step_ua.value = 10_000
    min_vdd_uv = 2_000_000
    max_n_on = n_on_before
    droop_seen = False
    far_lo_seen = False
    clock_stretched = False

    for _ in range(25):
        await FallingEdge(dut.clk_sys)
        await ReadOnly()
        min_vdd_uv = min(min_vdd_uv, int(dut.vdd_cpu_uv.value))
        max_n_on = max(max_n_on, int(dut.dldo_on.value).bit_count())
        if int(dut.droop_alert.value) == 1:
            droop_seen = True
        if int(dut.dldo_far_lo.value) == 1:
            far_lo_seen = True
        if int(dut.u_chip.clk_cpu_en.value) == 0:
            clock_stretched = True

    assert min_vdd_uv < 1_140_000, f"load step did not droop rail below 1.14 V (min {min_vdd_uv} uV)"
    assert droop_seen, "droop_alert never asserted on +10 mA load step"
    assert far_lo_seen, "dldo_far_lo never asserted on +10 mA load step"
    assert clock_stretched, "clk_cpu_en never stretched clock during droop"
    assert max_n_on >= n_on_before + 16, f"DLDO switches only rose from {n_on_before} to {max_n_on}"

    dut.i_load_step_ua.value = 0
    await ClockCycles(dut.clk_sys, 80)
    await ReadOnly()
    assert int(dut.droop_alert.value) == 0, "droop_alert stuck high after load-step release"
    assert int(dut.u_chip.clk_cpu_en.value) == 1, "clk_cpu_en did not resume after recovery"
    assert 1_170_000 <= int(dut.vdd_cpu_uv.value) <= 1_230_000
    assert int(dut.adc_overflow.value) == 0


def test_whole_chip_cocotb():
    sim = os.getenv("SIM", "verilator")
    runner = build("whole_chip_cosim_top", sources(), __file__, sim=sim)
    fw_dst = WC / "build" / f"{sim}_whole_chip_cosim_top_test_whole_chip_cocotb" / "firmware" / "fir8_dvfs.hex"
    fw_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(WC / "firmware" / "fir8_dvfs.hex", fw_dst)
    run("whole_chip_cosim_top", sources(), __file__, runner=runner, sim=sim)
