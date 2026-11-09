"""Tests for Section 4 (Verilog generation) and Section 5 (functional units).

For each case this test generates synth_core.v, simulates it with Icarus
Verilog while pressing step once per cycle, and checks:
  - in every cycle, the unit doing each operation shows the right value
  - at DONE, every result register holds the right value
The expected values come from evaluating the equations directly in Python.

Run from the repo root:   python -m tests.test_section4
Needs iverilog (macOS: brew install icarus-verilog).
"""

import os
import random
import shutil
import subprocess
import tempfile

from synthesis.dag import build_dag
from synthesis.scheduler import schedule
from synthesis.codegen import generate_verilog, view_list
from tests.test_section3 import EXAMPLE1, EXAMPLE2, EXAMPLE3, EXAMPLE4

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FU_FILES = [os.path.join(REPO, "verilog", "fu", name)
            for name in ("adder.v", "subtractor.v", "multiplier.v")]
MASK = 0xFFFF   # 16-bit data
LIMITS = {"add": 1, "sub": 1, "mul": 1}
MODES = [("asap", None), ("alap", None), ("casap", LIMITS), ("calap", LIMITS), ("custom", LIMITS)]


def golden(result, values):
    """Evaluate the equations in Python, 16 bits wide like the hardware."""
    env = dict(values)
    for op in result["ops"]:
        a = int(op["a"]) if op["a"].isdigit() else env[op["a"]]
        b = int(op["b"]) if op["b"].isdigit() else env[op["b"]]
        if op["op"] == "add":
            env[op["dest"]] = (a + b) & MASK
        elif op["op"] == "sub":
            env[op["dest"]] = (a - b) & MASK
        else:
            env[op["dest"]] = (a * b) & MASK
    return env


def make_testbench(result, values):
    """Enters every input with in_write, steps through every state and
    prints 'V <tag> <value>' lines."""
    index = {}
    for i, (label, _) in enumerate(view_list(result)):
        index[label] = i

    t = ["module tb;",
         "    reg clk = 0, rst = 1, step = 0, in_write = 0;",
         "    reg [5:0] in_sel = 0;",
         "    reg [7:0] in_val = 0;",
         "    reg [4:0] fu_sel = 0;",
         "    wire [15:0] disp_val; wire [4:0] state; wire done;",
         "    synth_core dut (clk, rst, step, in_sel, in_val, in_write, fu_sel, disp_val, state, done);",
         "    always #5 clk = ~clk;",
         "    task press; begin @(negedge clk) step = 1; @(negedge clk) step = 0; end endtask",
         "    task write(input [5:0] s, input [7:0] x); begin",
         "        @(negedge clk) begin in_sel = s; in_val = x; in_write = 1; end",
         "        @(negedge clk) in_write = 0; end endtask",
         "    initial begin",
         "        repeat (2) @(negedge clk); rst = 0;"]
    for i, var in enumerate(result["inputs"]):
        t.append(f"        write({i}, {values[var]});   // {var}")
    t.append("        press;   // LOAD -> cycle 1")
    if result["inputs"]:
        # in_write outside LOAD must be ignored
        t.append(f"        write(0, {values[result['inputs'][0]] ^ 0xFF});")
    for c in range(1, result["num_cycles"] + 1):
        for op in result["ops"]:
            if op["cycle"] == c:
                t.append(f"        fu_sel = {index[op['unit']]}; #1 "
                         f"$display(\"V c:{op['dest']} %0d\", disp_val);")
        t.append("        press;")
    t.append("        #1 $display(\"V done %0d\", done);")
    for op in result["ops"]:
        if op["dest"] in index:
            t.append(f"        fu_sel = {index[op['dest']]}; #1 "
                     f"$display(\"V final:{op['dest']} %0d\", disp_val);")
    t += ["        $finish;", "    end", "endmodule"]
    return "\n".join(t) + "\n"


def simulate(verilog, testbench):
    """Compile and run with iverilog; return {tag: value}."""
    with tempfile.TemporaryDirectory() as tmp:
        files = []
        for name, text in (("synth_core.v", verilog), ("tb.v", testbench)):
            path = os.path.join(tmp, name)
            with open(path, "w") as f:
                f.write(text)
            files.append(path)
        out = os.path.join(tmp, "sim.vvp")
        subprocess.run(["iverilog", "-g2005", "-o", out] + files + FU_FILES,
                       check=True, capture_output=True, text=True)
        run = subprocess.run(["vvp", "-n", out], check=True, capture_output=True, text=True)

    values = {}
    for line in run.stdout.splitlines():
        if line.startswith("V "):
            tag, number = line[2:].split()
            values[tag] = int(number)
    return values


def check(ssa, mode, limits, input_values):
    result = schedule(build_dag(ssa), mode, limits)
    values = {}
    for var in result["inputs"]:
        values[var] = input_values[var] % 256      # in_val is 8 bits

    expected = golden(result, values)
    got = simulate(generate_verilog(result), make_testbench(result, values))

    assert got["done"] == 1, f"{mode}: FSM did not reach DONE"
    for op in result["ops"]:
        want = expected[op["dest"]]
        assert got["c:" + op["dest"]] == want, \
            f"{mode}: {op['unit']} in cycle {op['cycle']} shows {got['c:' + op['dest']]}, expected {want}"
        if "final:" + op["dest"] in got:
            assert got["final:" + op["dest"]] == want, \
                f"{mode}: register {op['dest']} is {got['final:' + op['dest']]}, expected {want}"


def test_examples():
    for ssa in (EXAMPLE1, EXAMPLE2, EXAMPLE3, EXAMPLE4):
        for mode, limits in MODES:
            check(ssa, mode, limits, {"A": 3, "B": 2, "C": 5, "D": 4})


def test_constants():
    ssa = [("X", "+", "A", "3"), ("Y", "*", "X", "2"), ("Z", "-", "Y", "B")]
    for mode, limits in MODES:
        check(ssa, mode, limits, {"A": 7, "B": 1})


def test_random_programs():
    """Up to 20 random equations, like ones the professor might write."""
    rng = random.Random(551)
    names = ["A", "B", "C", "D", "E"]
    for trial in range(40):
        ssa = []
        for i in range(rng.randint(1, 20)):
            known = names + [s[0] for s in ssa]
            a = rng.choice(known) if rng.random() > 0.1 else str(rng.randint(0, 9))
            ssa.append((f"T{i}", rng.choice("+-*"), a, rng.choice(known)))
        limits = {"add": rng.randint(1, 3), "sub": rng.randint(1, 2), "mul": rng.randint(1, 2)}
        mode = rng.choice(["asap", "alap", "casap", "calap", "custom"])
        values = {var: rng.randint(0, 255) for var in names}
        check(ssa, mode, limits, values)


if __name__ == "__main__":
    if shutil.which("iverilog") is None:
        print("iverilog not found; install Icarus Verilog to run these tests.")
    else:
        test_examples()
        test_constants()
        test_random_programs()
        print("All section 4 tests passed (examples, constants, 40 random programs).")
