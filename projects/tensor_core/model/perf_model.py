# Exact cycle, utilization, dataflow (OS vs WS), and roofline performance model for projects/tensor_core/design/tensor_core.sv: python3 perf_model.py.
import math

ELEM_BYTES = {
    "bf16": 2.0,
    "fp8": 1.0,
    "mxfp8": 1.0 + 1.0 / 32.0,
    "mxfp4": 0.5 + 1.0 / 32.0,
}

def _ceil_mult(val, step):
    return ((val + step - 1) // step) * step

def conv2d_gemm_shape(batch, h_out, w_out, c_in, kh, kw, c_out):
    return (batch * h_out * w_out, c_in * kh * kw, c_out)

def gemm_cycles(m, k, n, ws=0, array_n=8):
    if m <= 0 or k <= 0 or n <= 0 or array_n <= 0:
        raise ValueError("m, k, n, and array_n must be positive")
    if ws not in (0, 1):
        raise ValueError(f"ws must be 0 (OS) or 1 (WS), got {ws}")
    mp = _ceil_mult(m, array_n)
    kp = _ceil_mult(k, array_n)
    np_ = _ceil_mult(n, array_n)
    if ws == 0:
        tiles = (mp // array_n) * (np_ // array_n)
        per_tile = kp + 4 * array_n - 2
    else:
        tiles = (kp // array_n) * (np_ // array_n)
        per_tile = mp + 3 * array_n - 1
    return tiles * per_tile

def workload_metrics(m, k, n, ws=0, fmt="fp8", array_n=8):
    if fmt not in ELEM_BYTES:
        raise ValueError(f"unknown format {fmt}")
    cycles = gemm_cycles(m, k, n, ws=ws, array_n=array_n)
    macs = m * k * n
    flops = 2 * macs
    eb = ELEM_BYTES[fmt]
    bytes_total = (m * k + k * n) * eb + (2.0 * m * n * 4.0)
    return {
        "ws": ws,
        "fmt": fmt,
        "cycles": cycles,
        "flops": flops,
        "utilization": macs / (cycles * array_n * array_n),
        "bytes": bytes_total,
        "arithmetic_intensity": flops / bytes_total,
    }

def roofline_point(m, k, n, ws=0, fmt="fp8", freq_ghz=0.2, bw_gb_s=8.0, array_n=8):
    w = workload_metrics(m, k, n, ws=ws, fmt=fmt, array_n=array_n)
    peak_gflops = 2.0 * array_n * array_n * freq_ghz
    mem_cap = w["arithmetic_intensity"] * bw_gb_s
    attainable = min(peak_gflops, mem_cap)
    achieved = peak_gflops * w["utilization"]
    return {
        **w,
        "peak_gflops": peak_gflops,
        "attainable_gflops": attainable,
        "achieved_gflops": achieved,
        "bound": "memory" if mem_cap < peak_gflops else "compute",
    }

if __name__ == "__main__":
    conv = conv2d_gemm_shape(1, 56, 56, 64, 3, 3, 64)
    for name, shape in [("resnet18_conv3x3", conv), ("mlp_gemm", (64, 256, 256)), ("skinny_k", (16, 512, 64))]:
        for ws in (0, 1):
            r = roofline_point(*shape, ws=ws, fmt="fp8")
            print(f"{name} ws={ws} cycles={r['cycles']} util={r['utilization']:.4f} ai={r['arithmetic_intensity']:.2f} {r['bound']}")
