// Drives design/opamp_model.sv with the input waveform of a transistor run (wave.txt from tests/wave.cir: time, vin, time, vout) and writes the model's output every 0.1 ns to model.txt; the model's constants come from params.svh, written by helpers/opamp_model.py.
`timescale 1ps/1ps
`include "params.svh"
module opamp_model_tb;
  real vin, vout, t, v, t2, v2;
  integer fin, fout, n;
  opamp_model #(`OPAMP_MODEL) dut(.vin(vin), .vout(vout));
  initial begin
    fin = $fopen("wave.txt", "r");
    fout = $fopen("model.txt", "w");
    n = $fscanf(fin, "%e %e %e %e", t, v, t2, v2);
    vin = v;
    while (n == 4) begin
      #(t * 1e12 - $realtime);
      vin = v;
      n = $fscanf(fin, "%e %e %e %e", t, v, t2, v2);
    end
    $fclose(fout);
    $finish;
  end
  always #100 $fdisplay(fout, "%e %e", $realtime * 1e-12, vout);
endmodule
