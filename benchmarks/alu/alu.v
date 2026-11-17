// 32-bit Arithmetic Logic Unit (ALU)
// Real synthesizable digital benchmark for EDA-Genius

module alu #(
    parameter DATA_WIDTH = 32
)(
    input  wire [DATA_WIDTH-1:0] a,
    input  wire [DATA_WIDTH-1:0] b,
    input  wire [3:0]            alu_op,
    output reg  [DATA_WIDTH-1:0] result,
    output wire                  zero,
    output wire                  carry_out,
    output wire                  overflow
);

    localparam ALU_ADD  = 4'b0000;
    localparam ALU_SUB  = 4'b0001;
    localparam ALU_AND  = 4'b0010;
    localparam ALU_OR   = 4'b0011;
    localparam ALU_XOR  = 4'b0100;
    localparam ALU_NOR  = 4'b0101;
    localparam ALU_SLL  = 4'b0110;
    localparam ALU_SRL  = 4'b0111;
    localparam ALU_SRA  = 4'b1000;
    localparam ALU_SLT  = 4'b1001;

    wire [DATA_WIDTH:0] ext_add;
    wire [DATA_WIDTH:0] ext_sub;

    assign ext_add = {1'b0, a} + {1'b0, b};
    assign ext_sub = {1'b0, a} - {1'b0, b};

    assign carry_out = (alu_op == ALU_ADD) ? ext_add[DATA_WIDTH] :
                       (alu_op == ALU_SUB) ? ext_sub[DATA_WIDTH] : 1'b0;

    assign overflow = (alu_op == ALU_ADD) ? ((a[DATA_WIDTH-1] == b[DATA_WIDTH-1]) && (result[DATA_WIDTH-1] != a[DATA_WIDTH-1])) :
                      (alu_op == ALU_SUB) ? ((a[DATA_WIDTH-1] != b[DATA_WIDTH-1]) && (result[DATA_WIDTH-1] != a[DATA_WIDTH-1])) : 1'b0;

    assign zero = (result == {DATA_WIDTH{1'b0}});

    always @(*) begin
        case (alu_op)
            ALU_ADD: result = ext_add[DATA_WIDTH-1:0];
            ALU_SUB: result = ext_sub[DATA_WIDTH-1:0];
            ALU_AND: result = a & b;
            ALU_OR:  result = a | b;
            ALU_XOR: result = a ^ b;
            ALU_NOR: result = ~(a | b);
            ALU_SLL: result = a << b[4:0];
            ALU_SRL: result = a >> b[4:0];
            ALU_SRA: result = $signed(a) >>> b[4:0];
            ALU_SLT: result = ($signed(a) < $signed(b)) ? {{(DATA_WIDTH-1){1'b0}}, 1'b1} : {DATA_WIDTH{1'b0}};
            default: result = {DATA_WIDTH{1'b0}};
        endcase
    end

endmodule
