"""Initial rules for review suggestions; this is not an AI model."""
import re


def suggest_triage(issue: str) -> dict[str, str]:
    words = set(re.findall(r"[a-z]+", issue.lower()))
    if words & {"gas", "smoke", "fire", "sparks", "flood", "flooding"}:
        priority, trade, action = (
            "high", "urgent assessment",
            "Escalate immediately to the property manager for safety assessment and appropriate emergency routing.",
        )
    elif words & {"boiler", "heating", "radiator"}:
        priority, trade, action = "high", "heating engineer", "Confirm loss of heating or hot water and request an assessment for approval."
    elif words & {"leak", "leaking", "tap", "toilet", "pipe", "plumbing"}:
        priority, trade, action = "medium", "plumber", "Confirm the location and extent of the issue, then request a repair assessment."
    elif words & {"electrical", "electricity", "socket", "wiring", "power"}:
        priority, trade, action = "high", "electrician", "Request a qualified electrical assessment for approval."
    else:
        priority, trade, action = "medium", "general maintenance", "Ask for more detail and photos before assigning a contractor."
    return dict(suggested_priority=priority, suggested_trade=trade,
                recommended_action=action,
                rationale="Initial keyword rules; a person must confirm context and urgency.",
                source="rules-v1")
