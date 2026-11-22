# Verifies projects/whole_chip end-to-end: sensor-to-ADC-to-FIR8 reference chain, bit-exact RV32I fir8_dvfs.hex execution on helpers/cpu_model.py under the 3200-cycle frame budget with DVFS state switching, and DVFS energy scaling from real power_manager speed.log data.
import math, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "helpers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from cpu_model import Cpu
from chip_chain import analog_chain_quantize, fir8_reference, dvfs_energy_table

class ChipCpu(Cpu):
    def __init__(self, image, frames):
        self.queue = []
        for frame in frames:
            for idx, code in enumerate(frame):
                last = 1 if idx == len(frame) - 1 else 0
                self.queue.append((1 << 31) | (last << 8) | (code & 0xFF))
        self.fir_out = []
        self.dvfs_writes = []
        self.peaks = []
        super().__init__(image, io_read=self._io_read)

    def _io_read(self, addr):
        if addr == 0x10000000:
            return self.queue.pop(0) if self.queue else 0
        return 0

    def io_write(self, addr, data):
        if addr == 0x20000000:
            self.dvfs_writes.append(data)
        elif addr == 0x20000004:
            self.fir_out.append(data)
        elif addr == 0x20000008:
            self.peaks.append(data)

def load_hex(path):
    words = [int(l.strip(), 16) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    return b"".join(w.to_bytes(4, "little") for w in words)

def test_analog_headroom_and_end_to_end_firmware_fir8_dvfs():
    v_quiet = [0.6 + 0.12 * math.sin(2.0 * math.pi * 3 * i / 64.0) for i in range(64)]
    v_loud = [0.6 + 0.357 * math.sin(2.0 * math.pi * 2 * i / 64.0) for i in range(64)]
    f1 = analog_chain_quantize(v_quiet, opamp_vos_v=0.0027, adc_vos_lsb=0.5)
    f2 = analog_chain_quantize(v_loud, opamp_vos_v=0.0027, adc_vos_lsb=0.5)
    assert min(f2) > 0 and max(f2) < 255
    want1 = fir8_reference(f1)
    want2 = fir8_reference(f2, init_hist=[c ^ 0xFF for c in f1[-7:]])
    fw_path = Path(__file__).resolve().parents[1] / "firmware" / "fir8_dvfs.hex"
    sim = ChipCpu(load_hex(fw_path), [f1, f2])
    steps_frame1 = 0
    for step in range(8000):
        sim.step()
        if len(sim.dvfs_writes) == 1 and steps_frame1 == 0:
            steps_frame1 = step + 1
        if len(sim.dvfs_writes) >= 2:
            break
    assert sim.fir_out == want1 + want2
    assert steps_frame1 < 3200
    assert sim.dvfs_writes == [0, 3]
    assert sim.peaks == [max(want1), max(want2)]

def test_dvfs_energy_table_uses_real_speed_log():
    speed_log = ROOT / "projects" / "power_manager" / "results" / "speed.log"
    table = dvfs_energy_table(speed_log)
    assert [row["vdd_v"] for row in table] == [0.9, 1.0, 1.1, 1.2]
    e09, e12 = table[0]["energy_per_frame_nj"], table[-1]["energy_per_frame_nj"]
    assert abs((e09 / e12) - (0.9 / 1.2) ** 2) < 1e-6
    assert table[0]["delay_factor"] > 1.9 and table[-1]["delay_factor"] < 0.85
