// Fused multiply-add for the tensor core's cells: y = a * b + c rounded once to nearest even in FP32, with a and b in BF16, FP8 E4M3 or FP8 E5M2 (fmt 0, 1, 2; FP8 in the low byte) and c in FP32; both operands are normalized to a 24-bit significand first, so aligning the smaller one with a guard, a round and a sticky bit is exact under cancellation; subnormals in and out, infinities, and RISC-V NaN rules (every NaN result is 0x7FC00000).
module fma (
  input  logic [1:0]  fmt,
  input  logic [15:0] a, b,
  input  logic [31:0] c,
  output logic [31:0] y
);
  typedef struct packed {
    logic s, zero, inf, nan;
    logic signed [11:0] e;
    logic [23:0] m;
  } num_t;

  function automatic num_t narrow(input logic [1:0] f, input logic [15:0] x);
    num_t n = '0;
    case (f)
      2'd0: begin
        n.s = x[15]; n.zero = x[14:0] == 0; n.inf = x[14:7] == 8'hff && x[6:0] == 0; n.nan = x[14:7] == 8'hff && x[6:0] != 0;
        n.m = {16'b0, x[14:7] != 0, x[6:0]}; n.e = (x[14:7] == 0 ? 12'sd1 : $signed({4'b0, x[14:7]})) - 12'sd134;
      end
      2'd1: begin
        n.s = x[7]; n.zero = x[6:0] == 0; n.nan = x[6:0] == 7'h7f;
        n.m = {20'b0, x[6:3] != 0, x[2:0]}; n.e = (x[6:3] == 0 ? 12'sd1 : $signed({8'b0, x[6:3]})) - 12'sd10;
      end
      default: begin
        n.s = x[7]; n.zero = x[6:0] == 0; n.inf = x[6:2] == 5'h1f && x[1:0] == 0; n.nan = x[6:2] == 5'h1f && x[1:0] != 0;
        n.m = {21'b0, x[6:2] != 0, x[1:0]}; n.e = (x[6:2] == 0 ? 12'sd1 : $signed({7'b0, x[6:2]})) - 12'sd17;
      end
    endcase
    return n;
  endfunction

  function automatic num_t normalize(input num_t n);
    if (n.m == 0) begin
      n.e = -12'sd1024;
      return n;
    end
    while (!n.m[23]) begin
      n.m = n.m << 1;
      n.e = n.e - 1;
    end
    return n;
  endfunction

  function automatic logic [26:0] shift_sticky(input logic [26:0] x, input int unsigned d);
    logic [26:0] kept, lost;
    if (d >= 27) return {26'b0, |x};
    kept = x >> d;
    lost = x & ((27'd1 << d) - 1);
    return kept | {26'b0, |lost};
  endfunction

  always_comb begin
    num_t pa, pb, p, q, major, minor;
    logic [26:0] wide, aligned;
    logic [27:0] sum;
    logic [24:0] rounded;
    logic signed [11:0] eb;
    logic sub;
    pa = narrow(fmt, a);
    pb = narrow(fmt, b);
    q = '0;
    q.s = c[31]; q.zero = c[30:0] == 0; q.inf = c[30:23] == 8'hff && c[22:0] == 0; q.nan = c[30:23] == 8'hff && c[22:0] != 0;
    q.m = {c[30:23] != 0, c[22:0]}; q.e = (c[30:23] == 0 ? 12'sd1 : $signed({4'b0, c[30:23]})) - 12'sd150;
    p = '0;
    p.s = pa.s ^ pb.s; p.zero = pa.zero || pb.zero; p.inf = pa.inf || pb.inf;
    p.nan = pa.nan || pb.nan || p.inf && p.zero;
    p.m = {16'(pa.m[7:0]) * 16'(pb.m[7:0]), 8'b0}; p.e = pa.e + pb.e - 12'sd8;
    {major, minor, wide, aligned, sum, rounded, eb, sub} = '0;
    y = 32'h7fc00000;
    if (p.nan || q.nan || p.inf && q.inf && p.s != q.s) y = 32'h7fc00000;
    else if (p.inf) y = {p.s, 8'hff, 23'b0};
    else if (q.inf) y = c;
    else if (p.zero) y = q.zero ? {p.s && q.s, 31'b0} : c;
    else begin
      p = normalize(p);
      q = normalize(q);
      if (p.e > q.e || p.e == q.e && p.m >= q.m) {major, minor} = {p, q};
      else {major, minor} = {q, p};
      aligned = shift_sticky({minor.m, 3'b0}, int'(unsigned'(major.e - minor.e)));
      sub = major.s != minor.s;
      sum = sub ? {1'b0, major.m, 3'b0} - {1'b0, aligned} : {1'b0, major.m, 3'b0} + {1'b0, aligned};
      eb = major.e + 12'sd150;
      if (sum == 0) y = 32'b0;
      else begin
        if (sum[27]) begin
          wide = sum[27:1] | {26'b0, sum[0]};
          eb = eb + 1;
        end else begin
          wide = sum[26:0];
          while (!wide[26]) begin
            wide = wide << 1;
            eb = eb - 1;
          end
        end
        if (eb < 1) begin
          wide = shift_sticky(wide, int'(unsigned'(12'sd1 - eb)));
          eb = 1;
        end
        rounded = {1'b0, wide[26:3]} + {24'b0, wide[2] && (wide[1] || wide[0] || wide[3])};
        if (rounded[24]) begin
          rounded = rounded >> 1;
          eb = eb + 1;
        end
        if (eb >= 255) y = {major.s, 8'hff, 23'b0};
        else y = {major.s, rounded[23] ? eb[7:0] : 8'b0, rounded[22:0]};
      end
    end
  end
endmodule
