"""Create an equation-specific, step-by-step Basys 3 FPGA demo checklist.

The report uses the *same* scheduling result and observation ordering as
synthesis.scheduler.schedule() and synthesis.codegen.view_list(). It does not
hardcode variable names, operation counts, or functional-unit IDs.

Example from your existing CLI:
    write_demo_guide(current_equations, current_schedule,
                     PROJECT_ROOT / 'demo.txt', {'A': 3, 'B': 2})

Board contract: top.v from EC551 Program 2 (LED-only version)
  SW15:14=00 LOAD, 01 RUN, 10 or 11 VIEW
  SW13:8 input ID; SW7:0 8-bit input value; SW12:8 observation ID
  BTNC load; BTNU step; BTND reset; LEDs show 16-bit output
"""
# Generated with AI
from pathlib import Path
from synthesis.codegen import view_list
from synthesis.dag import OP_SYMBOLS
from synthesis.ssa import convertssa


DATA_WIDTH = 16

# Used AI
def _equation(eq):
    return f"{eq['output']} = {eq['input1']} {eq['operator']} {eq['input2']}"


def _on_switches(word):
    names = [f"SW{bit}" for bit in range(15, -1, -1) if word & (1 << bit)]
    return ", ".join(names) if names else "NONE (all OFF)"


def _on_leds(value, width=DATA_WIDTH):
    names = [f"LED{bit}" for bit in range(width - 1, -1, -1) if value & (1 << bit)]
    return ", ".join(names) if names else "NONE (all OFF)"



def _switch_word(mode, selector=0, value=0):
    """
    LOAD: SW13..8 = input ID, SW7..0 = input value.
    VIEW: SW13 = bit 6, SW7 = bit 5,
          SW12..8 = bits 4..0.
    """

    if not 0 <= mode <= 3 or not 0 <= value <= 255:
        raise ValueError("Invalid board mode or input value")

    if mode in (2, 3):
        # VIEW mode: 7-bit selector
        if not 0 <= selector < 128 or value != 0:
            raise ValueError("Invalid 7-bit VIEW selector")

        word = (
            (mode << 14)
            | ((selector & 31) << 8)
            | (((selector >> 5) & 1) << 7)
            | (((selector >> 6) & 1) << 13)
        )

    else:
        # LOAD and RUN modes: original mapping
        if not 0 <= selector < 64:
            raise ValueError("Invalid 6-bit input selector")

        word = (mode << 14) | (selector << 8) | value

    return f"{word:016b}", _on_switches(word)

def _format_switches(mode, selector=0, value=0):
    word, on = _switch_word(mode, selector, value)
    return f"SW15..SW0 = {word} | ON: {on}"


def _input_values(inputs, provided):
    """Resolve user-entered names (A=3) to SSA input names (A_0=3)."""
    provided = provided or {}
    if not isinstance(provided, dict):
        raise ValueError("input_values must be a dictionary, e.g. {'A': 3, 'B': 2}")
    resolved = {}
    permitted = set()
    for input_name in inputs:
        alias = input_name[:-2] if input_name.endswith("_0") else input_name
        permitted.update((alias, input_name))
        if alias in provided and input_name in provided and alias != input_name:
            if provided[alias] != provided[input_name]:
                raise ValueError(f"Conflicting values for {alias} / {input_name}")
        value = provided.get(input_name, provided.get(alias))
        if value is None:
            continue
        if type(value) is not int or not 0 <= value <= 255:
            raise ValueError(f"{input_name} must be an integer from 0 to 255 (8-bit switches)")
        resolved[input_name] = value
    extra = set(provided) - permitted
    if extra:
        raise ValueError(f"Unknown external input name(s): {', '.join(sorted(extra))}")
    return resolved


def _evaluate(scheduled, initial, width):
    """Reference evaluator: reads previous-cycle register snapshot.

    Matches single-cycle scheduled operations and register writes. Results
    wrap modulo 2**width, as unsigned W-bit RTL does; negative results are
    outside the assignment's supported demo domain.
    """
    mask = (1 << width) - 1
    registers = dict(initial)
    fu_last = {}
    cycles = {}
    warnings = []
    for c in range(1, scheduled["num_cycles"] + 1):
        before = dict(registers)
        updates = {}
        details = []
        active_units = set()
        for op in scheduled["ops"]:
            if op["cycle"] != c:
                continue
            unit = op["unit"]
            if unit in active_units:
                raise ValueError(f"{unit} was allocated twice in cycle {c}")
            active_units.add(unit)
            def lookup(operand):
                if str(operand).isdigit():
                    return int(operand)
                if operand not in before:
                    raise ValueError(f"Uninitialized operand {operand} in cycle {c}")
                return before[operand]
            a = lookup(op["a"])
            b = lookup(op["b"])
            kind = op["op"]
            if kind == "add":
                exact = a + b
            elif kind == "sub":
                exact = a - b
            elif kind == "mul":
                exact = a * b
            else:
                raise ValueError(f"Unsupported operation: {kind}")
            if exact < 0:
                raise ValueError(
                    f"{op['dest']} = {a} {OP_SYMBOLS[kind]} {b} = {exact} is negative. "
                    "Choose nonnegative demo results as allowed by the assignment."
                )
            stored = exact & mask
            if stored != exact:
                warnings.append(
                    f"Cycle {c}, {op['dest']}: exact {exact}, stored {stored} "
                    f"(unsigned {width}-bit overflow)"
                )
            updates[op["dest"]] = stored
            fu_last[unit] = stored
            details.append((op, a, b, stored))
        registers.update(updates)
        cycles[c] = details
    return registers, fu_last, cycles, warnings


def make_demo_guide(equations, scheduled, input_values=None, width=DATA_WIDTH):
    """Return an actionable TXT checklist for *any supported* equation schedule.

    If all inputs are specified, includes numerical expectations and exact ON
    switch lists for LOAD, RUN and VIEW. Without input values it still prints
    variable/functional-unit IDs and the scheduled press-by-press sequence.
    """
    if not equations:
        raise ValueError("Load an equation file before generating the demo")
    if not scheduled or not scheduled.get("ops"):
        raise ValueError("Run 'schedule <mode>' before generating the demo")
    if width != 16:
        raise ValueError("Current top.v uses 16-bit LEDs; this guide expects width=16")

    inputs = list(scheduled["inputs"])
    input_map = _input_values(inputs, input_values)
    missing = [name for name in inputs if name not in input_map]
    complete = not missing
    views = view_list(scheduled)  # *Exact* same ordering as generated synth_core.v.
    selector_by_name = {name: i for i, (name, signal) in enumerate(views)}
    unit_names = {
        f"{kind}{i}"
        for kind in ("add", "sub", "mul")
        for i in range(scheduled["units"][kind])
    }
    total_views = sum(scheduled["units"].values()) + len(scheduled["ops"]) + len(inputs)
    if total_views > 128:
        overflow_note = (
            f"WARNING: {total_views} outputs exist but current synth_core.v supports "
            "only 128 VIEW IDs. Unlisted values cannot be selected on the board "
            "until codegen.py/top.v are expanded."
        )
    else:
        overflow_note = None

    if complete:
        registers, last_outputs, cycle_detail, warnings = _evaluate(scheduled, input_map, width)
        expected = {**registers, **last_outputs}
    else:
        registers, last_outputs, cycle_detail, warnings, expected = {}, {}, {}, [], {}

    lines = []
    def put(s=""):
        lines.append(s)
    def action(title, pattern, on, text, expected_value=None):
        put(f"[ ] {title}")
        put(f"    SW15..SW0: {pattern}")
        put(f"    SWITCHES ON: {on}")
        put(f"    ACTION: {text}")
        if expected_value is not None:
            put(f"    EXPECTED: {expected_value} decimal = {expected_value:016b} binary")
            put(f"    LEDs ON: {_on_leds(expected_value)}")
        put()

    put("=" * 79)
    put("EC551 | BASYS 3 | AUTOMATIC PHYSICAL DEMO CHECKLIST")
    put("=" * 79)
    put("Generated from the current equations + CURRENT schedule + RTL observation order.")
    put("Every SW pattern includes all 16 switches; 1 = ON, 0 = OFF.")
    put("Switches run SW15 (left) to SW0 (right). Press AND RELEASE buttons.")
    put("Numbers on SELECT switches are IDs, NOT the calculated values.")
    put()
    put("ORIGINAL EQUATIONS")
    for i, eq in enumerate(equations, 1):
        put(f"   {i}. {_equation(eq)}")
    put()
    put("SSA EQUATIONS")
    for i, eq in enumerate(convertssa(equations), 1):
        put(f"   {i}. {_equation(eq)}")
    put()
    put("SCHEDULE & RESOURCE ALLOCATION")
    put(f"   Mode: {scheduled['mode'].upper()}")
    put(f"   Resource limits: {scheduled.get('limits') or 'none'}")
    put(f"   Scheduled arithmetic cycles: {scheduled['num_cycles']}")
    put(f"   Physical resources: " + ", ".join(
        f"{scheduled['units'][kind]} {kind}" for kind in ("add", "sub", "mul")
    ))
    for c in range(1, scheduled["num_cycles"] + 1):
        ops = [op for op in scheduled["ops"] if op["cycle"] == c]
        if not ops:
            put(f"   Cycle {c}: (idle)")
        for op in ops:
            sym = OP_SYMBOLS[op["op"]]
            result = f" => {next(d[3] for d in cycle_detail[c] if d[0] is op)}" if complete else ""
            put(f"   Cycle {c}: {op['dest']} = {op['a']} {sym} {op['b']} [{op['unit']}]{result}")
    put()
    put("BOARD CONTROLS (matches current top.v)")
    put("   SW15..14 = 00 LOAD | 01 RUN | 10 VIEW | 11 VIEW")
    put("   SW13..8  = input ID during LOAD (6-bit)")
    put("   SW7..0   = input VALUE during LOAD (8-bit: 0..255)")
    put("   VIEW selector (7-bit): SW13=64, SW7=32, SW12..8=16,8,4,2,1")
    put("   BTNC = save selected input, BTNU = advance one FSM state")
    put("   BTND = reset (CLEARS inputs and results)")
    put("   LED15..0 = current input preview in LOAD; selected value otherwise")
    put("   Seven-segment left digit = selected variable or FU.")
    put("   Rightmost three digits = decimal value.")
    put("   Values above 999 alternate with an H thousands page.")
    put("   LEDs show the full binary value.")
    put()
    put("PREPARE THE BOARD")
    put("[ ] Run your CLI: load <equations.txt> ; schedule <mode> ; verilog ; demo ...")
    put("[ ] In Vivado: Design Top = top, valid basys3.xdc constraints.")
    put("[ ] Run synthesis -> implementation -> generate bitstream.")
    put("[ ] Hardware Manager -> Program Device with the NEW top.bit.")
    put("    The LEDs alone following switches do NOT prove it is our design;")
    put("    the original Digilent demo also does that.")
    put()

    put("STEP 1 - RESET")
    word, on = _switch_word(0)
    action("RESET FPGA", word, on, "Press and release BTND once. All registers clear.")

    put("STEP 2 - LOAD AND VERIFY EACH EXTERNAL INPUT")
    if not inputs:
        put("   No external input variables appear in this schedule.")
    for i, name in enumerate(inputs):
        alias = name[:-2] if name.endswith("_0") else name
        put(f"   INPUT ID {i}: {name} (enter as {alias}=number in CLI)")
        if name in input_map:
            val = input_map[name]
            word, on = _switch_word(0, i, val)
            action(f"LOAD {name} = {val}", word, on, "Press and release BTNC once.")
        else:
            word, on = _switch_word(0, i, 0)
            put(f"[ ] LOAD {name}: SW13..8={i:06b}; set SW15..14=00.")
            put(f"    Selector baseline (value 0): {word} | ON: {on}")
            put("    Then choose SW7..0 8-bit input VALUE (0..255), press BTNC.")
            put("    Exact SWITCHES ON and expected LEDs require demo A=3 B=2 etc.")
            put()
        view_id = selector_by_name.get(name)
        if view_id is not None:
            word, on = _switch_word(2, view_id)
            action(
                f"VERIFY STORED {name} (VIEW selector {view_id:07b})",
                word, on,
                "No button. SW6..0 OFF; SW7 is part of the VIEW selector. "
                "The LEDs should show the SAVED value. "
                "Return to LOAD (00) for next input.",
                input_map.get(name)
            )
        else:
            put(f"   WARNING: {name} does not have an accessible VIEW selector.\n")

    put("STEP 3 - RUN: BTNU PRESS BY PRESS")
    word, on = _switch_word(1)
    action("ENTER RUN MODE", word, on, "Turn ON only SW14; do not reset.")
    put("[ ] BTNU PRESS #1: START (state 0 -> state 1)")
    put("    Press and release UP once. No calculation result is stored yet.")
    put()
    for c in range(1, scheduled["num_cycles"] + 1):
        ops = [op for op in scheduled["ops"] if op["cycle"] == c]
        put(f"[ ] BTNU PRESS #{c + 1}: EXECUTE CYCLE {c} (state {c} -> {c + 1})")
        put(f"    Keep RUN: {word} | ON: {on}; press/release BTNU once.")
        if not ops:
            put("    No operation this cycle (idle scheduling slot).")
        for op in ops:
            sym = OP_SYMBOLS[op["op"]]
            line = f"    {op['dest']} = {op['a']} {sym} {op['b']} via {op['unit']}"
            if complete:
                detail = next(d for d in cycle_detail[c] if d[0] is op)
                line += f" => {detail[1]} {sym} {detail[2]} = {detail[3]}"
            put(line)
        put("    OPTIONAL CHECK: switch temporarily to VIEW (10), inspect:")
        for op in ops:
            sel = selector_by_name.get(op["dest"])
            if sel is None:
                put(f"       {op['dest']}: UNAVAILABLE (128-entry selector limit)")
                continue
            vword, von = _switch_word(2, sel)
            desc = f" {op['dest']}: VIEW ID={sel:07b}; {vword}; ON: {von}"
            if complete:
                value = next(d[3] for d in cycle_detail[c] if d[0] is op)
                desc += f"; EXPECT {value} / {value:016b}; LEDs: {_on_leds(value)}"
            put("      " + desc)
        put("    Return to RUN: SW14 ON only before the next BTNU press.")
        put()
    put(f"   TOTAL BTNU PRESSES: {scheduled['num_cycles'] + 1}")
    put("   Final press enters DONE, no additional press required.")
    put()

    put("STEP 4 - VIEW ALL STORED RESULTS AND FUNCTIONAL-UNIT OUTPUTS")
    put("   Stay in VIEW (SW15=1, SW14=0); no button presses needed.")
    put("   Selector IDs EXACTLY match codegen.view_list(schedule).")
    put("   FU observations at DONE require your UPDATED *_last codegen.py;")
    put("   with the original live-output generator, FU values may differ.")
    put()
    for i, (name, _signal) in enumerate(views):
        category = "UNIT" if name in unit_names else "INPUT" if name in inputs else "REGISTER"
        word, on = _switch_word(2, i)
        put(f"[ ] VIEW {category:<8} {name:<20} ID={i:>2} (7-bit ID={i:07b})")
        put(f"    SW15..SW0: {word}")
        put(f"    SWITCHES ON: {on}")
        if complete:
            value = expected.get(name)
            if value is not None:
                put(f"    EXPECTED: {value} decimal | binary {value:016b}")
                put(f"    LEDs ON: {_on_leds(value)}")
        else:
            put("    EXPECTED: depends on the input values you actually loaded")
        put()

    put("WARNINGS & LIMITS")
    if missing:
        put("   No exact numeric predictions for this run because values were not")
        put("   provided for: " + ", ".join(missing))
        put("   Example for this schedule: demo " + " ".join(
            f"{x[:-2] if x.endswith('_0') else x}=3" for x in inputs
        ))
    if overflow_note:
        put("   " + overflow_note)
    for warning in warnings:
        put("   " + warning)
    put("   Current 16-bit datapath wraps for results above 65535.")
    put("   Subtraction results must be nonnegative for the assignment demo.")
    put("   Current 5-bit state supports at most 30 arithmetic cycles.")
    put("   If you change equations/schedule: regenerate synth_core.v, rebuild")
    put("   the bitstream and program the board before following this TXT.")
    put("=" * 79)
    return "\n".join(lines) + "\n"


def write_demo_guide(equations, scheduled, filename="demo.txt", input_values=None):
    """Write the TXT file and return its absolute or relative Path."""
    path = Path(filename)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(make_demo_guide(equations, scheduled, input_values), encoding="utf-8")
    return path
