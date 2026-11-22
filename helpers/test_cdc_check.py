# Runs cdc_check on probe designs built by Yosys, as RTL and mapped to IHP cells, and checks it reports exactly the crossing problem each probe was written to have, that waivers hide only what they match, that the fifo_bridge memory waiver names only the output stage, and that an SRAM macro counts as a register on the clock at its A_CLK pin.
import subprocess, pytest
from pathlib import Path
from cdc_check import find, read_waivers, waived

LIB = "/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/lib/sg13g2_stdcell_typ_1p20V_25C.lib"
PROBES = Path(__file__).resolve().parent.parent / "projects/fifo_bridge/cdc/probes"
WANT = {"clean": [], "no_sync": ["logic_before_sync"], "logic_before_sync": ["logic_before_sync"], "meta_used": ["meta_fanout"],
        "binary_bus": ["multibit"], "raw_reset": ["raw_reset"], "reset_from_a": ["reset_crossing"], "reset_sync_ok": []}

MAP = {"rtl": "prep -flatten -top {}", "cells": f"read_liberty -lib {LIB}; synth -flatten -top {{}}; dfflibmap -liberty {LIB}; abc -liberty {LIB}; opt_clean; hilomap -singleton -hicell sg13g2_tiehi L_HI -locell sg13g2_tielo L_LO"}

@pytest.mark.parametrize("probe", sorted(WANT))
@pytest.mark.parametrize("level", sorted(MAP))
def test_probe(probe, level, tmp_path):
    netlist = tmp_path / f"{probe}.json"
    subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {PROBES / probe}.sv; {MAP[level].format(probe)}; write_json {netlist}"], check=True)
    ports = {"d": "b_clk" if probe in ("raw_reset", "reset_from_a", "reset_sync_ok") else "a_clk", "e": "a_clk"}
    assert sorted({f[0] for f in find(netlist, probe, ports)}) == WANT[probe]

def test_waivers_hide_only_what_they_match(tmp_path):
    netlist = tmp_path / "bus.json"
    subprocess.run(["yosys", "-q", "-p", f"read_verilog -sv {PROBES}/binary_bus.sv; prep -flatten -top binary_bus; write_json {netlist}"], check=True)
    assert find(netlist, "binary_bus", {}, ["count -> meta: *"]) == []
    assert find(netlist, "binary_bus", {}, ["count -> meta: *", "nothing *"]) == [("unused_waiver", "nothing *")]

def test_fifo_bridge_memory_waiver_covers_only_the_output_stage():
    waivers = read_waivers(PROBES.parent / "waivers.txt")
    assert waived("m_tdata on m_clk samples fifo.mem[0], fifo.mem[1] through logic", waivers)
    assert waived("out.skid on m_clk samples fifo.mem[0] through logic", waivers)
    assert not waived("fifo.r_ready on m_clk samples fifo.mem[0] through logic", waivers)

def test_clock_buffers_and_repair_buffers_change_nothing(tmp_path):
    netlist = tmp_path / "tree.json"
    subprocess.run(["yosys", "-q", "-p", f"read_liberty -lib {LIB}; read_verilog {PROBES}/buffered_tree.v; hierarchy -top buffered_tree; write_json {netlist}"], check=True)
    assert find(netlist, "buffered_tree", {"d": "a_clk"}) == []

def test_a_flop_behind_an_output_buffer_is_named_after_its_port(tmp_path):
    probe = (PROBES / "buffered_tree.v").read_text().replace(".D(meta), .Q(net7)", ".D(mix), .Q(net7)").replace("  wire net7;", "  wire net7, mix;\n  sg13g2_xor2_1 x (.A(meta), .B(src_buf), .X(mix));")
    (tmp_path / "bad.v").write_text(probe)
    netlist = tmp_path / "bad.json"
    subprocess.run(["yosys", "-q", "-p", f"read_liberty -lib {LIB}; read_verilog {tmp_path}/bad.v; hierarchy -top buffered_tree; write_json {netlist}"], check=True)
    assert ("logic_before_sync", "q on b_clk samples src through logic") in find(netlist, "buffered_tree", {"d": "a_clk"})

SRAM = "/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_sram/lib/RM_IHPSG13_1P_2048x32_c2_bm_bist_typ_1p20V_25C.lib"

@pytest.mark.parametrize("macro_clk, want", [("a_clk", []), ("b_clk", ["logic_before_sync"])])
def test_an_sram_macro_is_a_register_on_its_own_clock(macro_clk, want, tmp_path):
    probe = f"""module macro (input a_clk, b_clk, rst_n, d, output q);
  wire addr, dout;
  sg13g2_dfrbpq_1 f1 (.CLK(a_clk), .D(d), .RESET_B(1'b1), .Q(addr));
  RM_IHPSG13_1P_2048x32_c2_bm_bist mem (.A_CLK({macro_clk}), .A_MEN(1'b1), .A_WEN(1'b0), .A_REN(1'b1), .A_ADDR({{10'b0, addr}}), .A_DIN(32'b0), .A_DLY(1'b1),
    .A_DOUT({{dout_hi, dout}}), .A_BM(32'b0), .A_BIST_CLK(1'b0), .A_BIST_EN(1'b0), .A_BIST_MEN(1'b0), .A_BIST_WEN(1'b0), .A_BIST_REN(1'b0),
    .A_BIST_ADDR(11'b0), .A_BIST_DIN(32'b0), .A_BIST_BM(32'b0));
  wire [30:0] dout_hi;
  wire mix;
  sg13g2_xor2_1 x (.A(dout), .B(addr), .X(mix));
  sg13g2_dfrbpq_1 f2 (.CLK(a_clk), .D(mix), .RESET_B(1'b1), .Q(q));
endmodule
"""
    (tmp_path / "macro.v").write_text(probe)
    netlist = tmp_path / "macro.json"
    subprocess.run(["yosys", "-q", "-p", f"read_liberty -lib {LIB}; read_liberty -lib {SRAM}; read_verilog {tmp_path}/macro.v; hierarchy -top macro; write_json {netlist}"], check=True)
    assert sorted({f[0] for f in find(netlist, "macro", {"d": "a_clk", "rst_n": "a_clk"})}) == want
