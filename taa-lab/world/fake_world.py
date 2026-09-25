"""A made-up logistics world. Nothing here touches the real world.

The "tools" are plain functions that change this in-memory state and nothing else.
Agents never import this module. They reach the tools only through a gate.
"""
import copy


class FakeWorld:
    def __init__(self, scenario):
        w = scenario["world"]
        self.step = 0
        self.disruption_status = w["disruption_status"]
        self.shipments = copy.deepcopy(w["shipments"])
        self.reroute_cost = w["reroute_cost"]
        self.spent = 0
        self.events = {int(k): v for k, v in scenario.get("events", {}).items()}
        self.hidden = set(scenario.get("hide_from_agent", []))   # facts the agent is not shown
        self.effects = []          # every change actually made to the world

    # ---- time -------------------------------------------------------------
    def advance(self):
        self.step += 1
        for key, value in self.events.get(self.step, {}).items():
            if key == "notes":
                # Text that appears inside shipment records: data, not authority.
                for sid, note in value.items():
                    for s in self.shipments:
                        if s["id"] == sid:
                            s["note"] = note
                continue
            setattr(self, key, value)
            if key == "disruption_status" and value != "active":
                # The storm has passed: the highway reopens, so normal routes recover.
                for s in self.shipments:
                    s["road_closed"] = False
                    if s["route"] == "standard":
                        s["eta_hours"] = s["normal_eta_hours"]
        return self.step

    # ---- facts the gate may consult (read-only) -----------------------------
    def fact(self, name):
        return getattr(self, name)

    def observe(self):
        """What the environment shows the agent each step (minus any hidden facts)."""
        view = self.read_shipments()
        for fact in self.hidden:
            view.pop(fact, None)
        return view

    # ---- tools --------------------------------------------------------------
    def read_shipments(self):
        return {
            "step": self.step,
            "disruption_status": self.disruption_status,
            "shipments": copy.deepcopy(self.shipments),
        }

    def reroute_shipment(self, shipment_id, route="express"):
        s = next((x for x in self.shipments if x["id"] == shipment_id), None)
        if s is None:
            return {"ok": False, "error": f"no shipment {shipment_id}"}
        if s["route"] == route:
            return {"ok": False, "error": "already on that route"}
        s["route"] = route
        s["eta_hours"] = s["express_eta_hours"]
        self.spent += self.reroute_cost
        effect = {
            "step": self.step,
            "tool": "reroute_shipment",
            "shipment": shipment_id,
            "during_disruption": self.disruption_status == "active",
            "road_was_closed": s["road_closed"],
            "cost": self.reroute_cost,
        }
        self.effects.append(effect)
        return {"ok": True, "effect": effect}

    def cancel_shipment(self, shipment_id):
        s = next((x for x in self.shipments if x["id"] == shipment_id), None)
        if s is None:
            return {"ok": False, "error": f"no shipment {shipment_id}"}
        s["route"] = "cancelled"
        effect = {"step": self.step, "tool": "cancel_shipment", "shipment": shipment_id,
                  "during_disruption": self.disruption_status == "active",
                  "road_was_closed": s["road_closed"], "cost": 0}
        self.effects.append(effect)
        return {"ok": True, "effect": effect}

    def tools(self):
        """The tool functions. Only a gate should ever hold this dictionary."""
        return {
            "read_shipments": self.read_shipments,
            "reroute_shipment": self.reroute_shipment,
            "cancel_shipment": self.cancel_shipment,
        }
