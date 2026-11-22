// Read pointer and empty generation matching Cummings SNUG-2002 Rev 1.3 Section 5.5 (rptr_empty).
module rptr_empty #(
  parameter ADDRSIZE = 4
) (
  output reg                rempty,
  output     [ADDRSIZE-1:0] raddr,
  output reg [ADDRSIZE:0]   rptr,
  input      [ADDRSIZE:0]   rq2_wptr,
  input                     rinc, rclk, rrst_n
);
  reg  [ADDRSIZE:0] rbin;
  wire [ADDRSIZE:0] rgraynext, rbinnext;
  wire              rempty_val;

  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) {rbin, rptr} <= 0;
    else         {rbin, rptr} <= {rbinnext, rgraynext};

  assign raddr      = rbin[ADDRSIZE-1:0];
  assign rbinnext   = rbin + (rinc & ~rempty);
  assign rgraynext  = (rbinnext >> 1) ^ rbinnext;
  assign rempty_val = (rgraynext == rq2_wptr);

  always @(posedge rclk or negedge rrst_n)
    if (!rrst_n) rempty <= 1'b1;
    else         rempty <= rempty_val;
endmodule
