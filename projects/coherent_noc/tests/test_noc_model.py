# Checks projects/coherent_noc/model/noc_model.py: 2x2 XY dimension-order routing without deadlock, 4-core directory MESI SWMR and data-value invariants vs missed invalidate, and CRC-16-CCITT die-to-die go-back-N replay under bit flips vs skipped flit.
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from noc_model import xy_route_path, simulate_mesh, MesiDirectory, crc16_ccitt, d2d_transfer

def test_xy_routing_moves_x_then_y_and_mesh_drains_all_patterns():
    assert xy_route_path((0, 0), (1, 1)) == [(0, 0), (1, 0), (1, 1)]
    assert xy_route_path((1, 1), (0, 0)) == [(1, 1), (0, 1), (0, 0)]
    for pattern in ("uniform", "hotspot", "transpose"):
        stats = simulate_mesh(pattern=pattern, n_packets=64, credits=4)
        assert stats["delivered"] == 64
        assert stats["max_occupancy"] <= 4
        assert stats["deadlocked"] is False

def test_early_credit_return_causes_buffer_overflow():
    stats = simulate_mesh(pattern="hotspot", n_packets=64, credits=2, early_credit=True)
    assert stats["overflows"] > 0

def test_mesi_directory_enforces_swmr_and_missed_invalidate_breaks_coherence():
    clean = MesiDirectory(n_cores=4, miss_invalidate=False)
    broken = MesiDirectory(n_cores=4, miss_invalidate=True)
    ops = []
    for step in range(200):
        core = (step * 3 + 1) % 4
        addr = (step // 5) % 4
        if step % 3 == 0:
            ops.append(("W", core, addr, 1000 + step))
        else:
            ops.append(("R", core, addr, 0))
    for op, core, addr, val in ops:
        if op == "W":
            clean.write(core, addr, val)
            broken.write(core, addr, val)
        else:
            assert clean.read(core, addr) == clean.oracle[addr]
            assert clean.check_swmr(addr)
    stale_reads = sum(1 for addr in range(4) for c in range(4) if broken.read(c, addr) != broken.oracle[addr])
    swmr_bad = any(not broken.check_swmr(addr) for addr in range(4))
    assert stale_reads > 0 or swmr_bad

def test_d2d_crc16_replay_delivers_exact_flits_and_skip_bug_drops_flit():
    assert crc16_ccitt(b"123456789") == 0x29B1
    flits = [0xA000 + i for i in range(40)]
    rx_ok = d2d_transfer(flits, corrupt_indices={5, 17, 18, 31}, skip_on_replay=False)
    assert rx_ok["received"] == flits
    assert rx_ok["replays"] >= 3
    rx_bad = d2d_transfer(flits, corrupt_indices={5, 17}, skip_on_replay=True)
    assert rx_bad["received"] != flits
