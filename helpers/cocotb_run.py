# Builds and runs one cocotb test module on the simulator named by SIM (verilator by default).
import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def build(top, sources, test_file, parameters={}):
    sim = os.getenv("SIM", "verilator")
    build_dir = Path(test_file).parent.parent / "build" / f"{sim}_{top}_{Path(test_file).stem}"
    runner = get_runner(sim)
    runner.build(sources=sources, hdl_toplevel=top, build_dir=build_dir, parameters=parameters, always=True, timescale=("1ns", "1ps"))
    return runner

def run(top, sources, test_file, parameters={}, plusargs=[], runner=None, results=None):
    runner = runner or build(top, sources, test_file, parameters)
    test_dir = Path(test_file).parent
    runner.test(test_module=Path(test_file).stem, hdl_toplevel=top, test_dir=test_dir, parameters=parameters,
                plusargs=plusargs, results_xml=results)
