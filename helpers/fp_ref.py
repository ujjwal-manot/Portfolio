# Reference arithmetic for tensor_core: widens a BF16, FP8 E4M3, FP8 E5M2 or FP4 E2M1 code to the FP32 bits of the same value (always exact: FP32 holds every value of all four), and computes a fused FP32 multiply-add rounded once to nearest even with Berkeley SoftFloat's f32_mulAdd, and for OCP MX blocks the same with the product scaled by two shared E8M0 exponents (2^(xa + xb - 254), NaN if either is 255), done in FP64 rounded to odd and then rounded to FP32 at nearest even, which is the correctly rounded result since 53 >= 24 + 2 bits (Boldo and Melquiond); SoftFloat runs with RISC-V NaN rules (every NaN result is 0x7FC00000) and is loaded from the shared library tensor_core's make softfloat builds (or SOFTFLOAT).
import ctypes, os, struct
from pathlib import Path

BF16, E4M3, E5M2, E2M1 = 0, 1, 2, 3
NEAR_EVEN, ODD = 0, 6
LIBRARY = os.environ.get("SOFTFLOAT", str(Path(__file__).resolve().parent.parent / "projects/tensor_core/build/softfloat/softfloat.so"))

class F32(ctypes.Structure):
    _fields_ = [("v", ctypes.c_uint32)]

def widen(fmt, code):
    if fmt == BF16:
        return code << 16
    width, ebits, mbits, bias = {E4M3: (8, 4, 3, 7), E5M2: (8, 5, 2, 15), E2M1: (4, 2, 1, 1)}[fmt]
    s = code >> width - 1 & 1
    e, m = code >> mbits & (1 << ebits) - 1, code & (1 << mbits) - 1
    if fmt == E4M3 and (e, m) == (15, 7) or fmt == E5M2 and e == 31 and m:
        return 0x7FC00000
    if fmt == E5M2 and e == 31:
        return s << 31 | 0x7F800000
    if e == 0 and m == 0:
        return s << 31
    if e == 0:
        shift = mbits - m.bit_length() + 1
        e, m = 1 - shift, (m << shift) & (1 << mbits) - 1
    return s << 31 | (e - bias + 127) << 23 | m << (23 - mbits)

def f32_value(bits):
    return struct.unpack("<f", struct.pack("<I", bits))[0]

class F64(ctypes.Structure):
    _fields_ = [("v", ctypes.c_uint64)]

_library = None

def library():
    global _library
    if _library is None:
        _library = ctypes.CDLL(LIBRARY)
        _library.f32_mulAdd.restype, _library.f32_mulAdd.argtypes = F32, [F32, F32, F32]
        _library.f64_mulAdd.restype, _library.f64_mulAdd.argtypes = F64, [F64, F64, F64]
        _library.f32_to_f64.restype, _library.f32_to_f64.argtypes = F64, [F32]
        _library.f64_to_f32.restype, _library.f64_to_f32.argtypes = F32, [F64]
    return _library

def mul_add(a, b, c):
    return library().f32_mulAdd(F32(a), F32(b), F32(c)).v

def scaled_mul_add(fmt, a, b, xa, xb, c):
    sf = library()
    if xa == 255 or xb == 255:
        return 0x7FC00000
    wa = sf.f32_to_f64(F32(widen(fmt, a))).v
    if wa & 0x7FF0000000000000 not in (0, 0x7FF0000000000000):
        wa += xa + xb - 254 << 52
    mode = ctypes.c_uint8.in_dll(sf, "softfloat_roundingMode")
    mode.value = ODD
    total = sf.f64_mulAdd(F64(wa), sf.f32_to_f64(F32(widen(fmt, b))), sf.f32_to_f64(F32(c)))
    mode.value = NEAR_EVEN
    return sf.f64_to_f32(total).v
