# Runs every rv32ui test and every rv32mi machine-mode test on Spike (configured like the cpu: machine mode only, no PMP, no debug triggers, so the breakpoint and pmpaddr tests, which test those optional extensions, are left out) and on cpu_model.py; the two must retire the same instructions with the same results.
import re, subprocess
from pathlib import Path
import pytest
from cpu_model import Cpu

BUILD = Path(__file__).resolve().parents[1] / "build"
SKIP = {"breakpoint_spike", "pmpaddr_spike"}
NAMES = sorted(f"{p.parent.name}/{p.stem.removesuffix('_spike')}" for s in ("rv32ui", "rv32mi") for p in (BUILD / s).glob("*_spike.elf") if p.stem not in SKIP)
SPIKE = ["spike", "--isa=rv32i_zicsr_zicntr", "--priv=m", "--pmpregions=0", "--triggers=0", "-m0x80000000:0x10000", "-l", "--log-commits"]
COMMIT = re.compile(r"^core\s+0: 3 0x([0-9a-f]+) \(0x([0-9a-f]+)\)(?: x(\d+)\s+0x([0-9a-f]+))?(?: mem 0x([0-9a-f]+))?", re.M)

def tohost(name):
    symbols = subprocess.run(["riscv64-unknown-elf-nm", BUILD / f"{name}_spike.elf"], capture_output=True, text=True, check=True).stdout
    return int(re.search(r"^([0-9a-f]+) . tohost$", symbols, re.M).group(1), 16)

def spike(name):
    run = subprocess.run(SPIKE + [BUILD / f"{name}_spike.elf"],
                         capture_output=True, text=True, timeout=60)
    assert run.returncode == 0, f"{name}: Spike says the test failed ({run.returncode})"
    trace = []
    for pc, instr, rd, value, mem in COMMIT.findall(run.stdout + run.stderr):
        if int(pc, 16) < 0x80000000:
            continue
        trace.append((int(pc, 16), int(instr, 16), int(rd or 0), int(value or "0", 16)))
        if mem and int(mem, 16) == tohost(name):
            return trace
    raise AssertionError(f"{name}: Spike never wrote the result")

def model(name):
    cpu = Cpu((BUILD / f"{name}_spike.bin").read_bytes(), base=0x80000000, ids={0xF12: 5})
    trace = []
    for _ in range(20000):
        pc, instr, rd, value, store = cpu.step()
        trace.append((pc, instr, rd, value))
        if store and store[0] == tohost(name):
            assert store[1] == 1, f"{name}: model reports failure code {store[1]}"
            return trace
    raise AssertionError(f"{name}: model never wrote the result")

def test_found_the_tests():
    assert len(NAMES) >= 54, f"only {len(NAMES)} tests built"

@pytest.mark.parametrize("name", NAMES)
def test_model_matches_spike(name):
    want, got = spike(name), model(name)
    for i, (w, g) in enumerate(zip(want, got)):
        assert w == g, f"{name} instruction {i}: Spike {[hex(x) for x in w]}, model {[hex(x) for x in g]}"
    assert len(want) == len(got)

def test_mac_accumulates_16_bit_signed_products_only_when_enabled():
    addi = lambda rd, rs1, imm: (imm & 0xFFF) << 20 | rs1 << 15 | rd << 7 | 0x13
    mac = lambda rs1, rs2: rs2 << 20 | rs1 << 15 | 0x0B
    macr = lambda rd: 1 << 12 | rd << 7 | 0x0B
    words = [addi(1, 0, -3), addi(2, 0, 7), mac(1, 2), mac(2, 2), macr(3), mac(1, 1), macr(4), macr(5)]
    image = b"".join(w.to_bytes(4, "little") for w in words)
    cpu = Cpu(image, mac=True)
    got = [cpu.step()[2:4] for _ in words]
    assert got[4] == (3, 28) and got[6] == (4, 9) and got[7] == (5, 0)
    plain = Cpu(image)
    plain.step(), plain.step()
    plain.step()
    assert plain.csr[0x342] == 2 and plain.csr[0x343] == mac(1, 2)
