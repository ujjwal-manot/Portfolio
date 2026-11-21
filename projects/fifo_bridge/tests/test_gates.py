# Runs the 10 MHz to 50 MHz bridge test on the mapped cell netlist (make timing first) with the IHP cell models, recording the waveform used for power.
from pathlib import Path
from cocotb_run import run
from test_fifo_bridge import adc_clock_to_cpu_clock

CELLS = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog")
NETLIST = Path(__file__).resolve().parents[1] / "build" / "fifo_bridge_cells.v"

def test_gates():
    run("fifo_bridge", [NETLIST, CELLS / "sg13g2_udp.v", CELLS / "sg13g2_stdcell.v"], __file__, sim="icarus", waves=True)
