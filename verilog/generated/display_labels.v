// AUTO-GENERATED. Do not edit.
module display_labels(
    input wire load_mode,
    input wire [5:0] in_sel,
    input wire [6:0] fu_sel,
    output reg [7:0] label
);
always @(*) begin
    label = 8'd45;
    if (load_mode) begin
        case (in_sel)
            6'd0: label = 8'd65; // A_0
            6'd1: label = 8'd66; // B_0
            default: label = 8'd45;
        endcase
    end else begin
        case (fu_sel)
            7'd0: label = 8'd97; // add0
            7'd1: label = 8'd115; // sub0
            7'd2: label = 8'd112; // mul0
            7'd3: label = 8'd88; // X_1
            7'd4: label = 8'd89; // Y_1
            7'd5: label = 8'd90; // Z_1
            7'd6: label = 8'd87; // W_1
            7'd7: label = 8'd65; // A_0
            7'd8: label = 8'd66; // B_0
            default: label = 8'd45;
        endcase
    end
end
endmodule
