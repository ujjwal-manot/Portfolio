// Formal verification harnesses for Cummings SNUG-2002 Rev 1.3 async FIFO (fifo1, wptr_full, rptr_empty): proves no overflow or underflow, exact in-order data delivery on arbitrary picked words, and single-bit Gray pointer steps.
module cummings_formal #(
  parameter int A = 2,
  parameter int D = 8
) (
  input logic         wclk, rclk, winc, rinc,
  input logic [D-1:0] wdata
);
  logic         wfull, rempty, wrst_n = 0, rrst_n = 0;
  logic [D-1:0] rdata, kept;
  logic [A+1:0] writes = 0, reads = 0;
  (* anyconst *) logic [A+1:0] pick;
  wire  [A+1:0] level = writes - reads;

  fifo1 #(.DSIZE(D), .ASIZE(A)) dut (
    .rdata (rdata),
    .wfull (wfull),
    .rempty(rempty),
    .wdata (wdata),
    .winc  (winc),
    .wclk  (wclk),
    .wrst_n(wrst_n),
    .rinc  (rinc),
    .rclk  (rclk),
    .rrst_n(rrst_n)
  );

  always_ff @(posedge wclk) begin
    wrst_n <= 1'b1;
    if (wrst_n && winc && !wfull) begin
      writes <= writes + 1;
      if (writes == pick) kept <= wdata;
    end
  end

  always_ff @(posedge rclk) begin
    rrst_n <= 1'b1;
    if (rrst_n && rinc && !rempty) begin
      reads <= reads + 1;
      if (reads == pick) begin
        assert (rdata == kept);
        cover (pick == 5);
      end
    end
  end

  always_comb begin
    assert (level <= 2**A);
    if (level == 2**A) assert (wfull);
    if (level == 0) assert (rempty);
    cover (level == 2**A && reads > 2);
    cover (level == 0 && reads > 0);
  end
endmodule

module gray_ptr_rules #(
  parameter int A = 2
) (
  input logic       wclk, rclk, winc, rinc,
  input logic [A:0] wq2_rptr, rq2_wptr
);
  logic       wrst_n = 0, rrst_n = 0;
  logic       wfull, rempty;
  logic [A-1:0] waddr, raddr;
  logic [A:0] wptr, rptr, wptr_was = 0, rptr_was = 0;
  wire  [A:0] wdiff = wptr ^ wptr_was;
  wire  [A:0] rdiff = rptr ^ rptr_was;

  wptr_full #(.ADDRSIZE(A)) u_wptr (
    .wfull   (wfull),
    .waddr   (waddr),
    .wptr    (wptr),
    .wq2_rptr(wq2_rptr),
    .winc    (winc),
    .wclk    (wclk),
    .wrst_n  (wrst_n)
  );

  rptr_empty #(.ADDRSIZE(A)) u_rptr (
    .rempty  (rempty),
    .raddr   (raddr),
    .rptr    (rptr),
    .rq2_wptr(rq2_wptr),
    .rinc    (rinc),
    .rclk    (rclk),
    .rrst_n  (rrst_n)
  );

  always_ff @(posedge wclk) begin
    wrst_n   <= 1'b1;
    wptr_was <= wptr;
    assert ((wdiff & (wdiff - 1)) == 0);
  end

  always_ff @(posedge rclk) begin
    rrst_n   <= 1'b1;
    rptr_was <= rptr;
    assert ((rdiff & (rdiff - 1)) == 0);
  end
endmodule
