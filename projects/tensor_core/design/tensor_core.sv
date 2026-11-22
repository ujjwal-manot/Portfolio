// Tensor core: an N x N array of fma cells running C = C + A * B from banked on-chip buffers (A by row and by k, B and C by column, so each cycle reads at most one word per bank), loaded and read back through one word port; WS=0 is output stationary (each cell keeps one C element, A flows right and B down with a one-cycle skew per row and column, the tile's C rows are loaded and stored one per cycle), WS=1 is weight stationary (each cell keeps one B element, loaded one row per cycle, A flows right and partial sums flow down from C and back into it); either way every C element is the FMA chain over k = 0 to K-1 in order from its starting value, with each element's MX scale (xa per A row and 32-element block of k, xb per B column and block, 127 when mx is low) travelling with it; M, N and K must be multiples of N.
module tensor_core #(
  parameter int N = 8,
  parameter int WS = 0,
  parameter int MAXM = 64,
  parameter int MAXK = 64,
  parameter int MAXN = 64
) (
  input  logic        clk, rst_n,
  input  logic        we,
  input  logic [2:0]  sel,
  input  logic [15:0] addr,
  input  logic [31:0] wdata,
  output logic [31:0] rdata,
  input  logic        start,
  input  logic [1:0]  fmt,
  input  logic        mx,
  input  logic [9:0]  m, k, n,
  output logic        busy
);
  localparam int KB = MAXK / 32;
  typedef enum logic [1:0] {IDLE, LOAD, STREAM, STORE} state_t;

  logic [15:0] amem [MAXM * MAXK];
  logic [15:0] bmem [MAXK * MAXN];
  logic [31:0] cmem [MAXM * MAXN];
  logic [7:0]  xamem [MAXM * KB];
  logic [7:0]  xbmem [KB * MAXN];

  state_t state;
  logic [1:0] f;
  logic s_mx;
  logic [9:0] dm, dk, dn, ti, tj, t, r;

  logic [15:0] edge_a [N], edge_b [N];
  logic [7:0]  edge_xa [N], edge_xb [N];
  logic        edge_av [N], edge_bv [N];
  logic [31:0] edge_c [N];

  logic [15:0] a_r [N][N], b_r [N][N];
  logic [7:0]  xa_r [N][N], xb_r [N][N];
  logic        av_r [N][N], bv_r [N][N];
  logic [31:0] acc [N][N], y [N][N];

  assign busy = state != IDLE;
  assign rdata = cmem[int'(addr)];

  always_comb
    for (int i = 0; i < N; i++) begin
      int kk, mm, row, col;
      row = int'(ti) * N + i;
      col = int'(tj) * N + i;
      if (WS == 0) begin
        kk = int'(t) - i;
        edge_av[i] = state == STREAM && kk >= 0 && kk < int'(dk);
        edge_bv[i] = edge_av[i];
        kk = edge_av[i] ? kk : 0;
        edge_a[i] = amem[row * MAXK + kk];
        edge_xa[i] = s_mx ? xamem[row * KB + kk / 32] : 8'd127;
        edge_b[i] = bmem[kk * MAXN + col];
        edge_xb[i] = s_mx ? xbmem[kk / 32 * MAXN + col] : 8'd127;
        edge_c[i] = 0;
      end else begin
        mm = int'(t) - i;
        kk = int'(ti) * N + i;
        edge_av[i] = state == STREAM && mm >= 0 && mm < int'(dm);
        edge_bv[i] = edge_av[i];
        mm = edge_av[i] ? mm : 0;
        edge_a[i] = amem[mm * MAXK + kk];
        edge_xa[i] = s_mx ? xamem[mm * KB + kk / 32] : 8'd127;
        edge_b[i] = 0;
        edge_xb[i] = 0;
        edge_c[i] = cmem[mm * MAXN + col];
      end
    end

  for (genvar i = 0; i < N; i++) begin : row_of
    for (genvar j = 0; j < N; j++) begin : pe
      wire [15:0] a_in = j == 0 ? edge_a[i] : a_r[i][j - 1];
      wire [7:0]  xa_in = j == 0 ? edge_xa[i] : xa_r[i][j - 1];
      wire        av_in = j == 0 ? edge_av[i] : av_r[i][j - 1];
      wire [15:0] b_in = WS != 0 ? b_r[i][j] : i == 0 ? edge_b[j] : b_r[i - 1][j];
      wire [7:0]  xb_in = WS != 0 ? xb_r[i][j] : i == 0 ? edge_xb[j] : xb_r[i - 1][j];
      wire        bv_in = WS != 0 ? av_in : i == 0 ? edge_bv[j] : bv_r[i - 1][j];
      wire [31:0] c_in = WS == 0 ? acc[i][j] : i == 0 ? edge_c[j] : acc[i - 1][j];
      fma unit (.fmt(f), .a(a_in), .b(b_in), .xa(xa_in), .xb(xb_in), .c(c_in), .y(y[i][j]));
      always_ff @(posedge clk or negedge rst_n)
        if (!rst_n) begin
          {a_r[i][j], xa_r[i][j], av_r[i][j], acc[i][j]} <= '0;
          if (WS == 0) {b_r[i][j], xb_r[i][j], bv_r[i][j]} <= '0;
        end else begin
          {a_r[i][j], xa_r[i][j], av_r[i][j]} <= {a_in, xa_in, av_in};
          if (WS == 0) begin
            {b_r[i][j], xb_r[i][j], bv_r[i][j]} <= {b_in, xb_in, bv_in};
            if (state == LOAD && int'(r) == i) acc[i][j] <= cmem[(int'(ti) * N + i) * MAXN + int'(tj) * N + j];
            else if (av_in && bv_in) acc[i][j] <= y[i][j];
          end else begin
            if (state == LOAD && int'(r) == i) begin
              b_r[i][j] <= bmem[(int'(ti) * N + i) * MAXN + int'(tj) * N + j];
              xb_r[i][j] <= s_mx ? xbmem[(int'(ti) * N + i) / 32 * MAXN + int'(tj) * N + j] : 8'd127;
            end
            bv_r[i][j] <= av_in;
            acc[i][j] <= y[i][j];
          end
        end
    end
  end

  always_ff @(posedge clk) begin
    if (we)
      case (sel)
        3'd0: amem[int'(addr)] <= wdata[15:0];
        3'd1: bmem[int'(addr)] <= wdata[15:0];
        3'd2: cmem[int'(addr)] <= wdata;
        3'd3: xamem[int'(addr)] <= wdata[7:0];
        default: xbmem[int'(addr)] <= wdata[7:0];
      endcase
    else if (WS == 0 && state == STORE)
      for (int j = 0; j < N; j++) cmem[(int'(ti) * N + int'(r)) * MAXN + int'(tj) * N + j] <= acc[int'(r)][j];
    else if (WS != 0 && state == STREAM)
      for (int j = 0; j < N; j++)
        if (bv_r[N - 1][j] && int'(t) - N - j >= 0) cmem[(int'(t) - N - j) * MAXN + int'(tj) * N + j] <= acc[N - 1][j];
  end

  always_ff @(posedge clk or negedge rst_n)
    if (!rst_n) begin
      state <= IDLE;
      {f, s_mx, dm, dk, dn, ti, tj, t, r} <= '0;
    end else
      case (state)
        IDLE: if (start) begin
          {f, s_mx, dm, dk, dn} <= {fmt, mx, m, k, n};
          {ti, tj, t, r} <= '0;
          state <= LOAD;
        end
        LOAD: if (int'(r) == N - 1) {state, r, t} <= {STREAM, 10'd0, 10'd0};
              else r <= r + 1;
        STREAM: if (int'(t) == (WS == 0 ? int'(dk) : int'(dm)) + 2 * N - (WS == 0 ? 3 : 2)) begin
          t <= 0;
          if (WS == 0) state <= STORE;
          else begin
            state <= LOAD;
            if (int'(ti) == int'(dk) / N - 1) begin
              ti <= 0;
              if (int'(tj) == int'(dn) / N - 1) state <= IDLE;
              else tj <= tj + 1;
            end else ti <= ti + 1;
          end
        end else t <= t + 1;
        default: if (int'(r) == N - 1) begin
          r <= 0;
          state <= LOAD;
          if (int'(tj) == int'(dn) / N - 1) begin
            tj <= 0;
            if (int'(ti) == int'(dm) / N - 1) state <= IDLE;
            else ti <= ti + 1;
          end else tj <= tj + 1;
        end else r <= r + 1;
      endcase
endmodule
