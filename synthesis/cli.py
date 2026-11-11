
"""
cli.py - Interactive command-line interface.

Handles user commands for the hardware synthesis tool.
"""

from pathlib import Path
from pprint import pprint

from synthesis.equationparser import parseqs
from synthesis.ssa import convertssa, exportssa
from synthesis.dag import build_dag, print_dag
from synthesis.scheduler import schedule, print_schedule, export_schedule
from synthesis.codegen import write_verilog, view_list

# Used AI
from synthesis.board_demo import write_demo_guide
from synthesis.tbgen import write_testbench

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_file(filename):
    """Load and parse equations from a text file."""

    path = Path(filename.strip().strip('"').strip("'"))

    if not path.is_absolute():
        path = PROJECT_ROOT / path

    equations = parseqs(path)

    print(f"Loaded {len(equations)} equation(s) from {path.name}.")

    return equations


def find_inputs(equations):
    """Find variables used before their first assignment."""

    assigned = set()
    inputs = []

    for equation in equations:

        # Check both operands
        for operand in (equation["input1"], equation["input2"]):

            if operand not in assigned and operand not in inputs:
                inputs.append(operand)

        # Marks the output as calculated (So if first line is X = A + B, it adds A and B into inputs and checks
        # them with the next operands, and then adds the X into outputs)
        assigned.add(equation["output"])

    return inputs


def run(initial_file=None):
    """Run the interactive command-line interface."""

    print("EC551 Program 2 - Hardware Synthesis Tool")
    print("Type 'help' for commands, or 'quit' to exit.\n")

    # Makes sure current equation is none at start (will load a list of dictionaries at the start)
    current_equations = None
    current_dag = None
    current_schedule = None

    # Only loads a file if one was provided through the command line
    if initial_file is not None:
        try:
            current_equations = load_file(initial_file)

        except (OSError, ValueError) as error:
            print("Error:", error)
            print("Try again with: load <filename>")

    # This is the interactive command loop (continues code until quit command is added)
    while True:

        try:
            line = input("hls> ").strip()

        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not line:
            continue

        command, _, argument = line.partition(" ")
        command = command.lower()
        argument = argument.strip()

        # Exits the program
        if command in ("quit", "exit"):
            break

        # Displays available commands
        elif command == "help":
            print("Available commands:")
            print("  load <filename> - Load equation file")
            print("  show            - Display parsed equations")
            print("  dict            - Display list of dictionaries")
            print("  inputs          - Show initial input variables")
            print("  help            - Display commands")
            print("  quit            - Exit program")
            print("  ssa             - Display SSA equations")
            print("  exportssa       - Export SSA equations to a file")
            print("  dag             - Displays the Equation Dependency Graph")
            print("  schedule <mode> - Schedule operations by cycle, asap|alap|casap|calap|custom")
            print("  exportschedule  - Exports schedule in a JSON")
            print("  verilog         - Generate Verilog hardware from the current schedule")
            print("  demo [A=3 B=2]  - Generate a step-by-step Basys 3 demo.txt")
            print("  testbench [A=3 B=2] - Generate Verilog testbench")
            print("  tb [A=3 B=2]        - Shortcut for testbench")
        # Loads a file
        elif command == "load":

            if not argument:
                try:
                    argument = input("File path: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    continue

            if not argument:
                print("Please enter a file path.")
                continue

            try:
                current_equations = load_file(argument)
                
                # Reset DAG and schedule when a new file is loaded
                current_dag = None
                current_schedule = None

            except (OSError, ValueError) as error:
                print("Error:", error)

        # Displays parsed equations
        elif command == "show":

            if current_equations is None:
                print("Load an equation file first.")

            else:
                for i, equation in enumerate(current_equations, start=1):
                    e = equation

                    print(
                        f'{i}. {e["output"]} = '
                        f'{e["input1"]} {e["operator"]} {e["input2"]}'
                    )

        # Displays the parsed equation dictionaries
        elif command == "dict":

            if current_equations is None:
                print("Please load an equation file first.")

            else:
                pprint(current_equations, sort_dicts=False)

        # Identifys external input variables
        elif command == "inputs":

            if current_equations is None:
                print("Load an equation file first.")

            else:
                inputs = find_inputs(current_equations)

                if not inputs:
                    print("No external input variables found.")

                for i, name in enumerate(inputs):
                    print(f"Variable {name}: SW13-SW8 = {i:06b}")

        # Displays equations in SSA form
        elif command == "ssa":

            if current_equations is None:
                print("Please load an equation file first.")

            else:
                ssaequations = convertssa(current_equations)

                for equation in ssaequations:
                    print(
                        f'{equation["output"]} = '
                        f'{equation["input1"]} '
                        f'{equation["operator"]} '
                        f'{equation["input2"]}'
                    )

        # Exports SSA equations into a text file
        elif command == "exportssa":

            if current_equations is None:
                print("Please load an equation file first.")

            else:
                ssaequations = convertssa(current_equations)

                # Default filepath if none provided
                filename = argument if argument else "example/ssa.txt"

                path = Path(filename.strip().strip('"').strip("'"))

                if not path.is_absolute():
                    path = PROJECT_ROOT / path

                try:
                    outputpath = exportssa(ssaequations, path)
                    print(f"SSA exported to: {outputpath}")

                except OSError as error:
                    print("Error:", error)

        # Command for dependency graph
        elif command == "dag":

            if current_equations is None:
                print("Please load an equation file first.")

            else:
                # Converts equations into SSA
                ssaequations = convertssa(current_equations)

                # Builds the dependency graph
                current_dag = build_dag(ssaequations)

                # Makes old schedule is no longer valid
                current_schedule = None

                # Displays the graph
                print_dag(current_dag)

        # Schedules operations by clock cycle
        elif command == "schedule":

            if current_equations is None:
                print("Please load an equation file first.")

            elif not argument:
                print("Usage: schedule <asap|alap|casap|calap|custom>")
                print("Optional: add=N sub=N mul=N latency=N")

            else:
                try:
                    # Build DAG if not already created
                    if current_dag is None:
                        ssaequations = convertssa(current_equations)
                        current_dag = build_dag(ssaequations)

                    parts = argument.split()
                    mode = parts[0].lower()

                    limits = {}
                    latency = None

                    # Reads optional arguments
                    for option in parts[1:]:
                        key, value = option.split("=", 1)

                        if key in ("add", "sub", "mul"):
                            limits[key] = int(value)

                        elif key == "latency":
                            latency = int(value)

                        else:
                            raise ValueError(f"Unknown option: {key}")

                    # Runs teammate's scheduler
                    current_schedule = schedule(
                        current_dag,
                        mode,
                        limits=limits,
                        latency=latency
                    )

                    print_schedule(current_schedule)

                except ValueError as error:
                    print("Error:", error)

        # Exports the current schedule into a JSON file
        elif command == "exportschedule":

            if current_schedule is None:
                print("Please schedule the equations first.")

            else:
                # Default output file
                filename = argument if argument else "example/schedule.json"

                path = Path(filename.strip().strip('"').strip("'"))

                if not path.is_absolute():
                    path = PROJECT_ROOT / path

                try:
                    path.parent.mkdir(parents=True, exist_ok=True)

                    export_schedule(current_schedule, path)

                    print(f"Schedule exported to: {path}")

                except OSError as error:
                    print("Error:", error)

        # Generates Verilog hardware using the current schedule
        elif command == "verilog":

            if current_schedule is None:
                print("Please schedule the equations first.")

            else:
                # Default generated Verilog file
                filename = argument if argument else "verilog/generated/synth_core.v"

                path = Path(filename.strip().strip('"').strip("'"))

                if not path.is_absolute():
                    path = PROJECT_ROOT / path

                try:
                    path.parent.mkdir(parents=True, exist_ok=True)

                    # Generates the circuit
                    write_verilog(current_schedule, path, width=16)

                    print(f"Verilog generated: {path}")

                    # Shows which switches select which input
                    print("\nFPGA INPUT MAPPING")
                    for i, name in enumerate(current_schedule["inputs"]):
                        print(f"{i:06b} -> {name}")

                    # Shows which switches select which output
                    print("\nFPGA OUTPUT MAPPING")
                    for i, (name, signal) in enumerate(view_list(current_schedule)):
                        print(f"{i:07b} -> {name}")

                except (OSError, ValueError) as error:
                    print("Error:", error)

        # Generates a .txt guide for the FPGA demo (used AI)
        elif command == "demo":

            if current_equations is None:
                print("Please load an equation file first.")

            elif current_schedule is None:
                print("Please schedule the equations first.")

            else:
                try:
                    values = {}
                    filename = "example/demo_guide.txt"

                    for item in argument.split():
                        name, sep, value = item.partition("=")

                        if not sep:
                            raise ValueError(f"Use name=value: {item}")

                        if name.lower() in ("file", "out"):
                            filename = value
                        else:
                            values[name] = int(value)

                    path = Path(filename)

                    if not path.is_absolute():
                        path = PROJECT_ROOT / path

                    output = write_demo_guide(
                        current_equations,
                        current_schedule,
                        path,
                        values
                    )

                    print(f"Demo guide saved to: {output}")

                except (ValueError, KeyError, OSError) as error:
                    print("Error:", error)

        # Automatically generate a Verilog testbench (AI Generated)
        elif command in ("testbench", "tb"):

            if current_schedule is None:
                print("Please schedule equations first.")

            else:
                try:
                    values = {}

                    # Read optional input values, e.g. A=3 B=2
                    for item in argument.split():
                        name, sep, value = item.partition("=")

                        if not sep or not name:
                            raise ValueError(
                                f"Expected NAME=VALUE, got {item}"
                            )

                        values[name] = int(value)

                    # Generated file location
                    output = (
                        PROJECT_ROOT
                        / "verilog"
                        / "testbench"
                        / "tb_synth_core.v"
                    )

                    # Use the currently selected schedule
                    path = write_testbench(
                        current_schedule,
                        output,
                        values
                    )

                    print("Testbench generated successfully!")
                    print(f"Saved to: {path}")
                    print("Tests include:")
                    print("  - Input loading")
                    print("  - Scheduled arithmetic operations")
                    print("  - Intermediate results")
                    print("  - Functional units")
                    print("  - Final results and DONE state")

                except (ValueError, KeyError, OSError) as error:
                    print("Testbench error:", error)

        # This is what shows for an unknown command
        else:
            print(
                f"Unknown command: {command}. "
                "Type 'help' to see commands."
            )
