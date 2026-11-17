// UART Transmitter Module
// Real synthesizable digital benchmark for EDA-Genius

module uart_tx #(
    parameter CLKS_PER_BIT = 87 // Example: 10MHz clock / 115200 baud
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       tx_start,
    input  wire [7:0] tx_data,
    output reg        tx_serial,
    output reg        tx_busy,
    output reg        tx_done
);

    localparam S_IDLE       = 3'b000;
    localparam S_START_BIT  = 3'b001;
    localparam S_DATA_BITS  = 3'b010;
    localparam S_STOP_BIT   = 3'b011;
    localparam S_CLEANUP    = 3'b100;

    reg [2:0]   state;
    reg [15:0]  clk_count;
    reg [2:0]   bit_index;
    reg [7:0]   data_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= S_IDLE;
            tx_serial   <= 1'b1; // Idle high
            tx_busy     <= 1'b0;
            tx_done     <= 1'b0;
            clk_count   <= 16'd0;
            bit_index   <= 3'd0;
            data_reg    <= 8'd0;
        end else begin
            tx_done <= 1'b0;
            case (state)
                S_IDLE: begin
                    tx_serial <= 1'b1;
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    if (tx_start) begin
                        tx_busy  <= 1'b1;
                        data_reg <= tx_data;
                        state    <= S_START_BIT;
                    end else begin
                        tx_busy  <= 1'b0;
                    end
                end

                S_START_BIT: begin
                    tx_serial <= 1'b0; // Start bit is low
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 16'd0;
                        state     <= S_DATA_BITS;
                    end
                end

                S_DATA_BITS: begin
                    tx_serial <= data_reg[bit_index];
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        clk_count <= 16'd0;
                        if (bit_index < 3'd7) begin
                            bit_index <= bit_index + 1;
                        end else begin
                            bit_index <= 3'd0;
                            state     <= S_STOP_BIT;
                        end
                    end
                end

                S_STOP_BIT: begin
                    tx_serial <= 1'b1; // Stop bit is high
                    if (clk_count < CLKS_PER_BIT - 1) begin
                        clk_count <= clk_count + 1;
                    end else begin
                        tx_done   <= 1'b1;
                        clk_count <= 16'd0;
                        state     <= S_CLEANUP;
                    end
                end

                S_CLEANUP: begin
                    tx_busy <= 1'b0;
                    state   <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
