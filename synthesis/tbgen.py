"""Automatically generate a self-checking Vivado/Verilog testbench for synth_core.

Inputs are the EXISTING scheduler.schedule() result and optional primary input values.
No equation names, selector numbers, FU allocation, or cycle numbers are hardcoded.

    write_testbench(current_schedule, 'verilog/testbench/tb_synth_core.v', {'A':3,'B':2})

Generated testbench checks input storage, FSM states, FU outputs in the active
cycle, intermediate output registers, final registers, DONE, and reset.
The post-DONE FU checks are enabled only if codegen.view_list maps a unit to
its '_observed' (latched last result) wire.
"""
# Used AI

from pathlib import Path
import random

from synthesis.codegen import view_list, unit_list

OP_SYMBOL = {"add": "+", "sub": "-", "mul": "*"}


def _values_for_inputs(inputs, supplied):
    """Convert A=3 and/or A_0=3 into {A_0:3}, rejecting mistaken names."""
    supplied = supplied or {}
    if not isinstance(supplied, dict):
        raise ValueError("input values must be a dictionary such as {'A': 3, 'B': 2}")
    aliases = {}
    for name in inputs:
        short = name[:-2] if name.endswith("_0") else name
        aliases[short] = name
        aliases[name] = name
    unknown = set(supplied) - set(aliases)
    if unknown:
        raise ValueError("Unknown input name(s): " + ", ".join(sorted(unknown)))
    resolved = {}
    for original, val in supplied.items():
        if type(val) is not int or not (0 <= val <= 255):
            raise ValueError(f"{original}: input switch value must be from 0 through 255")
        name = aliases[original]
        if name in resolved and resolved[name] != val:
            raise ValueError(f"Conflicting values supplied for {name}")
        resolved[name] = val
    return resolved


def _reference(schedule, inputs, width=16):
    """A small unsigned golden model, with simultaneous per-cycle writes."""
    regs = dict(inputs)
    mask = (1 << width) - 1
    by_cycle = {}
    overflow = []
    fu_last = {}
    for cycle in range(1, schedule["num_cycles"] + 1):
        snapshot = dict(regs)
        updates = {}
        op_details = []
        busy = set()
        for op in schedule["ops"]:
            if op["cycle"] != cycle:
                continue
            if op["unit"] in busy:
                raise ValueError(f"FU {op['unit']} assigned twice during cycle {cycle}")
            busy.add(op["unit"])
            def read(item):
                if str(item).isdigit():
                    return int(item)
                if item not in snapshot:
                    raise ValueError(f"Uninitialized {item} in cycle {cycle}")
                return snapshot[item]
            a, b = read(op["a"]), read(op["b"])
            kind = op["op"]
            if kind == "add":
                raw = a + b
            elif kind == "sub":
                raw = a - b
            elif kind == "mul":
                raw = a * b
            else:
                raise ValueError(f"Unsupported operation {kind}")
            if raw < 0:
                raise ValueError(
                    f"Cycle {cycle}: {op['dest']} = {a} {OP_SYMBOL[kind]} {b} "
                    f"= {raw} (negative). Choose nonnegative test inputs."
                )
            val = raw & mask
            if val != raw:
                overflow.append(f"{op['dest']}: {raw} wraps to {val} (unsigned {width}-bit)")
            updates[op["dest"]] = val
            fu_last[op["unit"]] = val
            op_details.append((op, a, b, val))
        regs.update(updates)
        by_cycle[cycle] = op_details
    return regs, by_cycle, fu_last, overflow


def _automatic_cases(schedule, supplied, width):
    """Produce 2 meaningful vectors; search for unsigned-safe inputs."""
    inputs = list(schedule["inputs"])
    selected = _values_for_inputs(inputs, supplied)
    rng = random.Random(551)
    results = []
    # Keep first sample intuitive for the currently used X/Y/Z/Q example.
    first = {name: selected.get(name, [3, 2, 4, 6, 5][i % 5])
             for i, name in enumerate(inputs)}

    def choose(seed, preserve):
        last_error = None
        for attempt in range(2400):
            if attempt == 0:
                candidate = dict(seed)
            elif attempt == 1:
                candidate = {name: seed.get(name, 0) for name in inputs}
                candidate.update({name: 0 for name in inputs if name not in preserve})
            else:
                candidate = {name: preserve.get(name, rng.randint(0, 12)) for name in inputs}
            try:
                model = _reference(schedule, candidate, width)
            except ValueError as exc:
                last_error = exc
                continue
            return candidate, model
        raise ValueError(
            "Could not find nonnegative results for the supplied inputs. "
            f"Last reason: {last_error}"
        )

    # Supplied inputs are authoritative; a user shouldn't be surprised by changed values.
    if selected:
        if len(selected) != len(inputs):
            # Fill only unspecified inputs while keeping all user-entered values.
            case1, model1 = choose(first, selected)
        else:
            case1 = dict(selected)
            model1 = _reference(schedule, case1, width)
    else:
        case1, model1 = choose(first, {})
    results.append((case1, model1))

    for variant in range(2):
        seed = {name: [10, 4, 8, 5, 7][i % 5] if variant == 0 else (i + 1)
                for i, name in enumerate(inputs)}
        second, model2 = choose(seed, {})
        if second != case1:
            results.append((second, model2))
            break
    # One-case fallback if only a single unsigned-valid input assignment exists.
    return results


def generate_testbench(schedule, input_values=None, width=16):
    """Return Verilog-2001 testbench source (works in Vivado XSim)."""
    if not schedule or not schedule.get("ops"):
        raise ValueError("Please schedule some equations first")
    if width != 16:
        raise ValueError("Current synth_core uses 16-bit data; width=16 is required")
    if schedule["num_cycles"] > 30:
        raise ValueError("The 5-bit FSM supports a maximum of 30 operation cycles")
    inputs = list(schedule["inputs"])
    if len(inputs) > 64:
        raise ValueError("More than 64 external inputs cannot fit in 6-bit in_sel")
    entries = list(view_list(schedule))
    expected_count = sum(schedule["units"].values()) + len(schedule["ops"]) + len(inputs)
    if expected_count > 128 or len(entries) != expected_count:
        raise ValueError(
            f"{expected_count} observations need more than 128 fu_sel positions. "
            "Change the selector width in codegen.py and top.v before testing."
        )
    names_to_id = {name: i for i, (name, _signal) in enumerate(entries)}
    for name in inputs + [op["dest"] for op in schedule["ops"]] + unit_list(schedule):
        if name not in names_to_id:
            raise ValueError(f"Missing display selector for {name}")
    units_latched = {
        name for name, sig in entries if name in unit_list(schedule) and sig.endswith("_observed")
    }
    cases = _automatic_cases(schedule, input_values, width)

    lines = [
        "`timescale 1ns / 1ps",
        "// AUTO-GENERATED by synthesis/tbgen.py. Do not edit by hand.",
        f"// Mode: {schedule['mode']}; scheduled cycles: {schedule['num_cycles']}",
        "// Rebuild this testbench when examples.txt or scheduling mode changes.",
        "// Selectors (exactly from synthesis.codegen.view_list):",
    ]
    for idx, (name, signal) in enumerate(entries):
        lines.append(f"// fu_sel {idx:2d} = {name} ({signal})")
    for idx, name in enumerate(inputs):
        lines.append(f"// in_sel {idx:2d} = {name}")
    lines.extend([
        "",
        "module tb_synth_core;",
        "    reg clk = 0;",
        "    reg rst = 0;",
        "    reg step = 0;",
        "    reg [5:0] in_sel = 0;",
        "    reg [7:0] in_val = 0;",
        "    reg in_write = 0;",
        "    reg [6:0] fu_sel = 0;",
        "    wire [15:0] disp_val;",
        "    wire [4:0] state;",
        "    wire done;",
        "    integer checks = 0;",
        "",
        "    synth_core #(.W(16)) dut (",
        "        .clk(clk), .rst(rst), .step(step),",
        "        .in_sel(in_sel), .in_val(in_val), .in_write(in_write),",
        "        .fu_sel(fu_sel), .disp_val(disp_val),",
        "        .state(state), .done(done)",
        "    );",
        "    always #5 clk = ~clk;  // 100 MHz",
        "",
        "    task reset_core;",
        "    begin",
        "        @(negedge clk); rst = 1; step = 0; in_write = 0;",
        "        @(negedge clk); rst = 0; #1;",
        "        if (state !== 5'd0 || done !== 1'b0)",
        "            $fatal(1, \"FAIL: reset did not return to LOAD\");",
        "    end",
        "    endtask",
        "",
        "    task load_input;",
        "        input [5:0] sel;",
        "        input [7:0] value;",
        "    begin",
        "        @(negedge clk); in_sel = sel; in_val = value; in_write = 1;",
        "        @(negedge clk); in_write = 0; #1;",
        "    end",
        "    endtask",
        "",
        "    task press_step;",
        "    begin",
        "        @(negedge clk); step = 1;",
        "        @(negedge clk); step = 0; #1;",
        "    end",
        "    endtask",
        "",
        "    task check_value;",
        "        input [6:0] selector;",
        "        input [15:0] expected;",
        "        input [8*80-1:0] description;",
        "    begin",
        "        fu_sel = selector; #1;",
        "        if (disp_val !== expected) begin",
        "            $display(\"FAIL: %0s (fu_sel=%0d): got %0d (%h), expected %0d (%h), state=%0d\",",
        "                     description, selector, disp_val, disp_val, expected, expected, state);",
        "            $fatal(1, \"Incorrect synth_core output\");",
        "        end",
        "        checks = checks + 1;",
        "    end",
        "    endtask",
        "",
        "    task check_state;",
        "        input [4:0] expected;",
        "    begin",
        "        if (state !== expected)",
        "            $fatal(1, \"Wrong state: got %0d, expected %0d\", state, expected);",
        "        if (done !== (expected == 5'd" + str(schedule['num_cycles']+1) + "))",
        "            $fatal(1, \"DONE flag mismatch in state %0d\", state);",
        "        checks = checks + 1;",
        "    end",
        "    endtask",
        "",
        "    initial begin",
        "        // Watchdog: catches stalled or nonterminating tests.",
        "        // This delay is greater than all generated stimulus durations.",
        "        // (Set according to number of test cases, inputs, cycles.)",
        f"        #({(len(cases) * (len(inputs) + schedule['num_cycles'] + 12) + 30) * 30});",
        "        $fatal(1, \"TIMEOUT: generated testbench did not finish\");",
        "    end",
        "",
        "    initial begin",
        f"        $display(\"AUTO TESTBENCH: {len(cases)} vectors, {schedule['num_cycles']} arithmetic cycles\");",
    ])

    for case_i, (initial, model) in enumerate(cases, 1):
        registers, cycles, fu_last, overflow = model
        lines.append("")
        lines.append(f"        // ------------------- TEST VECTOR {case_i} -------------------")
        lines.append(f"        $display(\"TEST {case_i} INPUTS: " + ", ".join(
            f"{name}={initial[name]}" for name in inputs
        ) + "\");")
        lines.append("        reset_core;")
        lines.append("        // Reset must clear every saved input and result register.")
        for saved in inputs + [op["dest"] for op in schedule["ops"]]:
            lines.append(f"        check_value(7'd{names_to_id[saved]}, 16'd0, \"reset {saved}\");")
        for idx, name in enumerate(inputs):
            lines.append(f"        load_input(6'd{idx}, 8'd{initial[name]});")
            lines.append(f"        check_value(7'd{names_to_id[name]}, 16'd{initial[name]}, \"loaded {name}\");")
        lines.append("        check_state(5'd0);")
        lines.append("        press_step;  // LOAD -> arithmetic cycle 1")
        lines.append("        check_state(5'd1);")
        for cycle in range(1, schedule["num_cycles"] + 1):
            lines.append(f"        // Arithmetic cycle {cycle}: check active FU outputs, then write registers.")
            for op, a, b, val in cycles[cycle]:
                lines.append(f"        check_value(7'd{names_to_id[op['unit']]}, 16'd{val}, \"cycle {cycle} {op['unit']}: {op['dest']}\");")
            lines.append("        press_step;")
            lines.append(f"        check_state(5'd{cycle+1});")
            for op, a, b, val in cycles[cycle]:
                lines.append(f"        check_value(7'd{names_to_id[op['dest']]}, 16'd{val}, \"cycle {cycle} stored {op['dest']}\");")
        lines.append("        if (done !== 1'b1) $fatal(1, \"DONE not asserted\");")
        lines.append("        // Verify every final visible register, including intermediate SSA results.")
        for name in inputs + [op["dest"] for op in schedule["ops"]]:
            lines.append(f"        check_value(7'd{names_to_id[name]}, 16'd{registers[name]}, \"final {name}\");")
        if units_latched:
            lines.append("        // Updated FU observation RTL remembers final result even at DONE.")
            for unit in unit_list(schedule):
                if unit in units_latched and unit in fu_last:
                    lines.append(f"        check_value(7'd{names_to_id[unit]}, 16'd{fu_last[unit]}, \"last {unit}\");")
        if inputs:
            lines.append("        // Inputs cannot be overwritten after leaving LOAD mode.")
            lines.append(f"        load_input(6'd0, 8'd255);")
            lines.append(f"        check_value(7'd{names_to_id[inputs[0]]}, 16'd{initial[inputs[0]]}, \"write ignored after DONE\");")
        lines.append("        press_step;  // DONE should ignore extra steps")
        lines.append(f"        check_state(5'd{schedule['num_cycles']+1});")
        lines.append(f"        $display(\"TEST {case_i} PASSED\");")
        if overflow:
            for note in overflow:
                lines.append("        // NOTE: " + note)
    lines.extend([
        "        $display(\"ALL SYNTH_CORE TESTS PASSED (%0d checks)\", checks);",
        "        $finish;",
        "    end",
        "endmodule",
    ])
    return "\n".join(lines) + "\n"


def write_testbench(schedule, filename="verilog/testbench/tb_synth_core.v", input_values=None, width=16):
    """Write the generated self-checking testbench and return its path."""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(generate_testbench(schedule, input_values, width), encoding="utf-8")
    return path
