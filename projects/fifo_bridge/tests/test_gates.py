# Runs the ADC-rate bridge test on the mapped cell netlist (make timing first) with the IHP cell models and the OpenSTA SDF delays of each corner (slow, typ, fast), recording the waveform each corner's power report reads; the cell models are copied with their 10 ps time step cut to 100 fs so the SDF's 0.1 ps delays survive, and Icarus skips their setup and hold checks, which STA covers.
from pathlib import Path
import pytest
from cocotb_run import run
from test_fifo_bridge import adc_samples_to_cpu

CELLS = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog")
HERE = Path(__file__).resolve().parent
BUILD = HERE.parent / "build"

def fine(name):
    text = (CELLS / name).read_text()
    assert "`timescale 1ns/10ps" in text
    (BUILD / name).write_text(text.replace("`timescale 1ns/10ps", "`timescale 1ns/100fs"))
    return BUILD / name

@pytest.mark.parametrize("corner", ["slow", "typ", "fast"])
def test_gates(corner):
    run("fifo_bridge", [BUILD / "fifo_bridge_cells.v", fine("sg13g2_udp.v"), fine("sg13g2_stdcell.v"), HERE / "sdf.v"], __file__, sim="icarus", waves=True,
        defines={"SDF": f'"{BUILD}/fifo_bridge_{corner}_sim.sdf"', corner.upper(): 1}, build_args=["-gspecify", "-ginterconnect", "-Tmax", "-s", "sdf"])
