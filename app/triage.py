"""Choose explicit triage mode; local keyword rules are the default."""
import re


def suggest_triage(issue: str) -> dict[str, str]:
    from app.ai_triage import TriageUnavailable, settings, suggest_ai_triage, triage_mode

    if triage_mode() == "rules":
        return suggest_rules_triage(issue)
    key, model = settings()
    if not key:
        raise TriageUnavailable("OpenAI mode requires OPENAI_API_KEY. Set TRIAGE_MODE=rules to work offline.")
    return suggest_ai_triage(issue, key, model)


def suggest_rules_triage(issue: str) -> dict[str, str]:
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
