# Runs cdc_check on probe designs built by Yosys and checks it reports exactly the crossing problem each probe was written to have, and that waivers hide only what they match.
import subprocess, pytest
from pathlib import Path
from cdc_check import find

PROBES = Path(__file__).resolve().parent.parent / "projects/fifo_bridge/cdc/probes"
WANT = {"clean": [], "no_sync": ["logic_before_sync"], "logic_before_sync": ["logic_before_sync"], "meta_used": ["meta_fanout"],
        "binary_bus": ["multibit"], "raw_reset": ["raw_reset"], "reset_from_a": ["reset_crossing"]}

@pytest.mark.parametrize("probe", sorted(WANT))
def test_probe(probe, tmp_path):
    netlist = tmp_path / f"{probe}.json"
    subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {PROBES / probe}.sv; prep -flatten -top {probe}; write_json {netlist}"], check=True)
    ports = {"d": "b_clk" if probe in ("raw_reset", "reset_from_a") else "a_clk", "e": "a_clk"}
    assert sorted({f[0] for f in find(netlist, probe, ports)}) == WANT[probe]

def test_waivers_hide_only_what_they_match(tmp_path):
    netlist = tmp_path / "bus.json"
    subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {PROBES}/binary_bus.sv; prep -flatten -top binary_bus; write_json {netlist}"], check=True)
    assert find(netlist, "binary_bus", {}, ["count -> meta: *"]) == []
    assert find(netlist, "binary_bus", {}, ["count -> meta: *", "nothing *"]) == [("unused_waiver", "nothing *")]
