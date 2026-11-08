
"""
ssa.py - Convert equations into Static Single Assignment form.

Each assigned variable receives a unique version number.
"""

from pathlib import Path


def convertssa(equations):

    versions = {}
    ssa_equations = []

    # This looks at the equations in current_function
    for equation in equations:

        input1 = equation["input1"]
        input2 = equation["input2"]
        operator = equation["operator"]
        output = equation["output"]

        # Initializes input variables if not seen before
        if input1 not in versions:
            versions[input1] = 0

        if input2 not in versions:
            versions[input2] = 0

        # Gets the current versions of the inputs
        newinput1 = f"{input1}_{versions[input1]}"
        newinput2 = f"{input2}_{versions[input2]}"

        # Increment the output variable's version
        versions[output] = versions.get(output, 0) + 1

        newoutput = f"{output}_{versions[output]}"

        # Store the renamed equation
        ssa_equations.append({
            "output": newoutput,
            "input1": newinput1,
            "operator": operator,
            "input2": newinput2
        })

    return ssa_equations


def exportssa(ssaequations, filename):

    path = Path(filename)

    # Creates the output folder if needed
    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w") as file:

        for equation in ssaequations:
            line = (
                f'{equation["output"]} = '
                f'{equation["input1"]} '
                f'{equation["operator"]} '
                f'{equation["input2"]}\n'
            )

            file.write(line)

    return path
