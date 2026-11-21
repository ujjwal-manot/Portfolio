# Builds and runs one cocotb test module on the simulator named by SIM (verilator by default) or the one given; defines are also passed to the test as environment variables.
import os
from pathlib import Path
from cocotb_tools.runner import get_runner

def build(top, sources, test_file, parameters={}, defines={}, sim=None):
    sim = sim or os.getenv("SIM", "verilator")
    name = "_".join([sim, top, Path(test_file).stem] + sorted(defines))
    runner = get_runner(sim)
    runner.build(sources=sources, hdl_toplevel=top, build_dir=Path(test_file).parent.parent / "build" / name,
                 parameters=parameters, defines=defines, always=True, timescale=("1ns", "1ps"))
    return runner

def run(top, sources, test_file, parameters={}, plusargs=[], runner=None, results=None, defines={}, sim=None):
    runner = runner or build(top, sources, test_file, parameters, defines, sim)
    runner.test(test_module=Path(test_file).stem, hdl_toplevel=top, test_dir=Path(test_file).parent, parameters=parameters,
                plusargs=plusargs, results_xml=results, extra_env={k: str(v) for k, v in defines.items()})
