// RV32I core with machine mode, 5 stages (IF ID EX MEM WB), every flop reset by rst_n asserted at once and released two edges later through reset_sync (from fifo_bridge), x0 read as zero rather than stored: forwarding, one-cycle load-use stall, 2-bit predictor with a 16-entry BTB, with MAC set a custom-0 multiply-accumulate for the filter (mac rs1, rs2 adds the signed product of their low halves to an accumulator when it commits in EX, macr rd reads the accumulator into rd and clears it; without MAC both trap as illegal), Zicsr with the machine CSRs, precise traps and interrupts (timer, and external while a stream sample waits, registered for a cycle) taken in EX where instructions commit, mret, wfi holding the pipeline asleep until an enabled interrupt is pending, and stream, counters and the mtime/mtimecmp timer at 0x1000_0000; memories are synchronous like the IHP SRAM macros: the next fetch address and the data address, write data and byte strobes of the instruction in EX go out in one cycle and are captured at its closing edge, and read data comes back in the next cycle (IF and MEM); imem_en is low when the fetch address repeats (a stall or sleep without a redirect), so the code memory need not read again and holds its last word.
module cpu #(parameter bit MAC = 1) (
  input  logic        clk, rst_n,
  output logic [31:0] imem_addr,
  output logic        imem_en,
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
  output logic [4:0]  retire_rd,
  output logic        retire_intr, sleep,
  output logic [3:0]  retire_cause
);
  localparam logic [6:0] LUI = 7'h37, AUIPC = 7'h17, JAL = 7'h6f, JALR = 7'h67, BRANCH = 7'h63,
                         LOAD = 7'h03, STORE = 7'h23, OPIMM = 7'h13, OP = 7'h33, FENCE = 7'h0f, SYSTEM = 7'h73, CUSTOM0 = 7'h0b;
  localparam logic [31:0] ECALL = 32'h00000073, EBREAK = 32'h00100073, MRET = 32'h30200073, WFI = 32'h10500073;

  logic [31:0] pc, d_pc, d_instr, d_next, e_pc, e_instr, e_next, e_a, e_b, e_imm;
  logic [31:0] m_pc, m_instr, m_addr, m_data, m_store, w_pc, w_instr, w_value;
  logic [31:0] branches, mispredicts, mtvec, mscratch, mepc, mcause, mtval, acc;
  logic [63:0] mcycle, minstret, mtime, mtimecmp;
  logic [4:0]  m_rd, w_rd;
  logic [3:0]  m_cause, w_cause;
  logic [2:0]  ie;
  logic        d_valid, e_valid, m_valid, w_valid, m_intr, w_intr, mstatus_mie, mpie, stop_cycle, stop_instret, asleep, meip;
  logic [31:0] x [32];
  logic        run;
  reset_sync reset_release (.clk, .rst_n_in(rst_n), .rst_n(run));

  logic        btb_valid [16];
  logic [25:0] btb_tag [16];
  logic [31:0] btb_target [16];
  logic [1:0]  btb_count [16];

  wire [3:0] f_idx = pc[5:2];
  wire       f_taken = btb_valid[f_idx] && btb_tag[f_idx] == pc[31:6] && btb_count[f_idx][1];

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
  wire d_uses_rs2 = d_op == BRANCH || d_op == STORE || d_op == OP || d_op == CUSTOM0;
  wire [31:0] d_a = d_rs1 == 0 ? 32'b0 : w_valid && w_rd == d_rs1 ? w_value : x[d_rs1];
  wire [31:0] d_b = d_rs2 == 0 ? 32'b0 : w_valid && w_rd == d_rs2 ? w_value : x[d_rs2];

  wire [6:0]  e_op = e_instr[6:0];
  wire [2:0]  e_f3 = e_instr[14:12];
  wire [6:0]  e_f7 = e_instr[31:25];
  wire [11:0] e_csr = e_instr[31:20];
  wire        e_csr_op = e_op == SYSTEM && e_f3[1:0] != 0;
  wire        e_writes = e_op == LUI || e_op == AUIPC || e_op == JAL || e_op == JALR || e_op == LOAD || e_op == OPIMM || e_op == OP || e_csr_op || MAC && e_op == CUSTOM0 && e_f3 == 1;
  wire [4:0]  e_rd = e_writes ? e_instr[11:7] : 5'd0;
  wire [4:0]  e_rs1 = e_instr[19:15], e_rs2 = e_instr[24:20];
  wire stall = e_valid && e_op == LOAD && e_rd != 0 && d_valid &&
               (d_uses_rs1 && d_rs1 == e_rd || d_uses_rs2 && d_rs2 == e_rd);

  wire m_fwd_ok = m_valid && m_rd != 0 && m_instr[6:0] != LOAD;
  wire [31:0] a = m_fwd_ok && m_rd == e_rs1 ? m_data : w_valid && w_rd != 0 && w_rd == e_rs1 ? w_value : e_a;
  wire [31:0] b = m_fwd_ok && m_rd == e_rs2 ? m_data : w_valid && w_rd != 0 && w_rd == e_rs2 ? w_value : e_b;
  wire [31:0] y = e_op == OP ? b : e_imm;
  wire        alt = e_instr[30];

  wire        mtip = mtime >= mtimecmp;
  wire [2:0]  pending = ie & {meip, mtip, 1'b0};
  logic [31:0] csr_old;
  logic        csr_known;
  always_comb begin
    csr_known = 1'b1;
    case (e_csr)
      12'h300: csr_old = {24'b0, mpie, 3'b0, mstatus_mie, 3'b0} | 32'h1800;
      12'h301: csr_old = 32'h40000100;
      12'h304: csr_old = {20'b0, ie[2], 3'b0, ie[1], 3'b0, ie[0], 3'b0};
      12'h305: csr_old = mtvec;
      12'h320: csr_old = {29'b0, stop_instret, 1'b0, stop_cycle};
      12'h340: csr_old = mscratch;
      12'h341: csr_old = mepc;
      12'h342: csr_old = mcause;
      12'h343: csr_old = mtval;
      12'h344: csr_old = {20'b0, meip, 3'b0, mtip, 7'b0};
      12'hb00, 12'hc00: csr_old = mcycle[31:0];
      12'hb80, 12'hc80: csr_old = mcycle[63:32];
      12'hb02, 12'hc02: csr_old = minstret[31:0];
      12'hb82, 12'hc82: csr_old = minstret[63:32];
      12'hf11, 12'hf12, 12'hf13, 12'hf14, 12'hf15: csr_old = 32'b0;
      default: begin csr_old = 32'b0; csr_known = 1'b0; end
    endcase
  end
  wire        csr_writes = e_f3[1:0] == 2'd1 || e_rs1 != 0;
  wire [31:0] csr_src = e_f3[2] ? {27'b0, e_rs1} : a;
  wire [31:0] csr_new = e_f3[1:0] == 2'd1 ? csr_src : e_f3[1:0] == 2'd2 ? csr_old | csr_src : csr_old & ~csr_src;

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
      SYSTEM:    e_result = csr_old;
      CUSTOM0:   e_result = acc;
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
  wire [31:0] e_addr = a + e_imm;
  wire        e_odd = e_f3[1:0] == 2'd1 && e_addr[0] || e_f3[1:0] == 2'd2 && e_addr[1:0] != 0;
  wire [3:0]  e_idx = e_pc[5:2];
  wire        e_hit = btb_valid[e_idx] && btb_tag[e_idx] == e_pc[31:6];

  logic e_legal;
  always_comb
    case (e_op)
      LUI, AUIPC, JAL, FENCE: e_legal = 1'b1;
      JALR:   e_legal = e_f3 == 0;
      BRANCH: e_legal = e_f3[2:1] != 2'b01;
      LOAD:   e_legal = e_f3 != 3 && e_f3 < 6;
      STORE:  e_legal = e_f3 < 3;
      OPIMM:  e_legal = e_f3 == 1 ? e_f7 == 0 : e_f3 == 5 ? (e_f7 & ~7'h20) == 0 : 1'b1;
      OP:     e_legal = e_f7 == 0 || e_f7 == 7'h20 && (e_f3 == 0 || e_f3 == 5);
      CUSTOM0: e_legal = MAC && e_f7 == 0 && (e_f3 == 0 && e_instr[11:7] == 0 || e_f3 == 1 && e_rs1 == 0 && e_rs2 == 0);
      SYSTEM: e_legal = e_f3 == 0 ? e_instr == ECALL || e_instr == EBREAK || e_instr == MRET || e_instr == WFI
                                  : e_f3 != 4 && csr_known && !(csr_writes && e_csr[11:10] == 2'b11);
      default: e_legal = 1'b0;
    endcase
  logic       e_exception;
  logic [3:0] e_exc_cause;
  logic [31:0] e_tval;
  always_comb begin
    {e_exception, e_exc_cause, e_tval} = {1'b1, 4'd0, 32'b0};
    if (!e_legal) {e_exc_cause, e_tval} = {4'd2, e_instr};
    else if (e_instr == ECALL) e_exc_cause = 4'd11;
    else if (e_instr == EBREAK) {e_exc_cause, e_tval} = {4'd3, e_pc};
    else if (e_op == LOAD && e_odd) {e_exc_cause, e_tval} = {4'd4, e_addr};
    else if (e_op == STORE && e_odd) {e_exc_cause, e_tval} = {4'd6, e_addr};
    else if (e_taken && e_target[1]) e_tval = e_target;
    else e_exception = 1'b0;
  end
  wire        wake = pending != 0;
  wire        e_irq = e_valid && mstatus_mie && wake;
  wire [3:0]  irq_cause = pending[2] ? 4'd11 : 4'd7;
  wire        e_trap = e_valid && (e_irq || e_exception);
  wire        e_hold = asleep && !wake && e_valid;
  wire        e_commit = e_valid && !e_trap && !e_hold;
  wire        e_mret = e_instr == MRET;
  wire        csr_write = e_commit && e_csr_op && csr_writes;
  wire        mispredict = e_commit && !e_mret && e_actual != e_next;
  wire        redirect = e_trap || e_commit && e_mret || mispredict;
  wire [3:0]  trap_cause = e_irq ? irq_cause : e_exc_cause;
  wire [31:0] trap_pc = {mtvec[31:2], 2'b0} + (mtvec[0] && e_irq ? {26'b0, irq_cause, 2'b0} : 32'b0);
  wire [31:0] new_pc = e_trap ? trap_pc : e_mret ? mepc : e_actual;

  wire [1:0]  m_off = m_addr[1:0];
  wire        m_io = m_addr[31:28] == 4'h1;
  wire        m_load = m_valid && m_instr[6:0] == LOAD;
  wire        m_write = m_valid && m_instr[6:0] == STORE;
  wire [2:0]  m_f3 = m_instr[14:12];
  logic [31:0] io_data, m_word, m_value;
  always_comb begin
    case (m_addr[7:0])
      8'h00:   io_data = {s_tvalid, 22'b0, s_tlast, s_tdata};
      8'h10:   io_data = mcycle[31:0];
      8'h14:   io_data = minstret[31:0];
      8'h18:   io_data = branches;
      8'h1c:   io_data = mispredicts;
      8'h20:   io_data = mtime[31:0];
      8'h24:   io_data = mtime[63:32];
      8'h28:   io_data = mtimecmp[31:0];
      8'h2c:   io_data = mtimecmp[63:32];
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
  wire [31:0] pc_next = redirect ? new_pc : e_hold || stall ? pc : f_taken ? btb_target[f_idx] : pc + 4;
  assign imem_addr  = run ? pc_next : 32'b0;
  assign imem_en    = redirect || !(e_hold || stall);
  assign dmem_addr  = e_addr;
  assign dmem_read  = e_commit && e_op == LOAD;
  assign dmem_wdata = e_f3 == 3'd0 ? {4{b[7:0]}} : e_f3 == 3'd1 ? {2{b[15:0]}} : b;
  assign dmem_wstrb = !(e_commit && e_op == STORE) ? 4'b0 : e_f3 == 3'd0 ? 4'b0001 << e_addr[1:0] : e_f3 == 3'd1 ? 4'b0011 << e_addr[1:0] : 4'b1111;
  assign s_tready   = m_load && m_addr == 32'h1000_0000;

  assign retire_valid   = w_valid;
  assign retire_pc      = w_pc;
  assign retire_instr   = w_instr;
  assign retire_rd      = w_rd;
  assign retire_rd_data = w_rd != 0 ? w_value : 32'b0;
  assign retire_intr    = w_intr;
  assign retire_cause   = w_cause;
  assign sleep          = asleep;

  always_ff @(posedge clk or negedge run)
    if (!run) begin
      pc <= 0;
      {d_valid, e_valid, m_valid, w_valid, m_intr, w_intr, asleep, meip} <= '0;
      {branches, mispredicts, mcycle, minstret, mtime, acc} <= '0;
      mtimecmp <= '1;
      {mtvec, mscratch, mepc, mcause, mtval, ie, mstatus_mie, mpie, stop_cycle, stop_instret} <= '0;
      for (int i = 0; i < 16; i++) {btb_valid[i], btb_tag[i], btb_target[i], btb_count[i]} <= '0;
    end else begin
      mtime <= mtime + 1;
      meip <= s_tvalid;
      if (!stop_cycle && !(csr_write && (e_csr == 12'hb00 || e_csr == 12'hb80))) mcycle <= mcycle + 1;
      if (e_commit && !stop_instret && !(csr_write && (e_csr == 12'hb02 || e_csr == 12'hb82))) minstret <= minstret + 1;
      branches <= branches + 32'(e_commit && e_op == BRANCH);
      mispredicts <= mispredicts + 32'(mispredict);
      if (redirect) begin
        pc <= pc_next;
        {d_valid, e_valid} <= '0;
      end else if (e_hold) ;
      else if (stall) e_valid <= 1'b0;
      else begin
        pc <= pc_next;
        d_valid <= 1'b1;
        e_valid <= d_valid;
      end
      m_valid <= e_commit;
      w_valid <= m_valid;
      m_intr <= e_irq;
      w_intr <= m_intr;
      if (wake) asleep <= 1'b0;
      else if (e_commit && e_instr == WFI) asleep <= 1'b1;
      if (e_trap) begin
        {mepc, mcause, mtval} <= {e_pc, e_irq, 27'b0, trap_cause, e_irq ? 32'b0 : e_tval};
        {mpie, mstatus_mie} <= {mstatus_mie, 1'b0};
      end
      if (e_commit && e_mret) {mpie, mstatus_mie} <= {1'b1, mpie};
      if (MAC && e_commit && e_op == CUSTOM0) acc <= e_f3[0] ? 32'b0 : acc + 32'($signed(a[15:0]) * $signed(b[15:0]));
      if (csr_write)
        case (e_csr)
          12'h300: {mpie, mstatus_mie} <= {csr_new[7], csr_new[3]};
          12'h304: ie <= {csr_new[11], csr_new[7], csr_new[3]};
          12'h305: mtvec <= csr_new & ~32'd2;
          12'h320: {stop_instret, stop_cycle} <= {csr_new[2], csr_new[0]};
          12'h340: mscratch <= csr_new;
          12'h341: mepc <= csr_new & ~32'd3;
          12'h342: mcause <= csr_new;
          12'h343: mtval <= csr_new;
          12'hb00: mcycle[31:0] <= csr_new;
          12'hb80: mcycle[63:32] <= csr_new;
          12'hb02: minstret[31:0] <= csr_new;
          12'hb82: minstret[63:32] <= csr_new;
          default: ;
        endcase
      if (m_write && m_io && m_addr[7:0] == 8'h28) mtimecmp[31:0] <= m_store;
      if (m_write && m_io && m_addr[7:0] == 8'h2c) mtimecmp[63:32] <= m_store;
      if (e_commit && (e_op == BRANCH || e_op == JAL)) begin
        btb_valid[e_idx] <= 1'b1;
        btb_tag[e_idx] <= e_pc[31:6];
        btb_target[e_idx] <= e_target;
        if (!e_hit) btb_count[e_idx] <= e_taken ? 2'b10 : 2'b01;
        else if (e_taken && btb_count[e_idx] != 2'b11) btb_count[e_idx] <= btb_count[e_idx] + 1;
        else if (!e_taken && btb_count[e_idx] != 2'b00) btb_count[e_idx] <= btb_count[e_idx] - 1;
      end
    end

  always_ff @(posedge clk or negedge run)
    if (!run) begin
      {d_pc, d_instr, d_next, e_pc, e_instr, e_next, e_imm, e_a, e_b} <= '0;
      {m_pc, m_instr, m_rd, m_data, m_store, m_cause, m_addr, w_pc, w_instr, w_rd, w_value, w_cause} <= '0;
      for (int i = 1; i < 32; i++) x[i] <= '0;
    end else begin
      if (!redirect && !stall && !e_hold) begin
        {d_pc, d_instr} <= {pc, imem_data};
        d_next <= f_taken ? btb_target[f_idx] : pc + 4;
        {e_pc, e_instr, e_next, e_imm, e_a, e_b} <= {d_pc, d_instr, d_next, d_imm, d_a, d_b};
      end
      {m_pc, m_instr, m_rd, m_data, m_store, m_cause} <= {e_pc, e_instr, e_rd, e_result, b, irq_cause};
      m_addr <= e_addr;
      {w_pc, w_instr, w_rd, w_value, w_cause} <= {m_pc, m_instr, m_rd, m_value, m_cause};
      if (w_valid && w_rd != 0) x[w_rd] <= w_value;
    end
endmodule
