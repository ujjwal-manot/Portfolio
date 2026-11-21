# Checks the cpu against cpu_model.py one retirement at a time: each retired instruction must match, an interrupt the cpu reports is replayed on the model (which must have it enabled and be at the same pc), and reads whose value depends on timing (the cycle counter and mip) are taken from the cpu, as are IO loads through the model's io_read.
from pathlib import Path
from cpu_model import MSTATUS, MIE

TIMED = {0xB00, 0xB80, 0xC00, 0xC80, 0x344}

def hex_file(binary):
    image = Path(binary).read_bytes()
    image += bytes(-len(image) % 4)
    path = Path(binary).with_suffix(".hex")
    path.write_text("\n".join(f"{int.from_bytes(image[i:i + 4], 'little'):08x}" for i in range(0, len(image), 4)) + "\n")
    return path

def check(dut, model, retired, name):
    if dut.retire_intr.value:
        cause, pc = int(dut.retire_cause.value), int(dut.retire_pc.value)
        assert model.csr[MSTATUS] & 8 and model.csr[MIE] >> cause & 1, f"{name}: cpu took interrupt {cause} that the model has disabled"
        assert pc == model.pc, f"{name}: cpu took interrupt {cause} at {pc:#x}, model is at {model.pc:#x}"
        model.interrupt(cause)
    if not dut.retire_valid.value:
        return retired
    got = tuple(int(s.value) for s in (dut.retire_pc, dut.retire_instr, dut.retire_rd, dut.retire_rd_data))
    want = model.step()[:4]
    if got[1] & 0x7F == 0x73 and got[1] >> 12 & 3 and got[1] >> 20 in TIMED and want[2]:
        model.x[want[2]] = got[3]
        want = (*want[:3], got[3])
    assert got == want, f"{name} instruction {retired}: cpu {[hex(x) for x in got]}, model {[hex(x) for x in want]}"
    return retired + 1
