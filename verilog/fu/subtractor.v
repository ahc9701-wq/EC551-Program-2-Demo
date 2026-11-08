// Section 5: functional unit, y = a - b (results are assumed non-negative)
module subtractor #(parameter W = 16) (
    input  wire [W-1:0] a,
    input  wire [W-1:0] b,
    output wire [W-1:0] y
);
    assign y = a - b;
endmodule
