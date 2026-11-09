from synthesis.codegen import view_list, unit_list

# Used AI

def generate_display_labels(schedule):
    """
    Generate Verilog that maps selector IDs
    to variable and functional-unit labels.
    """

    views = view_list(schedule)
    units = set(unit_list(schedule))

    expected = (
        sum(schedule["units"].values())
        + len(schedule["ops"])
        + len(schedule["inputs"])
    )

    # Current FPGA output selector has 5 bits.
    if expected > 128 or len(views) != expected:
        raise ValueError(
            f"{expected} outputs exceed the 128-ID limit."
        )

    if len(schedule["inputs"]) > 64:
        raise ValueError(
            "Too many inputs for the 6-bit input selector."
        )

    def character(name):

        # Functional units have their own labels.
        if name in units:
            return {
                "add": "a",
                "sub": "s",
                "mul": "p"
            }[name[:3]]

        # Example: X_1 becomes X.
        first = name.split("_")[0][:1]

        if first.isascii() and first.isalpha():
            return first

        return "-"

    lines = [
        "// AUTO-GENERATED. Do not edit.",
        "module display_labels(",
        "    input wire load_mode,",
        "    input wire [5:0] in_sel,",
        "    input wire [6:0] fu_sel,",
        "    output reg [7:0] label",
        ");",
        "always @(*) begin",
        "    label = 8'd45;",
        "    if (load_mode) begin",
        "        case (in_sel)"
    ]

    # Input labels used during LOAD mode.
    for i, name in enumerate(schedule["inputs"]):

        code = ord(character(name))

        lines.append(
            f"            6'd{i}: label = 8'd{code}; // {name}"
        )

    lines += [
        "            default: label = 8'd45;",
        "        endcase",
        "    end else begin",
        "        case (fu_sel)"
    ]

    # Output labels used during RUN / VIEW.
    for i, (name, _) in enumerate(views):

        code = ord(character(name))

        lines.append(
            f"            7'd{i}: label = 8'd{code}; // {name}"
        )

    lines += [
        "            default: label = 8'd45;",
        "        endcase",
        "    end",
        "end",
        "endmodule",
        ""
    ]

    return "\n".join(lines)