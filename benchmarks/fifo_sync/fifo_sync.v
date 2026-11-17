// Parameterized Synchronous FIFO
// Real synthesizable digital benchmark for EDA-Genius

module fifo_sync #(
    parameter DATA_WIDTH = 16,
    parameter ADDR_WIDTH = 4,
    parameter FIFO_DEPTH = 1 << ADDR_WIDTH
)(
    input  wire                  clk,
    input  wire                  rst_n,
    input  wire                  wr_en,
    input  wire [DATA_WIDTH-1:0] wr_data,
    input  wire                  rd_en,
    output reg  [DATA_WIDTH-1:0] rd_data,
    output wire                  full,
    output wire                  empty,
    output wire                  almost_full,
    output wire                  almost_empty,
    output reg  [ADDR_WIDTH:0]   fifo_count
);

    reg [DATA_WIDTH-1:0] mem [0:FIFO_DEPTH-1];
    reg [ADDR_WIDTH-1:0] wr_ptr;
    reg [ADDR_WIDTH-1:0] rd_ptr;

    assign full         = (fifo_count == FIFO_DEPTH);
    assign empty        = (fifo_count == 0);
    assign almost_full  = (fifo_count >= FIFO_DEPTH - 2);
    assign almost_empty = (fifo_count <= 2);

    // Memory write logic
    always @(posedge clk) begin
        if (wr_en && !full) begin
            mem[wr_ptr] <= wr_data;
        end
    end

    // Memory read logic
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            rd_data <= {DATA_WIDTH{1'b0}};
        end else if (rd_en && !empty) begin
            rd_data <= mem[rd_ptr];
        end
    end

    // Pointer and counter management
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            wr_ptr     <= {ADDR_WIDTH{1'b0}};
            rd_ptr     <= {ADDR_WIDTH{1'b0}};
            fifo_count <= {(ADDR_WIDTH+1){1'b0}};
        end else begin
            case ({wr_en && !full, rd_en && !empty})
                2'b10: begin
                    wr_ptr     <= wr_ptr + 1'b1;
                    fifo_count <= fifo_count + 1'b1;
                end
                2'b01: begin
                    rd_ptr     <= rd_ptr + 1'b1;
                    fifo_count <= fifo_count - 1'b1;
                end
                2'b11: begin
                    wr_ptr <= wr_ptr + 1'b1;
                    rd_ptr <= rd_ptr + 1'b1;
                end
                default: ;
            endcase
        end
    end

endmodule
