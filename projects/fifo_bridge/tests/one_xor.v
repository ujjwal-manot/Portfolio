// One IHP xor2 cell, so test_sim_sdf.py can time a cell whose SDF arcs depend on the other input.
module one_xor (input A, B, output X);
  sg13g2_xor2_1 u (.A(A), .B(B), .X(X));
endmodule
