
"""
equationparser.py - Parses high-level arithmetic equations.

Each equation (line) contains:
    - Output variable
    - First input
    - Operator (+, -, *)
    - Second input
"""
# Regular equation, allows us to define the pattern
import re


def parseqs(filename):
    equations = []

    # This determines patterns for equations such as X = A + B
    pattern = r"([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([A-Za-z_][A-Za-z0-9_]*)\s*([+*-])\s*([A-Za-z_][A-Za-z0-9_]*)"

    # Reads the input file
    with open(filename, "r") as file:
        lines = file.readlines()

    for line_number, line in enumerate(lines, start=1):
        line = line.strip()

        # This skips empty lines
        if not line:
            continue

        # Checks if the equation is valid
        match = re.fullmatch(pattern, line)

        # If equation is not valid, it notes that down in cmd window
        if not match:
            raise ValueError(
                f"Invalid equation on line {line_number}: {line}"
            )

        output, input1, operator, input2 = match.groups()

        # Appends the parsed equation (in a dictionary) in a list
        equations.append({
            "output": output,
            "input1": input1,
            "operator": operator,
            "input2": input2
        })

    # Assignment allows a maximum of 20 equations
    if len(equations) > 21:
        raise ValueError("Maximum of 20 equations allowed.")

    return equations
