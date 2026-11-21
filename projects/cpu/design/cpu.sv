// RV32I core, 5 stages (IF ID EX MEM WB): forwarding, one-cycle load-use stall, 2-bit predictor with a 16-entry BTB, stream and counters at 0x1000_0000.
module cpu (
  input  logic        clk, rst_n,
  output logic [31:0] imem_addr,
  input  logic [31:0] imem_data,
  output logic [31:0] dmem_addr, dmem_wdata,
  output logic [3:0]  dmem_wstrb,
  output logic        dmem_read,
  input  logic [31:0] dmem_rdata,
  input  logic        s_tvalid,
  output logic        s_tready,
  input  logic [7:0]  s_tdata,
  input  logic        s_tlast,
  output logic        retire_valid,
  output logic [31:0] retire_pc, retire_instr, retire_rd_data,
  output logic [4:0]  retire_rd
);
  localparam logic [6:0] LUI = 7'h37, AUIPC = 7'h17, JAL = 7'h6f, JALR = 7'h67, BRANCH = 7'h63,
                         LOAD = 7'h03, STORE = 7'h23, OPIMM = 7'h13, OP = 7'h33;

  logic [31:0] pc, d_pc, d_instr, d_next, e_pc, e_instr, e_next, e_a, e_b, e_imm;
  logic [31:0] m_pc, m_instr, m_addr, m_data, m_store, w_pc, w_instr, w_value;
  logic [31:0] cycles, instret, branches, mispredicts;
  logic [4:0]  m_rd, w_rd;
  logic        d_valid, e_valid, m_valid, w_valid;
  logic [31:0] x [32];

  logic        btb_valid [16];
  logic [25:0] btb_tag [16];
  logic [31:0] btb_target [16];
  logic [1:0]  btb_count [16];

  wire [3:0] f_idx = pc[5:2];
  wire       f_taken = btb_valid[f_idx] && btb_tag[f_idx] == pc[31:6] && btb_count[f_idx][1];
  assign imem_addr = pc;

  wire [6:0] d_op = d_instr[6:0];
  wire [4:0] d_rs1 = d_instr[19:15], d_rs2 = d_instr[24:20];
  logic [31:0] d_imm;
  always_comb
    case (d_op)
      LUI, AUIPC: d_imm = {d_instr[31:12], 12'b0};
      JAL:        d_imm = {{12{d_instr[31]}}, d_instr[19:12], d_instr[20], d_instr[30:21], 1'b0};
      BRANCH:     d_imm = {{20{d_instr[31]}}, d_instr[7], d_instr[30:25], d_instr[11:8], 1'b0};
      STORE:      d_imm = {{21{d_instr[31]}}, d_instr[30:25], d_instr[11:7]};
      default:    d_imm = {{21{d_instr[31]}}, d_instr[30:20]};
    endcase
  wire d_uses_rs1 = !(d_op == LUI || d_op == AUIPC || d_op == JAL);
  wire d_uses_rs2 = d_op == BRANCH || d_op == STORE || d_op == OP;
  wire [31:0] d_a = w_valid && w_rd != 0 && w_rd == d_rs1 ? w_value : x[d_rs1];
  wire [31:0] d_b = w_valid && w_rd != 0 && w_rd == d_rs2 ? w_value : x[d_rs2];

  wire [6:0] e_op = e_instr[6:0];
  wire [2:0] e_f3 = e_instr[14:12];
  wire       e_writes = e_op == LUI || e_op == AUIPC || e_op == JAL || e_op == JALR || e_op == LOAD || e_op == OPIMM || e_op == OP;
  wire [4:0] e_rd = e_writes ? e_instr[11:7] : 5'd0;
  wire [4:0] e_rs1 = e_instr[19:15], e_rs2 = e_instr[24:20];
  wire stall = e_valid && e_op == LOAD && e_rd != 0 && d_valid &&
               (d_uses_rs1 && d_rs1 == e_rd || d_uses_rs2 && d_rs2 == e_rd);

  wire m_fwd_ok = m_valid && m_rd != 0 && m_instr[6:0] != LOAD;
  wire [31:0] a = m_fwd_ok && m_rd == e_rs1 ? m_data : w_valid && w_rd != 0 && w_rd == e_rs1 ? w_value : e_a;
  wire [31:0] b = m_fwd_ok && m_rd == e_rs2 ? m_data : w_valid && w_rd != 0 && w_rd == e_rs2 ? w_value : e_b;
  wire [31:0] y = e_op == OP ? b : e_imm;
  wire        alt = e_instr[30];
  logic [31:0] alu, e_result;
  always_comb begin
    case (e_f3)
      3'd0: alu = e_op == OP && alt ? a - y : a + y;
      3'd1: alu = a << y[4:0];
      3'd2: alu = {31'b0, $signed(a) < $signed(y)};
      3'd3: alu = {31'b0, a < y};
      3'd4: alu = a ^ y;
      3'd5: alu = alt ? $unsigned($signed(a) >>> y[4:0]) : a >> y[4:0];
      3'd6: alu = a | y;
      default: alu = a & y;
    endcase
    case (e_op)
      LUI:       e_result = e_imm;
      AUIPC:     e_result = e_pc + e_imm;
      JAL, JALR: e_result = e_pc + 4;
      default:   e_result = alu;
    endcase
  end
  logic e_cond;
  always_comb
    case (e_f3)
      3'd0: e_cond = a == b;
      3'd1: e_cond = a != b;
      3'd4: e_cond = $signed(a) < $signed(b);
      3'd5: e_cond = $signed(a) >= $signed(b);
      3'd6: e_cond = a < b;
      3'd7: e_cond = a >= b;
      default: e_cond = 1'b0;
    endcase
  wire        e_taken = e_op == JAL || e_op == JALR || e_op == BRANCH && e_cond;
  wire [31:0] e_target = e_op == JALR ? (a + e_imm) & ~32'd1 : e_pc + e_imm;
  wire [31:0] e_actual = e_taken ? e_target : e_pc + 4;
  wire        redirect = e_valid && e_actual != e_next;
  wire [3:0]  e_idx = e_pc[5:2];
  wire        e_hit = btb_valid[e_idx] && btb_tag[e_idx] == e_pc[31:6];

  wire [1:0]  m_off = m_addr[1:0];
  wire        m_io = m_addr[31:28] == 4'h1;
  wire        m_load = m_valid && m_instr[6:0] == LOAD;
  wire        m_write = m_valid && m_instr[6:0] == STORE;
  wire [2:0]  m_f3 = m_instr[14:12];
  logic [31:0] io_data, m_word, m_value;
  always_comb begin
    case (m_addr[7:0])
      8'h00:   io_data = {s_tvalid, 22'b0, s_tlast, s_tdata};
      8'h10:   io_data = cycles;
      8'h14:   io_data = instret;
      8'h18:   io_data = branches;
      8'h1c:   io_data = mispredicts;
      default: io_data = 32'b0;
    endcase
    m_word = (m_io ? io_data : dmem_rdata) >> (8 * m_off);
    case (m_f3)
      3'd0:    m_value = {{24{m_word[7]}}, m_word[7:0]};
      3'd1:    m_value = {{16{m_word[15]}}, m_word[15:0]};
      3'd4:    m_value = {24'b0, m_word[7:0]};
      3'd5:    m_value = {16'b0, m_word[15:0]};
      default: m_value = m_word;
    endcase
    if (!m_load) m_value = m_data;
  end
  assign dmem_addr  = m_addr;
  assign dmem_read  = m_load;
  assign dmem_wdata = m_f3 == 3'd0 ? {4{m_store[7:0]}} : m_f3 == 3'd1 ? {2{m_store[15:0]}} : m_store;
  assign dmem_wstrb = !m_write ? 4'b0 : m_f3 == 3'd0 ? 4'b0001 << m_off : m_f3 == 3'd1 ? 4'b0011 << m_off : 4'b1111;
  assign s_tready   = m_load && m_addr == 32'h1000_0000;

  assign retire_valid   = w_valid;
  assign retire_pc      = w_pc;
  assign retire_instr   = w_instr;
  assign retire_rd      = w_rd;
  assign retire_rd_data = w_rd != 0 ? w_value : 32'b0;

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      pc <= 0;
      {d_valid, e_valid, m_valid, w_valid} <= '0;
      {cycles, instret, branches, mispredicts} <= '0;
      for (int i = 0; i < 16; i++) btb_valid[i] <= 1'b0;
    end else begin
      cycles <= cycles + 1;
      instret <= instret + 32'(w_valid);
      branches <= branches + 32'(e_valid && e_op == BRANCH);
      mispredicts <= mispredicts + 32'(redirect);
      if (redirect) begin
        pc <= e_actual;
        {d_valid, e_valid} <= '0;
      end else if (stall) e_valid <= 1'b0;
      else begin
        pc <= f_taken ? btb_target[f_idx] : pc + 4;
        d_valid <= 1'b1;
        e_valid <= d_valid;
      end
      m_valid <= e_valid;
      w_valid <= m_valid;
      if (e_valid && (e_op == BRANCH || e_op == JAL)) begin
        btb_valid[e_idx] <= 1'b1;
        btb_tag[e_idx] <= e_pc[31:6];
        btb_target[e_idx] <= e_target;
        if (!e_hit) btb_count[e_idx] <= e_taken ? 2'b10 : 2'b01;
        else if (e_taken && btb_count[e_idx] != 2'b11) btb_count[e_idx] <= btb_count[e_idx] + 1;
        else if (!e_taken && btb_count[e_idx] != 2'b00) btb_count[e_idx] <= btb_count[e_idx] - 1;
      end
    end

  always_ff @(posedge clk) begin
    if (!redirect && !stall) begin
      {d_pc, d_instr} <= {pc, imem_data};
      d_next <= f_taken ? btb_target[f_idx] : pc + 4;
      {e_pc, e_instr, e_next, e_imm, e_a, e_b} <= {d_pc, d_instr, d_next, d_imm, d_a, d_b};
    end
    {m_pc, m_instr, m_rd, m_data, m_store} <= {e_pc, e_instr, e_rd, e_result, b};
    m_addr <= a + e_imm;
    {w_pc, w_instr, w_rd, w_value} <= {m_pc, m_instr, m_rd, m_value};
    if (w_valid && w_rd != 0) x[w_rd] <= w_value;
  end
endmodule
