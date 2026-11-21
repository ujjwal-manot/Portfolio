# Runs the ADC-rate bridge test on the mapped cell netlist (make timing first) and on the routed one (make layout first) with the IHP cell models and the SDF delays of each corner (slow, typ, fast), recording the waveform each corner's power report reads, and checks every m_clk-to-output delay against the arrival STA computed (within 0.5 ps mapped, 3 ps routed, whose SDF has 1 ps steps) to show the SDF really timed the run; the cell models are copied with their 10 ps time step cut to 100 fs so the SDF's 0.1 ps delays survive, and Icarus skips their setup and hold checks, which STA covers.
import os, random
from pathlib import Path
import pytest
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import FallingEdge, RisingEdge, Timer
from cocotb.utils import get_sim_time
from cocotb_run import run
from test_fifo_bridge import adc_samples_to_cpu

CELLS = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog")
HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"
ROUTED = HERE.parent / "layout/runs/signoff/final/nl/fifo_bridge.nl.v"
OUTPUTS = ("m_tvalid", "m_tlast", "m_tdata")
TOLERANCE = {False: 0.0005, True: 0.003}

def fine(name):
    text = (CELLS / name).read_text()
    assert "`timescale 1ns/10ps" in text
    (BUILD / name).write_text(text.replace("`timescale 1ns/10ps", "`timescale 1ns/100fs"))
    return BUILD / name

def expected(corner, routed):
    rows = (BUILD / f"clock_to_output_{'routed_' if routed else ''}{corner}.txt").read_text().split("\n")
    return {port: {1: float(rise), 0: float(fall)} for port, rise, fall in (r.split() for r in rows if r)}

@cocotb.test()
async def clock_to_output_matches_sta(dut):
    corner = next(c for c in ("slow", "typ", "fast") if c.upper() in os.environ)
    routed = "ROUTED" in os.environ
    arcs = expected(corner, routed)
    assert len(arcs) == 10, f"STA gave arrivals for {sorted(arcs)}, expected the 10 m_ outputs"
    cocotb.start_soon(Clock(dut.s_clk, 100, "ns").start())
    cocotb.start_soon(Clock(dut.m_clk, 20, "ns").start())
    dut.s_tvalid.value = dut.m_tready.value = 0
    dut.rst_n.value = 0
    await Timer(307, "ns")
    dut.rst_n.value = 1
    seen, last_rise = {}, [0.0]

    async def edges():
        while True:
            await RisingEdge(dut.m_clk)
            last_rise[0] = get_sim_time("ps")

    async def watch(name):
        signal = getattr(dut, name)
        old = int(signal.value)
        while True:
            await signal.value_change
            new = int(signal.value)
            delay = (get_sim_time("ps") - last_rise[0]) / 1000
            for bit in range(len(signal)):
                if (old ^ new) >> bit & 1:
                    port = f"{name}[{bit}]" if name == "m_tdata" else name
                    seen.setdefault((port, new >> bit & 1), []).append(delay)
            old = new

    cocotb.start_soon(edges())
    for name in OUTPUTS:
        cocotb.start_soon(watch(name))
    for i in range(40):
        await FallingEdge(dut.s_clk)
        dut.s_tvalid.value, dut.s_tdata.value, dut.s_tlast.value = 1, random.getrandbits(8), i % 2
        dut.m_tready.value = i % 3 != 0
    dut.s_tvalid.value = 0
    await Timer(2, "us")
    assert {port for port, _ in seen} == set(arcs), f"outputs that never toggled: {set(arcs) - {p for p, _ in seen}}"
    for (port, value), delays in sorted(seen.items()):
        want = arcs[port][value]
        dut._log.info(f"{'routed' if routed else 'mapped'} {corner} clock to output {port} {'rise' if value else 'fall'}: measured {min(delays):.4f} to {max(delays):.4f} ns over {len(delays)} edges, STA {want:.4f} ns")
        assert all(abs(d - want) < TOLERANCE[routed] for d in delays), f"{port} moved {delays} ns after m_clk, STA says {want} ns"

@pytest.mark.parametrize("corner", ["slow", "typ", "fast"])
@pytest.mark.parametrize("netlist", ["mapped", "routed"])
def test_gates(netlist, corner):
    cells, sdf, flags = (ROUTED, BUILD / f"routed_{corner}_sim.sdf", {"ROUTED": 1}) if netlist == "routed" else (BUILD / "fifo_bridge_cells.v", BUILD / f"fifo_bridge_{corner}_sim.sdf", {})
    run("fifo_bridge", [cells, fine("sg13g2_udp.v"), fine("sg13g2_stdcell.v"), HERE / "sdf.v"], __file__, sim="icarus", waves=True,
        defines={"SDF": f'"{sdf}"', corner.upper(): 1, **flags}, build_args=["-gspecify", "-ginterconnect", "-Tmax", "-s", "sdf"])
