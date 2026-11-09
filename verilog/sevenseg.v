
`timescale 1ns / 1ps

module sevenseg #(
    parameter integer REFRESH_DIV = 25000,
    parameter integer PAGE_CYCLES = 100000000
)(
    input wire clk,
    input wire [7:0] label,
    input wire [15:0] value,
    output reg [6:0] seg,
    output reg [3:0] an,
    output wire dp
);

    // Basys 3 segments and digit enables are active-low.
    assign dp = 1'b1;  // Decimal point OFF

    // Switch rapidly between the four physical digits.
    localparam integer REF_BITS =
        (REFRESH_DIV <= 1) ? 1 : $clog2(REFRESH_DIV);

    reg [REF_BITS-1:0] refresh_count = 0;
    reg [1:0] digit = 0;

    always @(posedge clk) begin
        if (refresh_count == REFRESH_DIV - 1) begin
            refresh_count <= 0;
            digit <= digit + 1'b1;
        end else begin
            refresh_count <= refresh_count + 1'b1;
        end
    end

    // Convert a 16-bit binary value to decimal BCD.
    // Five decimal digits support values from 0 to 65535.
    reg [19:0] bcd;
    integer i, j;

    always @(*) begin
        bcd = 0;

        for (i = 15; i >= 0; i = i - 1) begin
            for (j = 0; j < 5; j = j + 1) begin
                if (bcd[j*4 +: 4] >= 5)
                    bcd[j*4 +: 4] =
                        bcd[j*4 +: 4] + 4'd3;
            end

            bcd = {bcd[18:0], value[i]};
        end
    end

    // Values above 999 need a second display page.
    localparam integer PAGE_BITS =
        (PAGE_CYCLES <= 1) ? 1 : $clog2(PAGE_CYCLES);

    reg [PAGE_BITS-1:0] page_count = 0;
    reg high_page = 0;

    wire large_value = (value >= 16'd1000);

    always @(posedge clk) begin
        if (!large_value) begin
            page_count <= 0;
            high_page <= 0;
        end else if (page_count == PAGE_CYCLES - 1) begin
            page_count <= 0;
            high_page <= ~high_page;
        end else begin
            page_count <= page_count + 1'b1;
        end
    end

    // Determine which character appears on each digit.
    reg [7:0] left_char, hundreds, tens, ones;

    always @(*) begin
        left_char = label;
        hundreds = " ";
        tens = " ";
        ones = "0" + {4'b0, bcd[3:0]};

        if (large_value && high_page) begin
            // Example: 12345 -> H 12
            left_char = "H";
            tens = (bcd[19:16] != 0) ?
                ("0" + {4'b0, bcd[19:16]}) : " ";
            ones = "0" + {4'b0, bcd[15:12]};
        end else begin
            // Example: 345 -> X345
            hundreds = (large_value || value >= 100) ?
                ("0" + {4'b0, bcd[11:8]}) : " ";

            tens = (large_value || value >= 10) ?
                ("0" + {4'b0, bcd[7:4]}) : " ";
        end
    end

    // Activate one digit at a time.
    reg [7:0] current_char;

    always @(*) begin
        an = 4'b1111;
        current_char = " ";

        case (digit)
            2'd0: begin
                an = 4'b1110;
                current_char = ones;
            end

            2'd1: begin
                an = 4'b1101;
                current_char = tens;
            end

            2'd2: begin
                an = 4'b1011;
                current_char = hundreds;
            end

            2'd3: begin
                an = 4'b0111;
                current_char = left_char;
            end
        endcase

        seg = encode(current_char);
    end

    // Decode a character into seven illuminated segments.
    // Bits are {g,f,e,d,c,b,a}; 0 = segment ON.
    function [6:0] encode;
        input [7:0] ch;
        begin
            case (ch)
                "0": encode = 7'b1000000;
                "1": encode = 7'b1111001;
                "2": encode = 7'b0100100;
                "3": encode = 7'b0110000;
                "4": encode = 7'b0011001;
                "5": encode = 7'b0010010;
                "6": encode = 7'b0000010;
                "7": encode = 7'b1111000;
                "8": encode = 7'b0000000;
                "9": encode = 7'b0010000;

                "A": encode = 7'b0001000;
                "a": encode = 7'b0100000;
                "B", "b": encode = 7'b0000011;
                "C", "c": encode = 7'b1000110;
                "D", "d": encode = 7'b0100001;
                "E", "e": encode = 7'b0000110;
                "F", "f": encode = 7'b0001110;
                "G", "g": encode = 7'b1000010;
                "H", "h", "X", "x", "K", "k", "M", "m":
                    encode = 7'b0001001;
                "I", "i": encode = 7'b1111001;
                "J", "j": encode = 7'b1100001;
                "L", "l": encode = 7'b1000111;
                "N", "n": encode = 7'b0101011;
                "O", "o": encode = 7'b0100011;
                "P", "p": encode = 7'b0001100;
                "Q", "q": encode = 7'b0011000;
                "R", "r": encode = 7'b0101111;
                "S", "s": encode = 7'b0010010;
                "T", "t": encode = 7'b0000111;
                "U", "u", "V", "v", "W", "w":
                    encode = 7'b1000001;
                "Y", "y": encode = 7'b0010001;
                "Z", "z": encode = 7'b0100100;

                "-": encode = 7'b0111111;
                default: encode = 7'b1111111;
            endcase
        end
    endfunction

endmodule
