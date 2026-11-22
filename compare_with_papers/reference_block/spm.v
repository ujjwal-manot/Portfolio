// LibreLane 32-bit serial-parallel multiplier reference block (spm, tcmp, csadd, scadd) for IHP SG13G2 cells, area, and fmax comparison (plan.md line 279).
module spm #(
  parameter int SIZE = 32
) (
  input  wire            clk,
  input  wire            rst,
  input  wire            x,
  input  wire [SIZE-1:0] a,
  output wire            y
);
  wire [SIZE-1:1] pp;
  wire [SIZE-1:0] xy;

  genvar i;
  generate
    for (i = 0; i < SIZE; i = i + 1) begin : gen_xy
      assign xy[i] = a[i] & x;
    end
    for (i = 1; i < SIZE - 1; i = i + 1) begin : gen_csa
      csadd u_csa (.clk(clk), .rst(rst), .x(xy[i]), .y(pp[i+1]), .sum(pp[i]));
    end
  endgenerate

  tcmp u_tcmp (.clk(clk), .rst(rst), .a(xy[SIZE-1]), .s(pp[SIZE-1]));
  csadd u_csa0 (.clk(clk), .rst(rst), .x(xy[0]), .y(pp[1]), .sum(y));
endmodule

module tcmp (
  input  wire clk,
  input  wire rst,
  input  wire a,
  output reg  s
);
  reg z;
  always @(posedge clk or posedge rst) begin
    if (rst) begin
      s <= 1'b0;
      z <= 1'b0;
    end else begin
      z <= a | z;
      s <= a ^ z;
    end
  end
endmodule

module csadd (
  input  wire clk,
  input  wire rst,
  input  wire x,
  input  wire y,
  output reg  sum
);
  reg sc;
  wire hsum1, hco1, hco2;
  assign hsum1 = y ^ sc;
  assign hco1  = y & sc;
  assign hco2  = x & hsum1;

  always @(posedge clk or posedge rst) begin
    if (rst) begin
      sum <= 1'b0;
      sc  <= 1'b0;
    end else begin
      sum <= x ^ hsum1;
      sc  <= hco1 ^ hco2;
    end
  end
endmodule

module scadd (
  input  wire clk,
  input  wire rst,
  input  wire x,
  input  wire y,
  output reg  y_out
);
  reg c;
  always @(posedge clk or posedge rst) begin
    if (rst) begin
      y_out <= 1'b0;
      c     <= 1'b0;
    end else begin
      y_out <= x ^ y ^ c;
      c     <= (x & y) | (c & (x ^ y));
    end
  end
endmodule
