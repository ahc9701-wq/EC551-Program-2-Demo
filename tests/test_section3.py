"""Tests for Section 3 (DAG + scheduling).

Run from the repo root:
    python -m tests.test_section3      (prints every schedule, then checks)
    python -m pytest tests             (if pytest is installed)

The SSA lists are written by hand here so these tests do not depend on
the parser / SSA code.
"""

from synthesis.dag import build_dag, print_dag
from synthesis.scheduler import schedule, print_schedule

# examples/example1.txt (from the assignment)
EXAMPLE1 = [("X", "+", "A", "B"),
            ("Y", "+", "X", "A"),
            ("Z", "-", "X", "B"),
            ("Q", "*", "B", "Z")]

# examples/example2.txt after SSA (X is assigned twice)
EXAMPLE2 = [("X1", "+", "A", "B"),
            ("X2", "*", "X1", "A"),
            ("Y1", "-", "X2", "A")]

# examples/example3.txt (resource limits change the schedule)
EXAMPLE3 = [("X", "+", "A", "B"),
            ("Y", "+", "C", "D"),
            ("Z", "*", "X", "Y"),
            ("W", "-", "Z", "A"),
            ("V", "+", "Y", "B")]

# examples/example4.txt (custom beats constrained ASAP with 1 adder)
EXAMPLE4 = [("X", "+", "A", "B"),
            ("Y", "+", "C", "D"),
            ("Z", "*", "Y", "A"),
            ("W", "*", "Z", "B")]


def cycles(result):
    """{variable: cycle}, easier to compare than the full result."""
    out = {}
    for op in result["ops"]:
        out[op["dest"]] = op["cycle"]
    return out


def test_dag():
    dag = build_dag(EXAMPLE3)
    assert dag["inputs"] == ["A", "B", "C", "D"]
    assert dag["preds"][2] == [0, 1]          # Z depends on X and Y
    assert dag["succs"][1] == [2, 4]          # Y feeds Z and V


def test_example1():
    dag = build_dag(EXAMPLE1)
    assert cycles(schedule(dag, "asap")) == {"X": 1, "Y": 2, "Z": 2, "Q": 3}
    assert cycles(schedule(dag, "alap")) == {"X": 1, "Y": 3, "Z": 2, "Q": 3}


def test_example2_ssa_chain():
    dag = build_dag(EXAMPLE2)
    assert cycles(schedule(dag, "asap")) == {"X1": 1, "X2": 2, "Y1": 3}


def test_example3_unconstrained():
    dag = build_dag(EXAMPLE3)
    result = schedule(dag, "asap")
    assert cycles(result) == {"X": 1, "Y": 1, "Z": 2, "W": 3, "V": 2}
    assert result["units"]["add"] == 2
    assert cycles(schedule(dag, "alap")) == {"X": 1, "Y": 1, "Z": 2, "W": 3, "V": 3}


def test_example3_one_adder():
    dag = build_dag(EXAMPLE3)
    limits = {"add": 1}

    result = schedule(dag, "casap", limits)
    assert cycles(result) == {"X": 1, "Y": 2, "Z": 3, "W": 4, "V": 3}
    assert result["units"]["add"] == 1

    result = schedule(dag, "calap", limits)
    assert cycles(result) == {"X": 1, "Y": 2, "Z": 3, "W": 4, "V": 4}
    assert result["units"]["add"] == 1


def test_example4_custom_is_shorter():
    dag = build_dag(EXAMPLE4)
    limits = {"add": 1}
    assert schedule(dag, "casap", limits)["num_cycles"] == 4
    result = schedule(dag, "custom", limits)
    assert result["num_cycles"] == 3
    assert cycles(result) == {"X": 2, "Y": 1, "Z": 2, "W": 3}


def test_alap_with_longer_latency():
    dag = build_dag(EXAMPLE1)
    assert cycles(schedule(dag, "alap", latency=5)) == {"X": 3, "Y": 5, "Z": 4, "Q": 5}


def test_binding_names():
    dag = build_dag(EXAMPLE3)
    units = {}
    for op in schedule(dag, "asap")["ops"]:
        units[op["dest"]] = op["unit"]
    assert units == {"X": "add0", "Y": "add1", "Z": "mul0", "W": "sub0", "V": "add0"}


def test_input_order_matches_cli():
    """in_sel numbers in synth_core must match the CLI's 'inputs' command."""
    from synthesis.cli import find_inputs
    from synthesis.ssa import convertssa

    reassigned = [("Y", "+", "X", "A"), ("X", "*", "A", "B")]   # X is an input, then assigned
    for ssa in (EXAMPLE1, EXAMPLE3, EXAMPLE4, reassigned):
        equations = []
        for dest, op, a, b in ssa:
            equations.append({"output": dest, "input1": a, "operator": op, "input2": b})
        names = []
        for var in build_dag(convertssa(equations))["inputs"]:   # dicts straight from SSA
            names.append(var[:-2])                 # A_0 -> A
        assert names == find_inputs(equations)


def test_dependencies_always_respected():
    for ssa in (EXAMPLE1, EXAMPLE2, EXAMPLE3, EXAMPLE4):
        dag = build_dag(ssa)
        for mode in ("asap", "alap", "casap", "calap", "custom"):
            limits = {"add": 1, "sub": 1, "mul": 1}
            result = schedule(dag, mode, limits)
            c = cycles(result)
            for node in dag["nodes"]:
                for p in dag["preds"][node["id"]]:
                    assert c[dag["nodes"][p]["dest"]] < c[node["dest"]]
            if mode in ("casap", "calap", "custom"):
                for t in ("add", "sub", "mul"):
                    assert result["units"][t] <= 1


if __name__ == "__main__":
    for name, ssa in (("example1", EXAMPLE1), ("example3", EXAMPLE3)):
        print(f"\n######## {name} ########")
        dag = build_dag(ssa)
        print_dag(dag)
        for mode in ("asap", "alap"):
            print()
            print_schedule(schedule(dag, mode))
        for mode in ("casap", "calap", "custom"):
            print()
            print_schedule(schedule(dag, mode, {"add": 1}))

    print("\n######## example4: casap vs custom, 1 adder ########")
    dag = build_dag(EXAMPLE4)
    print_schedule(schedule(dag, "casap", {"add": 1}))
    print()
    print_schedule(schedule(dag, "custom", {"add": 1}))

    tests = [f for n, f in sorted(globals().items()) if n.startswith("test_")]
    for t in tests:
        t()
    print(f"\nAll {len(tests)} tests passed.")
