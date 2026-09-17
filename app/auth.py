import base64
import json

from fastapi import Depends, Header, HTTPException


def get_current_user(
    x_ms_client_principal: str | None = Header(
        default=None,
        alias="X-MS-CLIENT-PRINCIPAL",
    ),
):
    if not x_ms_client_principal:
        raise HTTPException(
            status_code=401,
            detail="Authentication required",
        )

    try:
        decoded = base64.b64decode(
            x_ms_client_principal
        ).decode("utf-8")

        principal = json.loads(decoded)

    except (
        ValueError,
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication information",
        )

    claims = principal.get("claims", [])

    roles = {
        claim.get("val")
        for claim in claims
        if claim.get("typ") == "roles"
    }

    actor = None

    for claim in claims:
        claim_type = claim.get("typ", "").lower()

        if claim_type in {
            "preferred_username",
            "email",
            "upn",
        }:
            actor = claim.get("val")
            break

    if not actor:
        actor = principal.get("name")

    return {
        "actor": actor or "authenticated-user",
        "roles": roles,
        "claims": claims,
    }


def require_role(required_role: str):
    def role_checker(
        user=Depends(get_current_user),
    ):
        roles = user["roles"]

        # Manager inherits normal user access.
        if "PropertyOps.Manager" in roles:
            return user

        if required_role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions",
            )

        return user

    return role_checker