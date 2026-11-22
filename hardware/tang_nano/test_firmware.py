# Verifies hardware/tang_nano/firmware.hex directly on helpers/cpu_model.py by feeding inverted 64-sample sensor frames on 0x1000_0000 and checking UART hex lines emitted on 0x2000_0000.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "helpers"))
from cpu_model import Cpu

def load_hex_image(path):
    words = [int(line.strip(), 16) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    return b"".join(w.to_bytes(4, "little") for w in words)

class BoardCpu(Cpu):
    def __init__(self, image, frames):
        self.queue = []
        for frame in frames:
            for idx, val in enumerate(frame):
                last = 1 if idx == len(frame) - 1 else 0
                self.queue.append((1 << 31) | (last << 8) | (val & 0xFF))
        self.tx = bytearray()
        self.busy_polls = 0
        super().__init__(image, io_read=self._io_read)

    def _io_read(self, addr):
        if addr == 0x10000000:
            return self.queue.pop(0) if self.queue else 0
        if addr == 0x20000004:
            self.busy_polls += 1
            return 1 if (self.busy_polls % 3) != 0 else 0
        return 0

    def io_write(self, addr, data):
        if addr == 0x20000000:
            self.tx.append(data & 0xFF)

def test_firmware_filters_two_frames_and_emits_hex_uart():
    hex_path = Path(__file__).resolve().parent / "firmware.hex"
    frame1 = [i ^ 0xFF for i in range(64)]
    frame2 = [0xAA ^ 0xFF for _ in range(64)]
    sim = BoardCpu(load_hex_image(hex_path), [frame1, frame2])
    for _ in range(4000):
        sim.step()
        if len(sim.tx) >= 8:
            break
    assert sim.tx.decode("ascii") == "1F\r\nAA\r\n"
