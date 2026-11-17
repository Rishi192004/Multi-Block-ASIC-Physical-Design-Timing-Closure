// priority_encoder.v
// 16-to-4 priority encoder with registered output and valid flag
// EDA-Genius benchmark design #6
// Synthesizable Verilog-2001

module priority_encoder (
    input  wire        clk,
    input  wire        rst_n,
    input  wire [15:0] req,       // 16 request lines (bit 15 = highest priority)
    output reg  [ 3:0] grant,     // encoded index of highest-priority active request
    output reg         valid      // asserted when at least one request is active
);

    // Combinational priority resolution
    reg [3:0] enc;
    reg       any_req;

    always @(*) begin
        enc     = 4'd0;
        any_req = 1'b0;
        casez (req)
            16'b1???_????_????_????: begin enc = 4'd15; any_req = 1'b1; end
            16'b01??_????_????_????: begin enc = 4'd14; any_req = 1'b1; end
            16'b001?_????_????_????: begin enc = 4'd13; any_req = 1'b1; end
            16'b0001_????_????_????: begin enc = 4'd12; any_req = 1'b1; end
            16'b0000_1???_????_????: begin enc = 4'd11; any_req = 1'b1; end
            16'b0000_01??_????_????: begin enc = 4'd10; any_req = 1'b1; end
            16'b0000_001?_????_????: begin enc = 4'd9;  any_req = 1'b1; end
            16'b0000_0001_????_????: begin enc = 4'd8;  any_req = 1'b1; end
            16'b0000_0000_1???_????: begin enc = 4'd7;  any_req = 1'b1; end
            16'b0000_0000_01??_????: begin enc = 4'd6;  any_req = 1'b1; end
            16'b0000_0000_001?_????: begin enc = 4'd5;  any_req = 1'b1; end
            16'b0000_0000_0001_????: begin enc = 4'd4;  any_req = 1'b1; end
            16'b0000_0000_0000_1???: begin enc = 4'd3;  any_req = 1'b1; end
            16'b0000_0000_0000_01??: begin enc = 4'd2;  any_req = 1'b1; end
            16'b0000_0000_0000_001?: begin enc = 4'd1;  any_req = 1'b1; end
            16'b0000_0000_0000_0001: begin enc = 4'd0;  any_req = 1'b1; end
            default:                 begin enc = 4'd0;  any_req = 1'b0; end
        endcase
    end

    // Registered output pipeline stage
    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            grant <= 4'd0;
            valid <= 1'b0;
        end else begin
            grant <= enc;
            valid <= any_req;
        end
    end

endmodule
