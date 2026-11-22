// Synthesizable 4-core directory-based MESI cache coherence controller tracking I/S/E/M state, 4-bit sharer vector, and line data with single-writer-multiple-reader (SWMR) invalidation masks for projects/coherent_noc.
module mesi_dir #(
  parameter int N_LINES = 4,
  parameter int DATA_W  = 32
) (
  input  logic              clk,
  input  logic              rst_n,
  input  logic              req_valid,
  input  logic              req_we,
  input  logic [1:0]        req_core,
  input  logic [1:0]        req_addr,
  input  logic [DATA_W-1:0] req_wdata,
  output logic              resp_valid,
  output logic [1:0]        resp_state,
  output logic [3:0]        inv_mask,
  output logic [3:0]        sharer_vec,
  output logic [DATA_W-1:0] resp_data
);
  localparam logic [1:0] ST_I = 2'd0, ST_S = 2'd1, ST_E = 2'd2, ST_M = 2'd3;

  logic [1:0]        dir_state   [N_LINES];
  logic [3:0]        dir_sharers [N_LINES];
  logic [DATA_W-1:0] dir_data    [N_LINES];
  logic [3:0]        core_mask, other_sharers, next_sharers, write_sharers;
  logic [1:0]        next_read_state;

  assign core_mask       = 4'b0001 << req_core;
  assign other_sharers   = dir_sharers[req_addr] & ~core_mask;
  assign next_sharers    = dir_sharers[req_addr] | core_mask;
  assign write_sharers   = core_mask;
  assign next_read_state = (other_sharers != 4'b0000) ? ST_S : ((dir_state[req_addr] == ST_M) ? ST_M : ST_E);

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      resp_valid <= 1'b0;
      resp_state <= ST_I;
      inv_mask   <= 4'b0000;
      sharer_vec <= 4'b0000;
      resp_data  <= '0;
      for (int i = 0; i < N_LINES; i++) begin
        dir_state[i]   <= ST_I;
        dir_sharers[i] <= 4'b0000;
        dir_data[i]    <= '0;
      end
    end else begin
      resp_valid <= 1'b0;
      inv_mask   <= 4'b0000;
      if (req_valid) begin
        if (req_we) begin
          dir_state[req_addr]   <= ST_M;
          dir_sharers[req_addr] <= write_sharers;
          dir_data[req_addr]    <= req_wdata;
          resp_valid            <= 1'b1;
          resp_state            <= ST_M;
          inv_mask              <= other_sharers;
          sharer_vec            <= write_sharers;
          resp_data             <= req_wdata;
        end else begin
          dir_state[req_addr]   <= next_read_state;
          dir_sharers[req_addr] <= next_sharers;
          resp_valid            <= 1'b1;
          resp_state            <= next_read_state;
          inv_mask              <= 4'b0000;
          sharer_vec            <= next_sharers;
          resp_data             <= dir_data[req_addr];
        end
      end
    end
  end
endmodule
