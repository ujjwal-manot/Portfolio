# Checks the cpu against cpu_model.Timed one clock edge at a time: the instruction in WB spent its EX two edges earlier (MEM and WB never stall), so the model is told that cycle and decides on its own whether an interrupt was due there and which one (external before timer): an interrupt the cpu reports must be exactly that one and a retired instruction must have had none due; every retired instruction must match in pc, instruction, destination register and value, and its store (address, byte strobes and stored bytes, driven to the memory during its EX cycle) must match the model's or be absent; the stream inputs are recorded every edge for the model's IO page, and the pc in decode during each instruction's EX cycle (the one fetched after it) for the model's mispredict counter; nothing is taken from the cpu. Every flop and memory starts at a random value (RANDOM_START, RANDOM_SEED), as in silicon, instead of Verilator's zeros.
from pathlib import Path
from cpu_model import Timed

RESET_SYNC = next(p / "projects/fifo_bridge/design/reset_sync.sv" for p in Path(__file__).resolve().parents if (p / "projects/fifo_bridge").is_dir())
RANDOM_START, RANDOM_SEED = ["--x-initial", "unique"], ["+verilator+rand+reset+2", "+verilator+seed+7"]

def hex_file(binary):
    image = Path(binary).read_bytes()
    image += bytes(-len(image) % 4)
    path = Path(binary).with_suffix(".hex")
    path.write_text("\n".join(f"{int.from_bytes(image[i:i + 4], 'little'):08x}" for i in range(0, len(image), 4)) + "\n")
    return path

class Lockstep:
    def __init__(self, dut, image, name, mtime0=0):
        self.dut, self.name, self.retired, self.stores, self.decode = dut, name, 0, {}, {}
        self.taken, self.both = {7: 0, 11: 0}, 0
        self.model = Timed(image, mtime0=mtime0)

    def tick(self, cycle):
        dut, model = self.dut, self.model
        model.stream[cycle] = (int(dut.s_tvalid.value), int(dut.s_tlast.value), int(dut.s_tdata.value))
        self.stores[cycle] = (int(dut.dmem_wstrb.value), int(dut.dmem_addr.value), int(dut.dmem_wdata.value))
        self.decode[cycle] = int(dut.core.d_pc.value)
        model.now = cycle - 2
        due = model.due()
        if dut.retire_intr.value:
            cause = int(dut.retire_cause.value)
            assert cause == due, f"{self.name}: cpu took interrupt {cause} at cycle {model.now}, the model has {due} due"
            self.taken[cause] += 1
            self.both += model.mip(model.now) & model.csr[0x304] & 0x880 == 0x880
            model.interrupt(cause)
        if not dut.retire_valid.value:
            return
        assert due is None, f"{self.name}: interrupt {due} was due at cycle {model.now} but the cpu retired the instruction at {int(dut.retire_pc.value):#x}"
        got = tuple(int(s.value) for s in (dut.retire_pc, dut.retire_instr, dut.retire_rd, dut.retire_rd_data))
        model.fetched_next = self.decode.pop(cycle - 2)
        pc, instr, rd, value, store = model.step()
        assert got == (pc, instr, rd, value), f"{self.name} instruction {self.retired}: cpu {[hex(x) for x in got]}, model {[hex(x) for x in (pc, instr, rd, value)]}"
        strobe, addr, data = self.stores.pop(cycle - 2)
        want = (((1 << store[2]) - 1) << (store[0] & 3), store[0], store[1]) if store else (0, addr, 0)
        seen = (strobe, addr, data >> 8 * (addr & 3) & ((1 << 8 * store[2]) - 1) if store else 0)
        assert seen == want, f"{self.name} instruction {self.retired} at {pc:#x}: cpu stored {[hex(x) for x in seen]}, model {[hex(x) for x in want]}"
        self.retired += 1
