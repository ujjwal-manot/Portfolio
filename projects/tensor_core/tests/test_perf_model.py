# Checks projects/tensor_core/model/perf_model.py: zero-error cycle match against all 12 measured Verilator GEMMs in results/test_array.log, conv2d im2col mapping, OS vs WS dataflow crossover, and roofline utilization bounds.
import re, sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "model"))
from perf_model import gemm_cycles, workload_metrics, conv2d_gemm_shape, roofline_point

def test_matches_all_twelve_measured_verilator_cycles_exactly():
    log = Path(__file__).resolve().parents[1] / "results" / "test_array.log"
    rows = re.findall(r"WS=(\d+)\s+format\s+\d+\s+mx\s+\d+\s+M\s+(\d+)\s+K\s+(\d+)\s+N\s+(\d+):\s+(\d+)\s+cycles", log.read_text(encoding="utf-8"))
    assert len(rows) == 12
    for ws, m, k, n, cycles in rows:
        pred = gemm_cycles(int(m), int(k), int(n), ws=int(ws), array_n=8)
        assert pred == int(cycles)

def test_dataflow_crossover_ws_wins_large_m_os_wins_large_k():
    conv_m, conv_k, conv_n = conv2d_gemm_shape(batch=1, h_out=56, w_out=56, c_in=64, kh=3, kw=3, c_out=64)
    assert (conv_m, conv_k, conv_n) == (3136, 576, 64)
    os_conv = workload_metrics(conv_m, conv_k, conv_n, ws=0, fmt="fp8")
    ws_conv = workload_metrics(conv_m, conv_k, conv_n, ws=1, fmt="fp8")
    assert ws_conv["cycles"] < os_conv["cycles"]
    assert ws_conv["utilization"] > os_conv["utilization"] > 0.9

    skinny_os = workload_metrics(16, 512, 64, ws=0, fmt="bf16")
    skinny_ws = workload_metrics(16, 512, 64, ws=1, fmt="bf16")
    assert skinny_os["cycles"] < skinny_ws["cycles"]
    assert skinny_os["utilization"] > skinny_ws["utilization"]

def test_roofline_compute_vs_memory_bound_regimes():
    pt_mem = roofline_point(16, 16, 16, ws=0, fmt="bf16", freq_ghz=0.2, bw_gb_s=1.0)
    pt_cmp = roofline_point(256, 256, 256, ws=1, fmt="mxfp4", freq_ghz=0.2, bw_gb_s=32.0)
    assert pt_mem["bound"] == "memory" and pt_mem["attainable_gflops"] < pt_mem["peak_gflops"]
    assert pt_cmp["bound"] == "compute" and abs(pt_cmp["attainable_gflops"] - pt_cmp["peak_gflops"]) < 1e-6
    assert pt_cmp["achieved_gflops"] <= pt_cmp["attainable_gflops"] + 1e-6
