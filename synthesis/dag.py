"""Section 3: build the DAG from SSA statements.

Input: the list that ssa.convertssa() returns, for example
    [{"output": "X_1", "input1": "A_0", "operator": "+", "input2": "B_0"},
     {"output": "Y_1", "input1": "X_1", "operator": "+", "input2": "A_0"}]
Tuples such as ("X_1", "+", "A_0", "B_0") also work (the tests use them).
The operator may be written as "+"/"-"/"*" or "add"/"sub"/"mul".

Each statement becomes one node. There is an edge i -> j when
statement j uses the value produced by statement i.

In SSA form every variable is defined before it is used, so the
statements are already in topological order: every predecessor of
node i has a smaller index than i. The scheduler relies on this.
"""

OP_NAMES = {"+": "add", "-": "sub", "*": "mul",
            "add": "add", "sub": "sub", "mul": "mul"}
OP_SYMBOLS = {"add": "+", "sub": "-", "mul": "*"}


def is_number(name):
    return name.isdigit()


def build_dag(ssa):
    nodes = []
    preds = {}
    succs = {}
    inputs = []
    producer = {}   # variable name -> id of the node that produces it

    for i in range(len(ssa)):
        stmt = ssa[i]
        if isinstance(stmt, dict):            # format from ssa.convertssa()
            dest = stmt["output"]
            op = stmt["operator"]
            a = stmt["input1"]
            b = stmt["input2"]
        else:                                 # (dest, op, a, b) tuple
            dest, op, a, b = stmt
        if op not in OP_NAMES:
            raise ValueError(f"Unknown operator '{op}' in statement {i + 1}")
        if dest in producer:
            raise ValueError(f"'{dest}' is assigned twice; input must be in SSA form")

        nodes.append({"id": i, "dest": dest, "op": OP_NAMES[op], "a": a, "b": b})
        preds[i] = []
        succs[i] = []

        for operand in (a, b):
            if is_number(operand):
                continue                      # constants create no dependency
            if operand in producer:
                p = producer[operand]
                if p not in preds[i]:         # X=Y+Y needs only one edge
                    preds[i].append(p)
                    succs[p].append(i)
            elif operand not in inputs:
                inputs.append(operand)        # never assigned -> primary input

        producer[dest] = i

    return {"nodes": nodes, "preds": preds, "succs": succs, "inputs": inputs}


def node_text(node):
    return f"{node['dest']} = {node['a']} {OP_SYMBOLS[node['op']]} {node['b']}"


def print_dag(dag):
    print("=== DAG ===")
    for node in dag["nodes"]:
        i = node["id"]
        if len(dag["preds"][i]) == 0:
            deps = "(inputs only)"
        else:
            deps = ", ".join(f"op{p + 1}" for p in dag["preds"][i])
        print(f"op{i + 1}: {node_text(node):<16} depends on: {deps}")
    print(f"Inputs: {', '.join(dag['inputs'])}")
