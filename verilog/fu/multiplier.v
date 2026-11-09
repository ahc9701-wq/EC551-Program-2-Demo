// Section 5: functional unit, y = a * b (truncated to W bits)
module multiplier #(parameter W = 16) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] y
);
    assign y = a * b;
endmodule
