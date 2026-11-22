// Top-level Tang Nano 20K (GW2AR-18) board wrapper joining fifo_bridge, the RV32I cpu, synchronous BRAM instruction/data memories initialized from firmware.hex, a dual-clock sensor frame feeder, and MMIO UART TX at 0x2000_0000.
module top (
  input  logic       clk,
  input  logic       btn1,
  output logic       uart_tx,
  output logic [5:0] led
);
  logic rst_n;
  assign rst_n = !btn1;

  logic [1:0]  clk_div;
  logic        s_clk;
  logic [23:0] hb_cnt;

  always_ff @(posedge clk or negedge rst_n) begin
    if (!rst_n) begin
      clk_div <= 2'd0;
      hb_cnt  <= 24'd0;
    end else begin
      clk_div <= clk_div + 2'd1;
      hb_cnt  <= hb_cnt + 24'd1;
    end
  end
  assign s_clk = clk_div[1];

  logic       s_rst_n;
  reset_sync gen_rst (.clk(s_clk), .rst_n_in(rst_n), .rst_n(s_rst_n));

  logic [15:0] sample_pace;
  logic [5:0]  sample_idx;
  logic        gen_valid, gen_ready, gen_last;
  logic [7:0]  gen_data;

  always_ff @(posedge s_clk or negedge s_rst_n) begin
    if (!s_rst_n) begin
      sample_pace <= 16'd0;
      sample_idx  <= 6'd0;
      gen_valid   <= 1'b0;
      gen_data    <= 8'd0;
      gen_last    <= 1'b0;
    end else begin
      if (gen_valid && gen_ready) begin
        gen_valid <= 1'b0;
      end else if (!gen_valid) begin
        if (sample_pace == 16'd6749) begin
          sample_pace <= 16'd0;
          gen_valid   <= 1'b1;
          gen_data    <= {2'b00, sample_idx} ^ 8'hff;
          gen_last    <= (sample_idx == 6'd63);
          sample_idx  <= sample_idx + 6'd1;
        end else begin
          sample_pace <= sample_pace + 16'd1;
        end
      end
    end
  end

  logic       m_tvalid, m_tready, m_tlast;
  logic [7:0] m_tdata;

  fifo_bridge #(.DEPTH_LOG2(4)) bridge (
    .rst_n(rst_n),
    .s_clk(s_clk),
    .s_tvalid(gen_valid),
    .s_tready(gen_ready),
    .s_tdata(gen_data),
    .s_tlast(gen_last),
    .m_clk(clk),
    .m_tvalid(m_tvalid),
    .m_tready(m_tready),
    .m_tdata(m_tdata),
    .m_tlast(m_tlast)
  );

  logic [31:0] imem [0:1023];
  logic [31:0] dmem [0:1023];
  initial $readmemh("firmware.hex", imem);

  logic [31:0] imem_addr, imem_data;
  logic        imem_en;
  logic [31:0] dmem_addr, dmem_wdata, dmem_rdata, dmem_ram_q, uart_status_q;
  logic [3:0]  dmem_wstrb;
  logic        dmem_read, uart_read_q;
  logic        dmem_is_uart, uart_busy, uart_tx_valid;
  logic        retire_valid, cpu_sleep;

  assign dmem_is_uart  = (dmem_addr[31:16] == 16'h2000);
  assign uart_tx_valid = dmem_is_uart && (dmem_addr[3:0] == 4'h0) && dmem_wstrb[0] && !uart_busy;

  always_ff @(posedge clk) begin
    if (imem_en)
      imem_data <= imem[imem_addr[11:2]];
  end

  always_ff @(posedge clk) begin
    if (dmem_addr[31:16] == 16'h0000) begin
      if (dmem_wstrb[0]) dmem[dmem_addr[11:2]][7:0]   <= dmem_wdata[7:0];
      if (dmem_wstrb[1]) dmem[dmem_addr[11:2]][15:8]  <= dmem_wdata[15:8];
      if (dmem_wstrb[2]) dmem[dmem_addr[11:2]][23:16] <= dmem_wdata[23:16];
      if (dmem_wstrb[3]) dmem[dmem_addr[11:2]][31:24] <= dmem_wdata[31:24];
    end
    dmem_ram_q    <= dmem[dmem_addr[11:2]];
    uart_read_q   <= dmem_read && dmem_is_uart;
    uart_status_q <= {31'b0, uart_busy};
  end

  assign dmem_rdata = uart_read_q ? uart_status_q : dmem_ram_q;

  cpu core (
    .clk(clk),
    .rst_n(rst_n),
    .imem_addr(imem_addr),
    .imem_en(imem_en),
    .imem_data(imem_data),
    .dmem_addr(dmem_addr),
    .dmem_wdata(dmem_wdata),
    .dmem_wstrb(dmem_wstrb),
    .dmem_read(dmem_read),
    .dmem_rdata(dmem_rdata),
    .s_tvalid(m_tvalid),
    .s_tready(m_tready),
    .s_tdata(m_tdata),
    .s_tlast(m_tlast),
    .retire_valid(retire_valid),
    .retire_pc(),
    .retire_instr(),
    .retire_rd_data(),
    .retire_rd(),
    .retire_intr(),
    .sleep(cpu_sleep),
    .retire_cause()
  );

  uart_tx #(.CLK_HZ(27_000_000), .BAUD(115_200)) console_tx (
    .clk(clk),
    .rst_n(rst_n),
    .tx_valid(uart_tx_valid),
    .tx_data(dmem_wdata[7:0]),
    .tx_busy(uart_busy),
    .tx_pin(uart_tx)
  );

  assign led = {~rst_n, ~m_tvalid, ~uart_busy, ~retire_valid, ~cpu_sleep, ~hb_cnt[23]};
endmodule
