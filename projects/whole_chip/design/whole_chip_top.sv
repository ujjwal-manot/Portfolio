// Top-level digital and mixed-signal integration wrapper for EdgeSense-130 whole_chip joining sar_logic, fifo_bridge, cpu, dldo_ctrl, synchronous 1024x32 memories initialized from firmware/fir8_dvfs.hex, DVFS/FIR MMIO registers at 0x2000_0000, and droop clock stretching.
module whole_chip_top (
  input  logic        rst_n,
  input  logic        clk_adc,
  input  logic        clk_sys,
  input  logic        comp_out,
  input  logic        dldo_lo,
  input  logic        dldo_hi,
  input  logic        dldo_far_lo,
  input  logic        dldo_far_hi,
  input  logic        droop_alert,
  output logic        adc_samp,
  output logic        adc_comp_clk,
  output logic [7:0]  adc_dac,
  output logic        adc_overflow,
  output logic [1:0]  dvfs_state,
  output logic [31:0] fir_last,
  output logic [31:0] peak_last,
  output logic        cpu_sleep,
  output logic [127:0] dldo_on
);
  logic       s_tvalid, s_tready, s_tlast;
  logic [7:0] s_tdata;
  logic       m_tvalid, m_tready, m_tlast;
  logic [7:0] m_tdata;

  sar_logic adc_ctrl (
    .clk(clk_adc), .rst_n(rst_n), .comp_out(comp_out),
    .samp(adc_samp), .comp_clk(adc_comp_clk), .dac(adc_dac),
    .m_tvalid(s_tvalid), .m_tready(s_tready), .m_tdata(s_tdata),
    .m_tlast(s_tlast), .overflow(adc_overflow)
  );

  logic clk_cpu_en, clk_cpu;
  always_latch begin
    if (!clk_sys) clk_cpu_en = !droop_alert;
  end
  assign clk_cpu = clk_sys & clk_cpu_en;

  fifo_bridge #(.DEPTH_LOG2(4)) bridge (
    .rst_n(rst_n),
    .s_clk(clk_adc), .s_tvalid(s_tvalid), .s_tready(s_tready), .s_tdata(s_tdata), .s_tlast(s_tlast),
    .m_clk(clk_sys), .m_tvalid(m_tvalid), .m_tready(m_tready && clk_cpu_en), .m_tdata(m_tdata), .m_tlast(m_tlast)
  );

  logic [31:0] imem [0:1023];
  logic [31:0] dmem [0:1023];
  initial $readmemh("firmware/fir8_dvfs.hex", imem);

  logic [31:0] imem_addr, imem_data, dmem_addr, dmem_wdata, dmem_rdata;
  logic [3:0]  dmem_wstrb;
  logic        imem_en, dmem_read, is_mmio;
  assign is_mmio = (dmem_addr[31:16] == 16'h2000);

  always_ff @(posedge clk_cpu) begin
    if (imem_en) imem_data <= imem[imem_addr[11:2]];
  end

  always_ff @(posedge clk_cpu or negedge rst_n) begin
    if (!rst_n) begin
      dvfs_state <= 2'd3;
      fir_last   <= 32'd0;
      peak_last  <= 32'd0;
    end else if (is_mmio && dmem_wstrb != 4'b0) begin
      if (dmem_addr[3:0] == 4'h0) dvfs_state <= dmem_wdata[1:0];
      if (dmem_addr[3:0] == 4'h4) fir_last   <= dmem_wdata;
      if (dmem_addr[3:0] == 4'h8) peak_last  <= dmem_wdata;
    end
  end

  always_ff @(posedge clk_cpu) begin
    if (dmem_addr[31:16] == 16'h0000) begin
      if (dmem_wstrb[0]) dmem[dmem_addr[11:2]][7:0]   <= dmem_wdata[7:0];
      if (dmem_wstrb[1]) dmem[dmem_addr[11:2]][15:8]  <= dmem_wdata[15:8];
      if (dmem_wstrb[2]) dmem[dmem_addr[11:2]][23:16] <= dmem_wdata[23:16];
      if (dmem_wstrb[3]) dmem[dmem_addr[11:2]][31:24] <= dmem_wdata[31:24];
      dmem_rdata <= dmem[dmem_addr[11:2]];
    end
  end

  cpu core (
    .clk(clk_cpu), .rst_n(rst_n),
    .imem_addr(imem_addr), .imem_en(imem_en), .imem_data(imem_data),
    .dmem_addr(dmem_addr), .dmem_wdata(dmem_wdata), .dmem_wstrb(dmem_wstrb),
    .dmem_read(dmem_read), .dmem_rdata(dmem_rdata),
    .s_tvalid(m_tvalid), .s_tready(m_tready), .s_tdata(m_tdata), .s_tlast(m_tlast),
    .retire_valid(), .retire_pc(), .retire_instr(), .retire_rd_data(),
    .retire_rd(), .retire_intr(), .sleep(cpu_sleep), .retire_cause()
  );

  dldo_ctrl #(.N(128), .BIG(8), .P(1), .PB(8)) pmu (
    .clk(clk_sys), .rst_n(rst_n),
    .lo(dldo_lo), .hi(dldo_hi), .far_lo(dldo_far_lo), .far_hi(dldo_far_hi),
    .on(dldo_on), .count(), .drive()
  );
endmodule
