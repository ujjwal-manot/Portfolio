# Container-ready cocotb verification benches for projects/coherent_noc RTL blocks (xy_router.sv, d2d_replay.sv, mesi_dir.sv): checks 5-port X-then-Y routing and credit flow control (catches broken/early_credit_return.patch), CRC-16-CCITT Go-Back-N replay and 7-to-0 wrap (catches broken/replay_skips_flit.patch), and 4-core directory MESI SWMR invalidations (catches broken/missed_invalidate.patch).
import sys
from pathlib import Path
import cocotb
from cocotb.clock import Clock
from cocotb.triggers import ClockCycles, FallingEdge, ReadOnly, RisingEdge
from cocotb_run import run

ROOT = Path(__file__).resolve().parents[1]
DESIGN = ROOT / "design"
MODEL = ROOT / "model" if (ROOT / "model").is_dir() else ROOT.parents[1] / "model"
sys.path.insert(0, str(MODEL))
from noc_model import crc16_ccitt


@cocotb.test()
async def xy_router_routing_and_credits(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.in_valid.value = 0
    dut.in_vc.value = 0
    dut.dst_x.value = 1
    dut.dst_y.value = 1
    dut.in_flit.value = 0
    dut.credit_ret_vc0.value = 0
    dut.credit_ret_vc1.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.out_valid.value) == 0 and int(dut.in_ready.value) == 1
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    route_cases = [
        (2, 0, 3, 0, 0xA0000003),
        (0, 2, 4, 1, 0xA0000004),
        (1, 2, 1, 0, 0xA0000001),
        (1, 0, 2, 1, 0xA0000002),
        (1, 1, 0, 0, 0xA0000000),
    ]
    for dx, dy, port, vc, flit in route_cases:
        dut.in_valid.value = 1
        dut.in_vc.value = vc
        dut.dst_x.value = dx
        dut.dst_y.value = dy
        dut.in_flit.value = flit
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.out_valid.value) == (1 << port), f"dst=({dx},{dy}): out_valid={int(dut.out_valid.value):#x}, expected {1 << port:#x}"
        assert int(dut.out_vc.value) == vc
        assert int(dut.out_flit.value) == flit
        await FallingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.credit_ret_vc0.value = (1 << 3) | (1 << 1) | (1 << 0)
    dut.credit_ret_vc1.value = (1 << 4) | (1 << 2)
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.credit_ret_vc0.value = 0
    dut.credit_ret_vc1.value = 0

    for idx in range(4):
        dut.in_valid.value = 1
        dut.in_vc.value = 0
        dut.dst_x.value = 2
        dut.dst_y.value = 1
        dut.in_flit.value = 0x1000 + idx
        await RisingEdge(dut.clk)
        await ReadOnly()
        assert int(dut.out_valid.value) == (1 << 3)
        await FallingEdge(dut.clk)

    dut.in_valid.value = 1
    dut.in_vc.value = 0
    dut.dst_x.value = 2
    dut.dst_y.value = 1
    dut.in_flit.value = 0xDEAD0000
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.in_ready.value) == 0, "East VC0 should stall after 4 unreturned credits"
    assert int(dut.out_valid.value) == 0, "router emitted flit when out of credits"
    await FallingEdge(dut.clk)

    dut.in_vc.value = 1
    dut.in_flit.value = 0xBEEF0001
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.out_valid.value) == (1 << 3) and int(dut.out_vc.value) == 1 and int(dut.out_flit.value) == 0xBEEF0001
    await FallingEdge(dut.clk)

    dut.in_valid.value = 0
    dut.credit_ret_vc0.value = 1 << 3
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.credit_ret_vc0.value = 0
    dut.in_valid.value = 1
    dut.in_vc.value = 0
    dut.in_flit.value = 0xCAFE0001
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.out_valid.value) == (1 << 3) and int(dut.out_flit.value) == 0xCAFE0001


@cocotb.test()
async def d2d_replay_crc_and_gobackn(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.tx_valid.value = 0
    dut.tx_flit.value = 0
    dut.ack_valid.value = 0
    dut.nak_valid.value = 0
    dut.ack_seq.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.tx_ready.value) == 1 and int(dut.link_valid.value) == 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    payloads = [0x11223300 + i for i in range(6)]
    wire_log = []
    for word in payloads:
        dut.tx_valid.value = 1
        dut.tx_flit.value = word
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.link_valid.value):
            wire_log.append((int(dut.link_seq.value), int(dut.link_flit.value), int(dut.link_crc.value)))
        await FallingEdge(dut.clk)
    dut.tx_valid.value = 0
    for _ in range(3):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.link_valid.value):
            wire_log.append((int(dut.link_seq.value), int(dut.link_flit.value), int(dut.link_crc.value)))
        await FallingEdge(dut.clk)

    assert len(wire_log) == len(payloads), f"expected {len(payloads)} wire flits, got {len(wire_log)}"
    for seq, (got_seq, got_flit, got_crc) in enumerate(wire_log):
        want_crc = crc16_ccitt(payloads[seq].to_bytes(4, "big"))
        assert got_seq == seq and got_flit == payloads[seq] and got_crc == want_crc

    dut.nak_valid.value = 1
    dut.ack_seq.value = 2
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.link_valid.value) == 0, "link_valid must deassert on NAK rewind cycle"
    await FallingEdge(dut.clk)
    dut.nak_valid.value = 0

    replayed = []
    for _ in range(6):
        await RisingEdge(dut.clk)
        await ReadOnly()
        if int(dut.link_valid.value):
            replayed.append((int(dut.link_seq.value), int(dut.link_flit.value), int(dut.link_crc.value)))
        await FallingEdge(dut.clk)

    expected_replay = [(seq, payloads[seq], crc16_ccitt(payloads[seq].to_bytes(4, "big"))) for seq in range(2, 6)]
    assert replayed == expected_replay, f"Go-Back-N replay mismatch: got {replayed}, expected {expected_replay}"

    for extra in range(2):
        dut.tx_valid.value = 1
        dut.tx_flit.value = 0x55AA0000 + extra
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
    dut.tx_valid.value = 0
    await ReadOnly()
    assert int(dut.tx_ready.value) == 0, "8-slot replay buffer must deassert tx_ready when full"
    await FallingEdge(dut.clk)
    dut.ack_valid.value = 1
    dut.ack_seq.value = 5
    await RisingEdge(dut.clk)
    await FallingEdge(dut.clk)
    dut.ack_valid.value = 0
    for wrap_idx in range(2):
        dut.tx_valid.value = 1
        dut.tx_flit.value = 0x77000000 + wrap_idx
        await RisingEdge(dut.clk)
        await FallingEdge(dut.clk)
    dut.tx_valid.value = 0
    dut.ack_valid.value = 1
    dut.ack_seq.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.tx_ready.value) == 1, "wrap-around cumulative ACK across 7->0 must free all slots"


@cocotb.test()
async def mesi_dir_coherence_and_swmr(dut):
    cocotb.start_soon(Clock(dut.clk, 10, "ns").start())
    dut.req_valid.value = 0
    dut.req_we.value = 0
    dut.req_core.value = 0
    dut.req_addr.value = 0
    dut.req_wdata.value = 0
    dut.rst_n.value = 0
    await ClockCycles(dut.clk, 2)
    await ReadOnly()
    assert int(dut.resp_valid.value) == 0 and int(dut.inv_mask.value) == 0
    await FallingEdge(dut.clk)
    dut.rst_n.value = 1

    dut.req_valid.value = 1
    dut.req_we.value = 0
    dut.req_core.value = 0
    dut.req_addr.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.resp_valid.value) == 1 and int(dut.resp_state.value) == 2 and int(dut.sharer_vec.value) == 0b0001
    await FallingEdge(dut.clk)

    dut.req_core.value = 2
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.resp_valid.value) == 1 and int(dut.resp_state.value) == 1 and int(dut.sharer_vec.value) == 0b0101
    await FallingEdge(dut.clk)

    dut.req_we.value = 1
    dut.req_core.value = 3
    dut.req_wdata.value = 0xCAFEBABE
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.resp_valid.value) == 1 and int(dut.resp_state.value) == 3
    assert int(dut.inv_mask.value) == 0b0101, f"expected inv_mask 0b0101, got {int(dut.inv_mask.value):#06b}"
    assert int(dut.sharer_vec.value) == 0b1000, f"SWMR violation: sharer_vec={int(dut.sharer_vec.value):#06b} in Modified state"
    assert int(dut.resp_data.value) == 0xCAFEBABE
    await FallingEdge(dut.clk)

    dut.req_we.value = 0
    dut.req_core.value = 1
    await RisingEdge(dut.clk)
    await ReadOnly()
    assert int(dut.resp_valid.value) == 1 and int(dut.resp_state.value) == 1
    assert int(dut.sharer_vec.value) == 0b1010 and int(dut.resp_data.value) == 0xCAFEBABE


def test_xy_router_rtl():
    run("xy_router", [DESIGN / "xy_router.sv"], __file__, parameters={"MY_X": 1, "MY_Y": 1, "FLIT_W": 32, "CREDITS": 4}, defines={"COCOTB_TEST_FILTER": "xy_router_routing_and_credits"})


def test_d2d_replay_rtl():
    run("d2d_replay", [DESIGN / "d2d_replay.sv"], __file__, parameters={"FLIT_W": 32}, defines={"COCOTB_TEST_FILTER": "d2d_replay_crc_and_gobackn"})


def test_mesi_dir_rtl():
    run("mesi_dir", [DESIGN / "mesi_dir.sv"], __file__, parameters={"N_LINES": 4, "DATA_W": 32}, defines={"COCOTB_TEST_FILTER": "mesi_dir_coherence_and_swmr"})
