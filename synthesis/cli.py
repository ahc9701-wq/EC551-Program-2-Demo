
"""
cli.py - Interactive command-line interface.

Handles user commands for the hardware synthesis tool.
"""

from pathlib import Path
from pprint import pprint

from synthesis.equationparser import parseqs
from synthesis.ssa import convertssa, exportssa


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

        # This is what shows for an unknown command
        else:
            print(
                f"Unknown command: {command}. "
                "Type 'help' to see commands."
            )
