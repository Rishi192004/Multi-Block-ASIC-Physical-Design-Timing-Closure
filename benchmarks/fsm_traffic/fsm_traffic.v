// Traffic Light Controller FSM
// Real synthesizable digital benchmark for EDA-Genius

module fsm_traffic #(
    parameter CLK_FREQ_HZ = 10000000,
    parameter SEC_MAIN_GREEN = 30,
    parameter SEC_SIDE_GREEN = 15,
    parameter SEC_YELLOW     = 3
)(
    input  wire       clk,
    input  wire       rst_n,
    input  wire       pedestrian_req,
    input  wire       emergency_sensor,
    output reg  [2:0] main_lights,   // {Red, Yellow, Green}
    output reg  [2:0] side_lights,   // {Red, Yellow, Green}
    output reg        walk_light,
    output reg  [3:0] debug_state
);

    localparam S_MAIN_GREEN  = 4'd0;
    localparam S_MAIN_YELLOW = 4'd1;
    localparam S_ALL_RED_1   = 4'd2;
    localparam S_SIDE_GREEN  = 4'd3;
    localparam S_SIDE_YELLOW = 4'd4;
    localparam S_ALL_RED_2   = 4'd5;
    localparam S_PEDESTRIAN  = 4'd6;
    localparam S_EMERGENCY   = 4'd7;

    reg [3:0]  state, next_state;
    reg [31:0] timer_cnt;
    wire       timer_done;

    reg [31:0] timeout_val;

    always @(*) begin
        case (state)
            S_MAIN_GREEN:  timeout_val = SEC_MAIN_GREEN;
            S_MAIN_YELLOW: timeout_val = SEC_YELLOW;
            S_SIDE_GREEN:  timeout_val = SEC_SIDE_GREEN;
            S_SIDE_YELLOW: timeout_val = SEC_YELLOW;
            S_PEDESTRIAN:  timeout_val = 10;
            default:       timeout_val = 2; // All-red clearance
        endcase
    end

    assign timer_done = (timer_cnt >= timeout_val);

    always @(posedge clk or negedge rst_n) begin
        if (!rst_n) begin
            state     <= S_MAIN_GREEN;
            timer_cnt <= 32'd0;
        end else if (emergency_sensor) begin
            state     <= S_EMERGENCY;
            timer_cnt <= 32'd0;
        end else if (state == S_EMERGENCY) begin
            if (!emergency_sensor) begin
                state     <= S_MAIN_GREEN;
                timer_cnt <= 32'd0;
            end
        end else if (timer_done) begin
            state     <= next_state;
            timer_cnt <= 32'd0;
        end else begin
            timer_cnt <= timer_cnt + 1;
        end
    end

    always @(*) begin
        next_state = state;
        case (state)
            S_MAIN_GREEN:  next_state = S_MAIN_YELLOW;
            S_MAIN_YELLOW: next_state = S_ALL_RED_1;
            S_ALL_RED_1:   next_state = pedestrian_req ? S_PEDESTRIAN : S_SIDE_GREEN;
            S_SIDE_GREEN:  next_state = S_SIDE_YELLOW;
            S_SIDE_YELLOW: next_state = S_ALL_RED_2;
            S_ALL_RED_2:   next_state = S_MAIN_GREEN;
            S_PEDESTRIAN:  next_state = S_SIDE_GREEN;
            S_EMERGENCY:   next_state = S_MAIN_GREEN;
            default:       next_state = S_MAIN_GREEN;
        endcase
    end

    always @(*) begin
        main_lights = 3'b100; // Red
        side_lights = 3'b100; // Red
        walk_light  = 1'b0;
        debug_state = state;

        case (state)
            S_MAIN_GREEN: begin
                main_lights = 3'b001; // Green
                side_lights = 3'b100; // Red
            end
            S_MAIN_YELLOW: begin
                main_lights = 3'b010; // Yellow
                side_lights = 3'b100; // Red
            end
            S_ALL_RED_1, S_ALL_RED_2: begin
                main_lights = 3'b100; // Red
                side_lights = 3'b100; // Red
            end
            S_SIDE_GREEN: begin
                main_lights = 3'b100; // Red
                side_lights = 3'b001; // Green
            end
            S_SIDE_YELLOW: begin
                main_lights = 3'b100; // Red
                side_lights = 3'b010; // Yellow
            end
            S_PEDESTRIAN: begin
                main_lights = 3'b100;
                side_lights = 3'b100;
                walk_light  = 1'b1;
            end
            S_EMERGENCY: begin
                main_lights = 3'b010; // Flashing / yellow priority
                side_lights = 3'b100;
            end
            default: begin
                main_lights = 3'b100;
                side_lights = 3'b100;
            end
        endcase
    end

endmodule
