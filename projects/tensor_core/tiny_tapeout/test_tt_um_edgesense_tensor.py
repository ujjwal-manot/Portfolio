# Verifies projects/tensor_core/tiny_tapeout/tt_um_edgesense_tensor.sv and info.yaml: pinout and parameter contracts (MAXK=32, busy on uio[7]), cycle-accurate byte-serial loading, bank switching, start pulse, and cmem readback on sel=7, plus container cocotb runner.
import importlib.util
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "helpers"))
TT_SV = HERE / "tt_um_edgesense_tensor.sv"
INFO_YAML = HERE / "info.yaml"


class TtWrapperModel:
    def __init__(self):
        self.we = 0
        self.start = 0
        self.busy = 0
        self.mx = 0
        self.sel = 0
        self.prev_sel = 0
        self.fmt = 0
        self.byte_idx = 0
        self.addr = 0
        self.wdata = 0
        self.prev_load = 0
        self.prev_start = 0
        self.banks = {0: {}, 1: {}, 2: {}, 3: {}, 4: {}}
        self.busy_countdown = 0

    def rdata(self):
        return self.banks[2].get(self.addr, 0)

    def uo_out(self):
        return (self.rdata() >> (8 * self.byte_idx)) & 0xFF

    def uio_out(self):
        return (self.busy & 1) << 7

    def step(self, ui_in, uio_in, ena=1):
        self.sel = uio_in & 0x7
        self.fmt = (uio_in >> 3) & 0x3
        load_in = (uio_in >> 5) & 1
        start_in = (uio_in >> 6) & 1
        if not ena:
            return
        if self.we:
            if self.sel in (0, 1):
                self.banks[self.sel][self.addr] = self.wdata & 0xFFFF
            elif self.sel == 2:
                self.banks[2][self.addr] = self.wdata & 0xFFFFFFFF
            elif self.sel in (3, 4):
                self.banks[self.sel][self.addr] = self.wdata & 0xFF
        if self.busy_countdown > 0:
            self.busy_countdown -= 1
            if self.busy_countdown == 0:
                self.busy = 0

        next_addr = (self.addr + 1) & 0xFFFF if self.we else self.addr
        next_byte_idx = self.byte_idx
        next_wdata = self.wdata
        next_we = 0
        next_start = 0
        next_mx = self.mx

        if self.sel != self.prev_sel:
            next_addr = 0
            next_byte_idx = 0
        elif load_in and not self.prev_load and not self.busy:
            if self.sel == 7:
                if self.byte_idx == 3:
                    next_byte_idx = 0
                    next_addr = (next_addr + 1) & 0xFFFF
                else:
                    next_byte_idx = self.byte_idx + 1
            else:
                next_wdata = ((ui_in & 0xFF) << 24) | (self.wdata >> 8)
                if self.byte_idx == 3:
                    next_we = 1
                    next_byte_idx = 0
                else:
                    next_byte_idx = self.byte_idx + 1
        elif start_in and not self.prev_start and not self.busy:
            next_mx = ui_in & 1
            next_start = 1
            next_addr = 0
            next_byte_idx = 0
            self.busy = 1
            self.busy_countdown = 4

        self.prev_sel = self.sel
        self.prev_load = load_in
        self.prev_start = start_in
        self.addr = next_addr
        self.byte_idx = next_byte_idx
        self.wdata = next_wdata
        self.we = next_we
        self.start = next_start
        self.mx = next_mx


def test_tt_protocol_and_pinout_contract():
    sv = re.sub(r"//.*", "", TT_SV.read_text(encoding="utf-8"))
    info = INFO_YAML.read_text(encoding="utf-8")
    assert ".N(4)" in sv and ".MAXK(32)" in sv
    assert "assign uio_oe  = 8'h80;" in sv
    assert "assign uio_out = {busy, 7'b0};" in sv
    assert "assign sel     = uio_in[2:0];" in sv
    assert "assign fmt     = uio_in[4:3];" in sv
    assert 'uio[7]: "busy_out"' in info
    assert 'top_module: "tt_um_edgesense_tensor"' in info


def test_tt_byte_serial_load_bank_switch_start_and_cmem_readback():
    m = TtWrapperModel()

    def load_word(bank_sel, word32):
        if m.prev_sel != bank_sel:
            m.step(0, bank_sel)
        for b_idx in range(4):
            byte_val = (word32 >> (8 * b_idx)) & 0xFF
            m.step(byte_val, bank_sel | (1 << 5))
            m.step(byte_val, bank_sel)
        m.step(0, bank_sel)

    load_word(0, 0x00003F80)
    load_word(0, 0x00004000)
    assert m.banks[0][0] == 0x3F80
    assert m.banks[0][1] == 0x4000

    load_word(1, 0x00004040)
    assert m.banks[1][0] == 0x4040

    load_word(2, 0xDEADBEEF)
    load_word(2, 0x12345678)
    assert m.banks[2][0] == 0xDEADBEEF
    assert m.banks[2][1] == 0x12345678

    load_word(3, 0x0000007F)
    assert m.banks[3][0] == 0x7F

    m.step(1, 3 | (1 << 6))
    assert m.start == 1 and m.mx == 1 and m.uio_out() == 0x80
    while m.busy:
        m.step(0, 0)
    assert m.uio_out() == 0x00

    m.step(0, 7)
    read_words = []
    for _ in range(2):
        w = 0
        for b_idx in range(4):
            w |= m.uo_out() << (8 * b_idx)
            m.step(0, 7 | (1 << 5))
            m.step(0, 7)
        read_words.append(w)
    assert read_words == [0xDEADBEEF, 0x12345678]


if importlib.util.find_spec("cocotb") is not None:
    import cocotb
    from cocotb.clock import Clock
    from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge

    @cocotb.test()
    async def tt_byte_serial_gemm_and_readback(dut):
        cocotb.start_soon(Clock(dut.clk, 20, "ns").start())
        dut.ena.value = 1
        dut.ui_in.value = 0
        dut.uio_in.value = 0
        dut.rst_n.value = 0
        await ClockCycles(dut.clk, 3)
        dut.rst_n.value = 1
        await RisingEdge(dut.clk)

        async def load_word_dut(bank_sel, word32):
            dut.uio_in.value = bank_sel
            await RisingEdge(dut.clk)
            for b_idx in range(4):
                byte_val = (word32 >> (8 * b_idx)) & 0xFF
                dut.ui_in.value = byte_val
                dut.uio_in.value = bank_sel | (1 << 5)
                await RisingEdge(dut.clk)
                dut.uio_in.value = bank_sel
                await RisingEdge(dut.clk)

        await load_word_dut(2, 0x3F800000)
        await load_word_dut(0, 0x00000000)
        await load_word_dut(1, 0x00000000)
        dut.ui_in.value = 0
        dut.uio_in.value = 1 | (1 << 6)
        await RisingEdge(dut.clk)
        dut.uio_in.value = 0
        for _ in range(80):
            await RisingEdge(dut.clk)
            await ReadOnly()
            if (int(dut.uio_out.value) & 0x80) == 0:
                break
        assert (int(dut.uio_out.value) & 0x80) == 0

        dut.uio_in.value = 7
        await RisingEdge(dut.clk)
        word0 = 0
        for b_idx in range(4):
            await ReadOnly()
            word0 |= int(dut.uo_out.value) << (8 * b_idx)
            await RisingEdge(dut.clk)
            dut.uio_in.value = 7 | (1 << 5)
            await RisingEdge(dut.clk)
            dut.uio_in.value = 7
        assert word0 == 0x3F800000


def run_cocotb():
    from cocotb_run import run

    tc_design = ROOT / "projects" / "tensor_core" / "design"
    run(
        "tt_um_edgesense_tensor",
        [tc_design / "fma.sv", tc_design / "tensor_core.sv", TT_SV],
        __file__,
    )


if __name__ == "__main__" and os.getenv("RUN_COCOTB") == "1":
    run_cocotb()
