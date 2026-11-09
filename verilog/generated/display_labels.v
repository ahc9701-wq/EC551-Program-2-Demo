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
            6'd0: label = 8'd65; // A0_0
            6'd1: label = 8'd66; // B0_0
            6'd2: label = 8'd65; // A1_0
            6'd3: label = 8'd66; // B1_0
            6'd4: label = 8'd65; // A2_0
            6'd5: label = 8'd66; // B2_0
            6'd6: label = 8'd65; // A3_0
            6'd7: label = 8'd66; // B3_0
            6'd8: label = 8'd65; // A4_0
            6'd9: label = 8'd66; // B4_0
            6'd10: label = 8'd65; // A5_0
            6'd11: label = 8'd66; // B5_0
            6'd12: label = 8'd65; // A6_0
            6'd13: label = 8'd66; // B6_0
            6'd14: label = 8'd65; // A7_0
            6'd15: label = 8'd66; // B7_0
            6'd16: label = 8'd65; // A8_0
            6'd17: label = 8'd66; // B8_0
            6'd18: label = 8'd65; // A9_0
            6'd19: label = 8'd66; // B9_0
            6'd20: label = 8'd65; // A10_0
            6'd21: label = 8'd66; // B10_0
            6'd22: label = 8'd65; // A11_0
            6'd23: label = 8'd66; // B11_0
            6'd24: label = 8'd65; // A12_0
            6'd25: label = 8'd66; // B12_0
            6'd26: label = 8'd65; // A13_0
            6'd27: label = 8'd66; // B13_0
            6'd28: label = 8'd65; // A14_0
            6'd29: label = 8'd66; // B14_0
            6'd30: label = 8'd65; // A15_0
            6'd31: label = 8'd66; // B15_0
            6'd32: label = 8'd65; // A16_0
            6'd33: label = 8'd66; // B16_0
            6'd34: label = 8'd65; // A17_0
            6'd35: label = 8'd66; // B17_0
            6'd36: label = 8'd65; // A18_0
            6'd37: label = 8'd66; // B18_0
            6'd38: label = 8'd65; // A19_0
            6'd39: label = 8'd66; // B19_0
            default: label = 8'd45;
        endcase
    end else begin
        case (fu_sel)
            7'd0: label = 8'd97; // add0
            7'd1: label = 8'd97; // add1
            7'd2: label = 8'd97; // add2
            7'd3: label = 8'd97; // add3
            7'd4: label = 8'd97; // add4
            7'd5: label = 8'd97; // add5
            7'd6: label = 8'd97; // add6
            7'd7: label = 8'd97; // add7
            7'd8: label = 8'd97; // add8
            7'd9: label = 8'd97; // add9
            7'd10: label = 8'd97; // add10
            7'd11: label = 8'd97; // add11
            7'd12: label = 8'd97; // add12
            7'd13: label = 8'd97; // add13
            7'd14: label = 8'd97; // add14
            7'd15: label = 8'd97; // add15
            7'd16: label = 8'd97; // add16
            7'd17: label = 8'd97; // add17
            7'd18: label = 8'd97; // add18
            7'd19: label = 8'd97; // add19
            7'd20: label = 8'd88; // X0_1
            7'd21: label = 8'd88; // X1_1
            7'd22: label = 8'd88; // X2_1
            7'd23: label = 8'd88; // X3_1
            7'd24: label = 8'd88; // X4_1
            7'd25: label = 8'd88; // X5_1
            7'd26: label = 8'd88; // X6_1
            7'd27: label = 8'd88; // X7_1
            7'd28: label = 8'd88; // X8_1
            7'd29: label = 8'd88; // X9_1
            7'd30: label = 8'd88; // X10_1
            7'd31: label = 8'd88; // X11_1
            7'd32: label = 8'd88; // X12_1
            7'd33: label = 8'd88; // X13_1
            7'd34: label = 8'd88; // X14_1
            7'd35: label = 8'd88; // X15_1
            7'd36: label = 8'd88; // X16_1
            7'd37: label = 8'd88; // X17_1
            7'd38: label = 8'd88; // X18_1
            7'd39: label = 8'd88; // X19_1
            7'd40: label = 8'd65; // A0_0
            7'd41: label = 8'd66; // B0_0
            7'd42: label = 8'd65; // A1_0
            7'd43: label = 8'd66; // B1_0
            7'd44: label = 8'd65; // A2_0
            7'd45: label = 8'd66; // B2_0
            7'd46: label = 8'd65; // A3_0
            7'd47: label = 8'd66; // B3_0
            7'd48: label = 8'd65; // A4_0
            7'd49: label = 8'd66; // B4_0
            7'd50: label = 8'd65; // A5_0
            7'd51: label = 8'd66; // B5_0
            7'd52: label = 8'd65; // A6_0
            7'd53: label = 8'd66; // B6_0
            7'd54: label = 8'd65; // A7_0
            7'd55: label = 8'd66; // B7_0
            7'd56: label = 8'd65; // A8_0
            7'd57: label = 8'd66; // B8_0
            7'd58: label = 8'd65; // A9_0
            7'd59: label = 8'd66; // B9_0
            7'd60: label = 8'd65; // A10_0
            7'd61: label = 8'd66; // B10_0
            7'd62: label = 8'd65; // A11_0
            7'd63: label = 8'd66; // B11_0
            7'd64: label = 8'd65; // A12_0
            7'd65: label = 8'd66; // B12_0
            7'd66: label = 8'd65; // A13_0
            7'd67: label = 8'd66; // B13_0
            7'd68: label = 8'd65; // A14_0
            7'd69: label = 8'd66; // B14_0
            7'd70: label = 8'd65; // A15_0
            7'd71: label = 8'd66; // B15_0
            7'd72: label = 8'd65; // A16_0
            7'd73: label = 8'd66; // B16_0
            7'd74: label = 8'd65; // A17_0
            7'd75: label = 8'd66; // B17_0
            7'd76: label = 8'd65; // A18_0
            7'd77: label = 8'd66; // B18_0
            7'd78: label = 8'd65; // A19_0
            7'd79: label = 8'd66; // B19_0
            default: label = 8'd45;
        endcase
    end
end
endmodule
