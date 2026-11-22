# Checks Cummings SNUG-2002 Rev 1.3 Gray-code 2-MSB full condition vs the broken 1-MSB inversion across all 32 pointer pairs (ASIZE=4) and confirms all six paper Verilog modules are present.
from pathlib import Path

def to_gray(val):
    return (val >> 1) ^ val

def test_cummings_two_msb_full_check_exact_and_one_msb_breaks():
    asize = 4
    depth = 1 << asize
    mask = (1 << (asize + 1)) - 1
    top2 = 0b11 << (asize - 1)
    top1 = 0b1 << asize
    for rbin in range(2 * depth):
        rgray = to_gray(rbin)
        for delta in range(2 * depth):
            wbin = (rbin + delta) & mask
            wgray = to_gray(wbin)
            is_full = (delta == depth)
            cummings_full = (wgray == (rgray ^ top2))
            assert cummings_full == is_full
    broken_matches = sum(1 for rbin in range(2 * depth) if to_gray((rbin + depth) & mask) == (to_gray(rbin) ^ top1))
    assert broken_matches == 0

def test_all_six_cummings_modules_exist():
    here = Path(__file__).resolve().parent
    for name in ("fifo1.v", "fifomem.v", "sync_r2w.v", "sync_w2r.v", "rptr_empty.v", "wptr_full.v"):
        assert (here / name).is_file()
