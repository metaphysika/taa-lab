"""Transfer-offer data operations. Standing never confers tool authority."""
def entries(duty):
    if "transfer_offers" in duty["content"]:
        return duty["content"]["transfer_offers"]
    return ([{"to": duty["offered_to"], "expires": duty["offer_deadline_step"], "status": "live"}]
            if duty.get("offered_to") else [])


def offer_to(duty, actor):
    return next((o for o in entries(duty) if o["status"] == "live" and o["to"] == actor), None)


def project(duty):
    live = [o for o in entries(duty) if o["status"] == "live"]
    duty["offered_to"] = live[0]["to"] if live else None
    duty["offer_deadline_step"] = live[0]["expires"] if live else None


def add(duty, actor, expires):
    offers = duty["content"].setdefault("transfer_offers", entries(duty))
    if not offer_to(duty, actor):
        offers.append({"to": actor, "expires": expires, "status": "live"})
    project(duty)


def accept(duty, actor, authority):
    offers = duty["content"].setdefault("transfer_offers", entries(duty))
    for o in offers:
        if o["status"] == "live":
            o["status"] = "accepted" if o["to"] == actor else "closed_by_acceptance"
    duty["owner"] = actor
    duty["interim_rule"].update(authority_lost=False, authority_baseline=authority)
    project(duty)
