
module top #(
    parameter integer DEBOUNCE_CYCLES = 1000000,
    parameter integer DISPLAY_REFRESH_DIV = 25000,
    parameter integer DISPLAY_PAGE_CYCLES = 100000000
)(
    input wire clk,
    input wire [15:0] sw,
    input wire btnC,
    input wire btnU,
    input wire btnD,
    output wire [15:0] led,
    output wire [6:0] seg,
    output wire [3:0] an,
    output wire dp
);

    // Create one clean pulse for each button press
    wire load_pulse;
    wire step_pulse;
    wire reset_pulse;

    button_control #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) load_button (
        .clk(clk),
        .btn(btnC),
        .pulse(load_pulse)
    );

    button_control #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) step_button (
        .clk(clk),
        .btn(btnU),
        .pulse(step_pulse)
    );

    button_control #(.DEBOUNCE_CYCLES(DEBOUNCE_CYCLES)) reset_button (
        .clk(clk),
        .btn(btnD),
        .pulse(reset_pulse)
    );

    // Choose operating mode using SW15 and SW14
    wire [1:0] mode = sw[15:14];

    wire load_mode = (mode == 2'b00);
    wire run_mode = (mode == 2'b01);

    // Only load inputs in LOAD mode
    wire in_write = load_pulse && load_mode;

    // Only advance calculations in RUN mode
    wire step = step_pulse && run_mode;

    // Outputs from our generated circuit
    wire [15:0] disp_val;
    wire [4:0] state;
    wire done;

    // Connect the generated hardware
    synth_core #(.W(16)) core (
        .clk(clk),
        .rst(reset_pulse),
        .step(step),
        .in_sel(sw[13:8]),
        .in_val(sw[7:0]),
        .in_write(in_write),
        .fu_sel({sw[13], sw[7], sw[12:8]}),
        .disp_val(disp_val),
        .state(state),
        .done(done)
    );

    // Show input preview in LOAD mode
    // Show calculated output in other modes
    assign led = load_mode ? {8'b0, sw[7:0]} : disp_val;

    // ----------------------------------------
    // Seven-segment variable label
    // ----------------------------------------

    wire [7:0] current_label;

    display_labels labels (
        .load_mode(load_mode),
        .in_sel(sw[13:8]),
        .fu_sel({sw[13], sw[7], sw[12:8]}),
        .label(current_label)
    );

    // ----------------------------------------
    // Seven-segment numerical display
    // ----------------------------------------
    // Shows the current FSM state.
    // LOAD and VIEW keep their existing display behavior.
    wire [7:0] sevenseg_label =
        run_mode ? "C" : current_label;

    wire [15:0] sevenseg_value =
        run_mode ? {11'b0, state} : led;

    sevenseg #(
        .REFRESH_DIV(DISPLAY_REFRESH_DIV),
        .PAGE_CYCLES(DISPLAY_PAGE_CYCLES)
    ) display (
        .clk(clk),
        .label(sevenseg_label),
        .value(sevenseg_value),
        .show_done(run_mode && done),
        .seg(seg),
        .an(an),
        .dp(dp)
    );

endmodule
