# Runs the filter firmware at full stream rate on the mapped cpu_top (IHP cells and the SRAM macros' own models, zero delay) under Icarus with a waveform for the power report: the filter outputs and event counts in the data macro must match the Python reference when the firmware reports its frame times.
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, RisingEdge, ReadOnly
from cocotb_run import run
from lockstep import hex_file
from test_filter import BUILD, FRAMES, feed, reference, samples, symbols

HERE = Path(__file__).resolve().parent
CELLS = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_stdcell/verilog")
SRAM = Path("/foss/pdks/ihp-sg13g2/libs.ref/sg13g2_sram/verilog")
SOURCES = [BUILD / "cpu_cells.v", HERE / "cpu_top_board.sv", CELLS / "sg13g2_udp.v", CELLS / "sg13g2_stdcell.v",
           SRAM / "RM_IHPSG13_1P_2048x32_c2_bm_bist.v", SRAM / "RM_IHPSG13_1P_core_behavioral_bm_bist.v"]

@cocotb.test()
async def filter_on_cells(dut):
    codes, sym = samples(), symbols()
    memory = dut.top.dmem.i_SRAM_1P_behavioral_bm_bist.memory
    cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
    dut.s_tvalid.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 3)
    dut.rst_n.value = 1
    cocotb.start_soon(feed(dut, codes, 0.0))
    last = sym["frame_cycles"] + 4 * (FRAMES - 1)
    for cycle in range(20000):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(memory[last >> 2].value):
            break
    else:
        raise AssertionError("the last frame time never arrived")
    word = lambda a: int(memory[a >> 2].value)
    byte = lambda a: word(a) >> 8 * (a & 3) & 0xFF
    ys, events = reference(codes)
    assert [byte(sym["out"] + i) for i in range(64 * FRAMES)] == ys, "filter outputs differ from the reference"
    assert [word(sym["events"] + 4 * f) for f in range(FRAMES)] == events
    frames = [word(sym["frame_cycles"] + 4 * f) for f in range(FRAMES)]
    dut._log.info(f"filter on cells: events {events}, frame cycles {frames}, {cycle} cycles from reset")

def test_power():
    run("cpu_top_board", SOURCES, __file__, sim="icarus", waves=True, defines={"FUNCTIONAL": 1},
        plusargs=[f"+program={hex_file(BUILD / 'filter.bin')}"])
