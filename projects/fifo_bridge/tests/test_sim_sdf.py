# Times one IHP xor2 cell in Icarus with the real SDF block of the first xor2 in the slow-corner SDF (make timing first): with the copy timing/sim_sdf.py writes, every edge through it must take the slowest of its conditional arcs, and with the SDF as OpenSTA wrote it every edge takes the plain arc instead, which is the delay Icarus would wrongly use without sim_sdf.py.
import importlib.util, os, re
from pathlib import Path
import pytest
import cocotb
from cocotb.triggers import Timer
from cocotb.utils import get_sim_time
from cocotb_run import run
from test_gates import BUILD, HERE, fine

spec = importlib.util.spec_from_file_location("sim_sdf", HERE.parent / "timing" / "sim_sdf.py")
sim_sdf = importlib.util.module_from_spec(spec)
spec.loader.exec_module(sim_sdf)

def xor_sdf():
    text = (BUILD / "fifo_bridge_slow.sdf").read_text()
    head = text[:text.index("\n (CELL\n")].replace('(DESIGN "fifo_bridge")', '(DESIGN "one_xor")')
    block = next(b for b in re.split(r"(?=\n \(CELL\n)", text) if '"sg13g2_xor2_1"' in b)
    return head + re.sub(r"\(INSTANCE \S+\)", "(INSTANCE u)", block) + "\n)\n"

def arcs(sdf):
    found = {}
    for cond, pin, rise, fall in re.findall(r"(\(COND[^\n]*\n\s*)?\(IOPATH (\w) X \(([^)]*)\) \(([^)]*)\)", sdf):
        found.setdefault(pin, []).append((bool(cond), float(rise.split(":")[-1]), float(fall.split(":")[-1])))
    return found

def expected(sdf, merged):
    want = {}
    for pin, rows in arcs(sdf).items():
        pick = rows if merged else [r for r in rows if not r[0]]
        want[pin] = {1: max(r[1] for r in pick), 0: max(r[2] for r in pick)}
    return want

@cocotb.test()
async def every_edge_takes_the_expected_arc(dut):
    merged = os.environ["KIND"] == "merged"
    want = expected(xor_sdf(), merged)
    assert {p: len(r) for p, r in arcs(xor_sdf()).items()} == {"A": 3, "B": 3}, "expected two conditional arcs and one plain arc per input"
    dut.A.value = dut.B.value = 0
    await Timer(5, "ns")
    seen = []
    for pin, other in (("A", "B"), ("B", "A")):
        for level in (0, 1):
            getattr(dut, other).value = level
            await Timer(5, "ns")
            for _ in range(2):
                old = int(dut.X.value)
                start = get_sim_time("ps")
                getattr(dut, pin).value = 1 - int(getattr(dut, pin).value)
                await dut.X.value_change
                delay = (get_sim_time("ps") - start) / 1000
                seen.append((pin, level, 1 - old, delay))
                await Timer(5, "ns")
    for pin, level, edge, delay in seen:
        dut._log.info(f"{'merged' if merged else 'as written'}: {pin} with the other input at {level}, X {'rise' if edge else 'fall'} after {delay:.4f} ns, expected {want[pin][edge]:.4f} ns")
        assert abs(delay - want[pin][edge]) < 0.0005, f"{pin} to X took {delay} ns, expected {want[pin][edge]} ns"

@pytest.mark.parametrize("kind", ["merged", "as_written"])
def test_sim_sdf(kind):
    raw = BUILD / "one_xor_as_written.sdf"
    raw.write_text(xor_sdf())
    (BUILD / "one_xor_merged.sdf").write_text(sim_sdf.convert(raw.read_text()))
    run("one_xor", [HERE / "one_xor.v", fine("sg13g2_udp.v"), fine("sg13g2_stdcell.v"), HERE / "sdf.v"], __file__, sim="icarus",
        defines={"SDF": f'"{BUILD}/one_xor_{kind}.sdf"', "TOP": "one_xor", "KIND": kind}, build_args=["-gspecify", "-Tmax", "-s", "sdf"])
