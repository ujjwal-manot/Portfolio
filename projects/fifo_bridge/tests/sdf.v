// Annotates the cell netlist whose top module the TOP define names with the delays in the SDF file named by the SDF define, for the timed gate-level simulations.
module sdf;
  initial $sdf_annotate(`SDF, `TOP);
endmodule
