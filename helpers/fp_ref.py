# Reference arithmetic for tensor_core: widens a BF16, FP8 E4M3 or FP8 E5M2 code to the FP32 bits of the same value (always exact: FP32 holds every value of all three), and computes a fused FP32 multiply-add rounded once to nearest even with Berkeley SoftFloat's f32_mulAdd (RISC-V NaN rules, so every NaN result is 0x7FC00000), loaded from the shared library tensor_core's make softfloat builds (or SOFTFLOAT).
import ctypes, os, struct
from pathlib import Path

BF16, E4M3, E5M2 = 0, 1, 2
LIBRARY = os.environ.get("SOFTFLOAT", str(Path(__file__).resolve().parent.parent / "projects/tensor_core/build/softfloat/softfloat.so"))

class F32(ctypes.Structure):
    _fields_ = [("v", ctypes.c_uint32)]

def widen(fmt, code):
    if fmt == BF16:
        return code << 16
    s, (ebits, mbits, bias) = code >> 7 & 1, {E4M3: (4, 3, 7), E5M2: (5, 2, 15)}[fmt]
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

_library = None

def mul_add(a, b, c):
    global _library
    if _library is None:
        _library = ctypes.CDLL(LIBRARY)
        _library.f32_mulAdd.restype, _library.f32_mulAdd.argtypes = F32, [F32, F32, F32]
    return _library.f32_mulAdd(F32(a), F32(b), F32(c)).v
