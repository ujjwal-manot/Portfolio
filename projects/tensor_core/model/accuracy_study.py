# Evaluates deterministic neural-network layer GEMM accuracy of BF16, FP8 E4M3, FP8 E5M2, MXFP8-E4M3, and MXFP4-E2M1 against FP32 using helpers/fp_ref.widen: python3 accuracy_study.py.
import math, struct, sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "helpers"))
from fp_ref import widen, f32_value, BF16, E4M3, E5M2, E2M1

MAX_EXP = {E4M3: 8, E5M2: 15, E2M1: 2}
CODE_COUNT = {E4M3: 256, E5M2: 256, E2M1: 16}

def _build_codebook(fmt):
    pairs = []
    for code in range(CODE_COUNT[fmt]):
        val = f32_value(widen(fmt, code))
        if not (math.isnan(val) or math.isinf(val)):
            pairs.append((val, code))
    pairs.sort(key=lambda item: (item[0], item[1] & 1, item[1]))
    vals = np.array([p[0] for p in pairs], dtype=np.float64)
    codes = np.array([p[1] for p in pairs], dtype=np.int32)
    return vals, codes

_BOOKS = {fmt: _build_codebook(fmt) for fmt in (E4M3, E5M2, E2M1)}

def quantize_scalar(val, fmt):
    x = float(val)
    if fmt == BF16:
        if math.isnan(x):
            return 0x7FC0
        u32 = struct.unpack("<I", struct.pack("<f", np.float32(x)))[0]
        if (u32 & 0x7FFFFFFF) >= 0x7F800000:
            return (u32 >> 16) & 0xFFFF
        lsb = (u32 >> 16) & 1
        return ((u32 + 0x7FFF + lsb) >> 16) & 0xFFFF
    vals, codes = _BOOKS[fmt]
    idx = int(np.searchsorted(vals, x))
    if idx <= 0:
        return int(codes[0])
    if idx >= len(vals):
        return int(codes[-1])
    d_lo = abs(x - vals[idx - 1])
    d_hi = abs(vals[idx] - x)
    if d_lo < d_hi:
        return int(codes[idx - 1])
    if d_hi < d_lo:
        return int(codes[idx])
    return int(codes[idx - 1] if (codes[idx - 1] & 1) == 0 else codes[idx])

def quantize_mx_block(block, fmt):
    arr = np.asarray(block, dtype=np.float64)
    amax = float(np.max(np.abs(arr)))
    vals, _ = _BOOKS[fmt]
    max_fin = float(vals[-1])
    if amax == 0.0:
        scale_exp = 127
    else:
        e_max = int(math.floor(math.log2(amax)))
        scale_exp = 127 + e_max - MAX_EXP[fmt]
        if amax > max_fin * (2.0 ** (scale_exp - 127)):
            scale_exp += 1
        scale_exp = max(0, min(254, scale_exp))
    scale = 2.0 ** (scale_exp - 127)
    codes = [quantize_scalar(v / scale, fmt) for v in arr]
    return scale_exp, codes

def _dequant_matrix(mat, fmt, mx=False):
    m, k = mat.shape
    out = np.zeros((m, k), dtype=np.float32)
    if not mx:
        for i in range(m):
            for j in range(k):
                out[i, j] = np.float32(f32_value(widen(fmt, quantize_scalar(mat[i, j], fmt))))
        return out
    for i in range(m):
        for b0 in range(0, k, 32):
            blk = mat[i, b0:b0 + 32]
            sexp, codes = quantize_mx_block(blk, fmt)
            scale = np.float32(2.0 ** (sexp - 127))
            for off, code in enumerate(codes):
                out[i, b0 + off] = np.float32(f32_value(widen(fmt, code))) * scale
    return out

def run_layer_study(m=32, k=64, n=32):
    ii = np.arange(m, dtype=np.float64)[:, None]
    kk = np.arange(k, dtype=np.float64)[None, :]
    jj = np.arange(n, dtype=np.float64)[None, :]
    a_fp32 = (np.sin(0.37 * ii + 0.19 * kk) * (0.25 + 1.5 * ((ii % 4) / 3.0))).astype(np.float32)
    b_fp32 = (np.cos(0.23 * kk.T - 0.41 * jj) * (0.1 + 0.8 * ((jj % 5) / 4.0))).astype(np.float32)
    ref = (a_fp32.astype(np.float64) @ b_fp32.astype(np.float64)).astype(np.float32)
    ref_norm = float(np.linalg.norm(ref))
    configs = [
        ("bf16", BF16, False),
        ("fp8_e4m3", E4M3, False),
        ("fp8_e5m2", E5M2, False),
        ("mxfp8_e4m3", E4M3, True),
        ("mxfp4_e2m1", E2M1, True),
    ]
    results = {}
    for name, fmt, mx in configs:
        qa = _dequant_matrix(a_fp32, fmt, mx=mx)
        qb = _dequant_matrix(b_fp32.T, fmt, mx=mx).T
        got = (qa.astype(np.float64) @ qb.astype(np.float64)).astype(np.float32)
        diff = got.astype(np.float64) - ref.astype(np.float64)
        err_norm = float(np.linalg.norm(diff))
        rel_l2 = err_norm / ref_norm
        sqnr_db = 20.0 * math.log10(ref_norm / err_norm) if err_norm > 0.0 else float("inf")
        results[name] = {
            "rmse": float(np.sqrt(np.mean(diff ** 2))),
            "max_abs": float(np.max(np.abs(diff))),
            "rel_l2": rel_l2,
            "sqnr_db": sqnr_db,
        }
    return results

if __name__ == "__main__":
    for name, stats in run_layer_study().items():
        print(f"{name:11s} rmse={stats['rmse']:.5f} rel_l2={stats['rel_l2']:.5f} max_abs={stats['max_abs']:.5f} sqnr_db={stats['sqnr_db']:.2f}")
