// Annotates the fifo_bridge cell netlist with the delays in the SDF file named by the SDF define, for the timed gate-level simulation.
module sdf;
  initial $sdf_annotate(`SDF, fifo_bridge);
endmodule
