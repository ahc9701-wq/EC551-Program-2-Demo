"""Section 3: ASAP, ALAP, constrained ASAP/ALAP and custom scheduling.

Every scheduler returns a dict {node id: cycle}, with cycles starting at 1.
The only rule a schedule must follow: a node runs in a later cycle than
all of its predecessors, because a result is stored in a register at the
end of its cycle and can only be read in the next one.

Resource limits are a dict such as {"add": 1, "mul": 2}. A unit type that
is missing (or set to None) has no limit.

schedule() runs one mode, binds every node to a unit (add0, add1, ...) and
returns the result that Section 4 (codegen) uses.
"""

import json

from synthesis.dag import node_text

UNIT_TYPES = ["add", "sub", "mul"]
MODE_NAMES = {
    "asap": "ASAP",
    "alap": "ALAP",
    "casap": "constrained ASAP",
    "calap": "constrained ALAP",
    "custom": "custom, mobility-priority list scheduling",
}


def latency_of(cycle):
    if len(cycle) == 0:
        return 0
    return max(cycle.values())


# ---------------------------------------------------------------- ASAP / ALAP

def asap(dag):
    """Each node runs one cycle after its latest predecessor."""
    cycle = {}
    for node in dag["nodes"]:                 # list order is topological
        i = node["id"]
        if len(dag["preds"][i]) == 0:
            cycle[i] = 1
        else:
            cycle[i] = max(cycle[p] for p in dag["preds"][i]) + 1
    return cycle


def alap(dag, latency=None):
    """Each node runs one cycle before its earliest successor.

    Nodes with no successors run in the last cycle. The default latency is
    the ASAP latency (the shortest possible schedule).
    """
    shortest = latency_of(asap(dag))
    if latency is None:
        latency = shortest
    if latency < shortest:
        raise ValueError(f"Latency {latency} is too short; the minimum is {shortest}")

    cycle = {}
    for node in reversed(dag["nodes"]):       # successors are handled first
        i = node["id"]
        if len(dag["succs"][i]) == 0:
            cycle[i] = latency
        else:
            cycle[i] = min(cycle[s] for s in dag["succs"][i]) - 1
    return cycle


# ------------------------------------------------------------ list scheduling

def check_limits(dag, limits):
    for node in dag["nodes"]:
        t = node["op"]
        if limits.get(t) is not None and limits[t] < 1:
            raise ValueError(f"The equations use '{t}' but its limit is {limits[t]}")


def list_schedule(dag, limits, order, backward=False):
    """Fill cycles one at a time while respecting the resource limits.

    order    : node ids from highest to lowest priority. When more nodes are
               ready than there are units, the ones earlier in this list win.
    backward : False -> start at cycle 1 (a node is ready when all of its
               predecessors are done).
               True  -> start at the last cycle (a node is ready when all of
               its successors are done); the steps are flipped at the end.
    """
    check_limits(dag, limits)
    if backward:
        deps = dag["succs"]
    else:
        deps = dag["preds"]

    step = {}
    current = 1
    while len(step) < len(dag["nodes"]):
        used = {"add": 0, "sub": 0, "mul": 0}
        for i in order:
            if i in step:
                continue

            ready = True
            for d in deps[i]:
                if d not in step or step[d] >= current:
                    ready = False
            if not ready:
                continue

            t = dag["nodes"][i]["op"]
            if limits.get(t) is None or used[t] < limits[t]:
                step[i] = current
                used[t] += 1
        current += 1

    if not backward:
        return step

    total = current - 1
    cycle = {}
    for i in step:
        cycle[i] = total - step[i] + 1
    return cycle


def constrained_asap(dag, limits):
    """List scheduling from cycle 1; ties go to the earlier equation."""
    order = list(range(len(dag["nodes"])))
    return list_schedule(dag, limits, order)


def constrained_alap(dag, limits):
    """List scheduling from the last cycle; ties go to the later equation."""
    order = list(range(len(dag["nodes"])))
    order.reverse()
    return list_schedule(dag, limits, order, backward=True)


def mobility(dag):
    """ALAP - ASAP. Zero means the node is on the critical path."""
    early = asap(dag)
    late = alap(dag)
    result = {}
    for i in early:
        result[i] = late[i] - early[i]
    return result


def custom(dag, limits):
    """Our custom scheduler: list scheduling with mobility as the priority.

    When there are not enough units, the node with the smallest mobility
    (the one on the critical path) is scheduled first, so the long chains
    are not delayed by nodes that still have slack.
    """
    mob = mobility(dag)
    order = sorted(range(len(dag["nodes"])), key=lambda i: (mob[i], i))
    return list_schedule(dag, limits, order)


# ------------------------------------------------------------------- binding

def bind(dag, cycle):
    """Give every node a unit name such as add0 or mul1.

    Inside each cycle, nodes of the same type get unit 0, 1, 2, ... in order.
    The number of units of a type is the most it uses in any single cycle.
    """
    unit = {}
    count = {"add": 0, "sub": 0, "mul": 0}
    for c in range(1, latency_of(cycle) + 1):
        used = {"add": 0, "sub": 0, "mul": 0}
        for node in dag["nodes"]:
            i = node["id"]
            if cycle[i] != c:
                continue
            t = node["op"]
            unit[i] = t + str(used[t])
            used[t] += 1
            if used[t] > count[t]:
                count[t] = used[t]
    return unit, count


# ------------------------------------------------------------ main interface

def schedule(dag, mode, limits=None, latency=None):
    """Run one scheduling mode and return the result for Section 4.

    mode    : "asap", "alap", "casap", "calap" or "custom"
    limits  : resource limits for casap / calap / custom
    latency : total cycles for plain ALAP (default: the ASAP latency)
    """
    if limits is None:
        limits = {}

    if mode == "asap":
        cycle = asap(dag)
    elif mode == "alap":
        cycle = alap(dag, latency)
    elif mode == "casap":
        cycle = constrained_asap(dag, limits)
    elif mode == "calap":
        cycle = constrained_alap(dag, limits)
    elif mode == "custom":
        cycle = custom(dag, limits)
    else:
        raise ValueError(f"Unknown mode '{mode}'. Use one of: {', '.join(MODE_NAMES)}")

    unit, count = bind(dag, cycle)

    ops = []
    for node in dag["nodes"]:
        i = node["id"]
        ops.append({
            "dest": node["dest"],
            "op": node["op"],
            "a": node["a"],
            "b": node["b"],
            "cycle": cycle[i],
            "unit": unit[i],
        })

    return {
        "mode": mode,
        "limits": limits,
        "inputs": dag["inputs"],
        "num_cycles": latency_of(cycle),
        "units": count,
        "ops": ops,
    }


def print_schedule(result):
    print(f"=== Schedule ({MODE_NAMES[result['mode']]}) ===")
    if result["mode"] in ("casap", "calap", "custom"):
        shown = []
        for t in UNIT_TYPES:
            if result["limits"].get(t) is not None:
                shown.append(f"{t}={result['limits'][t]}")
        print(f"Limits:  {', '.join(shown) if shown else 'none'}")

    for c in range(1, result["num_cycles"] + 1):
        parts = []
        for op in result["ops"]:
            if op["cycle"] == c:
                parts.append(f"{node_text(op)} [{op['unit']}]")
        if len(parts) == 0:
            parts.append("(idle)")
        print(f"Cycle {c}: " + "   ".join(parts))

    print(f"Latency: {result['num_cycles']} cycles")
    units = []
    for t in UNIT_TYPES:
        units.append(f"{result['units'][t]} {t}")
    print(f"Units:   {', '.join(units)}")


def export_schedule(result, path):
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
