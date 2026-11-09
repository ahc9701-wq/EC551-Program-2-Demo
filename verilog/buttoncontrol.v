
module button_control #(
    parameter integer DEBOUNCE_CYCLES = 1000000
)(
    input wire clk,
    input wire btn,
    output reg pulse = 0
);

    // Synchronize the physical button to the FPGA clock
    reg sync1 = 0;
    reg sync2 = 0;

    // Track whether the button is stably pressed or released
    reg stable = 0;
    reg [19:0] counter = 0;

    always @(posedge clk) begin

        sync1 <= btn;
        sync2 <= sync1;

        // Default: no button pulse
        pulse <= 0;

        if (sync2 == stable) begin
            counter <= 0;
        end
        else if (counter == DEBOUNCE_CYCLES - 1) begin

            // Button state has remained unchanged long enough
            stable <= sync2;
            counter <= 0;

            // Generate one pulse on a new button press
            if (sync2)
                pulse <= 1;
        end
        else begin
            counter <= counter + 1;
        end

    end

endmodule
