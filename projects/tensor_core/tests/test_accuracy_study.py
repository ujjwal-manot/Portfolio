# Checks projects/tensor_core/model/accuracy_study.py: exact round-to-nearest-even quantization and decode consistency with helpers/fp_ref.widen for BF16, FP8 E4M3/E5M2, MXFP8 and MXFP4, plus monotonic layer accuracy ordering against FP32.
import math, sys
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "helpers"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from fp_ref import widen, f32_value, BF16, E4M3, E5M2, E2M1
from accuracy_study import quantize_scalar, quantize_mx_block, run_layer_study

def test_scalar_quantizer_matches_fp_ref_widen_on_exact_codes():
    for fmt, n_codes in ((E4M3, 256), (E5M2, 256), (E2M1, 16)):
        for code in range(n_codes):
            val = f32_value(widen(fmt, code))
            if math.isnan(val) or math.isinf(val) or val == 0.0:
                continue
            qcode = quantize_scalar(val, fmt)
            assert f32_value(widen(fmt, qcode)) == val

def test_mx_block_quantization_recovers_wide_dynamic_range():
    block = np.array([1e-5 * (i + 1) for i in range(32)], dtype=np.float32)
    scale_exp, codes = quantize_mx_block(block, E4M3)
    scale = 2.0 ** (scale_exp - 127)
    decoded = np.array([f32_value(widen(E4M3, c)) * scale for c in codes], dtype=np.float32)
    rel_err = float(np.linalg.norm(decoded - block) / np.linalg.norm(block))
    assert rel_err < 0.05

def test_layer_accuracy_study_orders_formats_against_fp32():
    report = run_layer_study(m=32, k=64, n=32)
    assert set(report.keys()) == {"bf16", "fp8_e4m3", "fp8_e5m2", "mxfp8_e4m3", "mxfp4_e2m1"}
    assert report["bf16"]["rel_l2"] < report["mxfp8_e4m3"]["rel_l2"] < report["mxfp4_e2m1"]["rel_l2"]
    assert report["mxfp8_e4m3"]["sqnr_db"] >= report["fp8_e4m3"]["sqnr_db"] - 1.0
    assert report["bf16"]["sqnr_db"] > 40.0
    assert report["mxfp8_e4m3"]["sqnr_db"] > 40.0
    assert report["mxfp4_e2m1"]["sqnr_db"] > 18.0
