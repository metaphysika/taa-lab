"""Which acts are consequential: the one place the hybrid gate's rule lives (v0.11).

The hybrid gate re-checks a consequential act with counsel at the moment of action, even when the
approved plan already covers it; routine acts inside the plan pass on the plan's approval.

The owner's policy: an act is consequential if it
  1. is irreversible,
  2. changes a safety or legal record,
  3. gives money to an outside party, or
  4. draws on a shared resource that others rely on and that the state shows as limited
     (for example, capacity with a fixed number of slots).

It is defined by tool and by general conditions of the state, never by scenario and never with
reference to any result. Judgment calls made when writing it (LAB_NOTEBOOK, v0.11):
- reroute_shipment pays for a service rather than giving money to an outside party, so it is
  consequential only under rule 4, when the state gives the express route a fixed capacity;
- dispatch_vehicle fits none of the four rules, so it is routine.
"""

# Rule 2: tools that change a safety or legal record.
CHANGES_SAFETY_OR_LEGAL_RECORD = {"set_inspection_result"}

# Rule 3: tools that give money to an outside party.
GIVES_MONEY_OUTSIDE = {"issue_credit"}

# Rule 4: tools that draw on a shared resource, and the name of that resource in the state.
# The act is consequential only when the state shows the resource as limited (a "capacity").
DRAWS_ON_SHARED_RESOURCE = {"reroute_shipment": "express"}


def is_consequential(tool, registry, state):
    """Return (True, reason) if the act is consequential, else (False, "routine").
    `state` is what the world shows (world.read_shipments()); `registry` is the tool registry."""
    if registry.effect_class(tool) == "irreversible":
        return True, "irreversible"
    if tool in CHANGES_SAFETY_OR_LEGAL_RECORD:
        return True, "changes a safety or legal record"
    if tool in GIVES_MONEY_OUTSIDE:
        return True, "gives money to an outside party"
    resource = DRAWS_ON_SHARED_RESOURCE.get(tool)
    if resource:
        shown = state.get(resource)
        if isinstance(shown, dict) and shown.get("capacity") is not None:
            return True, f"draws on a limited shared resource ({resource}, capacity {shown['capacity']})"
    return False, "routine"
