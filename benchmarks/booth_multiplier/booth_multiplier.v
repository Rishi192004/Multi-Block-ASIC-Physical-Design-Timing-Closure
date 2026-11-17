// Radix-2 / Sequential Signed Multiplier
// Real synthesizable digital benchmark for EDA-Genius

module booth_multiplier #(
    parameter WIDTH = 16
)(
    input  wire                 clk,
    input  wire                 rst_n,
    input  wire                 start,
    input  wire [WIDTH-1:0]     multiplicand,
    input  wire [WIDTH-1:0]     multiplier,
    output reg  [(2*WIDTH)-1:0] product,
    output reg                  done,
    output reg                  busy
);

    localparam S_IDLE = 2'b00;
    localparam S_CALC = 2'b01;
    localparam S_DONE = 2'b10;

    reg [1:0]           state;
    reg [WIDTH-1:0]     a_reg;
    reg [WIDTH-1:0]     q_reg;
    reg [WIDTH-1:0]     m_reg;
    reg                 q_minus_1;
    reg [$clog2(WIDTH):0] count;

    wire [WIDTH-1:0]    add_res;
    wire [WIDTH-1:0]    sub_res;

    assign add_res = a_reg + m_reg;
    assign sub_res = a_reg - m_reg;

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state       <= S_IDLE;
            a_reg       <= {WIDTH{1'b0}};
            q_reg       <= {WIDTH{1'b0}};
            m_reg       <= {WIDTH{1'b0}};
            q_minus_1   <= 1'b0;
            count       <= 0;
            product     <= {(2*WIDTH){1'b0}};
            done        <= 1'b0;
            busy        <= 1'b0;
        end else begin
            case (state)
                S_IDLE: begin
                    done <= 1'b0;
                    if (start) begin
                        busy      <= 1'b1;
                        m_reg     <= multiplicand;
                        q_reg     <= multiplier;
                        a_reg     <= {WIDTH{1'b0}};
                        q_minus_1 <= 1'b0;
                        count     <= WIDTH;
                        state     <= S_CALC;
                    end else begin
                        busy <= 1'b0;
                    end
                end

                S_CALC: begin
                    if (count > 0) begin
                        // Arithmetic shift with addition/subtraction
                        case ({q_reg[0], q_minus_1})
                            2'b01: begin // Add
                                {a_reg, q_reg, q_minus_1} <= {add_res[WIDTH-1], add_res, q_reg};
                            end
                            2'b10: begin // Sub
                                {a_reg, q_reg, q_minus_1} <= {sub_res[WIDTH-1], sub_res, q_reg};
                            end
                            default: begin // Shift only
                                {a_reg, q_reg, q_minus_1} <= {a_reg[WIDTH-1], a_reg, q_reg};
                            end
                        endcase
                        count <= count - 1;
                    end else begin
                        product <= {a_reg, q_reg};
                        state   <= S_DONE;
                    end
                end

                S_DONE: begin
                    done <= 1'b1;
                    busy <= 1'b0;
                    state <= S_IDLE;
                end

                default: state <= S_IDLE;
            endcase
        end
    end

endmodule
