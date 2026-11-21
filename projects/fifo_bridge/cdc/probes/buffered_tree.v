// A clean two-flop synchronizer as layout leaves it: each clock reaches its flops through clock buffers, a repair buffer sits between the source flop and the first synchronizer flop, and an output buffer between the last flop and the q port.
module buffered_tree (input a_clk, b_clk, d, output q);
  wire a_leaf, b_root, b_leaf, src, src_buf, meta, one;
  sg13g2_tiehi t (.L_HI(one));
  sg13g2_buf_16 ra (.A(a_clk), .X(a_leaf));
  sg13g2_buf_16 rb (.A(b_clk), .X(b_root));
  sg13g2_buf_8 lb (.A(b_root), .X(b_leaf));
  sg13g2_dfrbpq_1 f_src (.CLK(a_leaf), .RESET_B(one), .D(d), .Q(src));
  sg13g2_buf_1 rep (.A(src), .X(src_buf));
  sg13g2_dfrbpq_1 f_meta (.CLK(b_root), .RESET_B(one), .D(src_buf), .Q(meta));
  wire net7;
  sg13g2_dfrbpq_1 f_q (.CLK(b_leaf), .RESET_B(one), .D(meta), .Q(net7));
  sg13g2_buf_2 out (.A(net7), .X(q));
endmodule
