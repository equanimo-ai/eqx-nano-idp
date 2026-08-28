"""
Clerk verification for the admin Web UI's optional Clerk sign-in.

This only guards the admin dashboard (routes/ui.py); it has no effect on the
OAuth2/OIDC/SAML endpoints NanoIDP issues to relying parties. clerk-backend-api
is imported lazily so installs that never set clerk.secret_key in settings.yaml
don't need the dependency (see the 'clerk' extra in pyproject.toml).
"""

import base64
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


def clerk_frontend_api(publishable_key: str) -> Optional[str]:
    """Derive the Clerk Frontend API host from a publishable key.

    A publishable key is 'pk_<env>_<base64>', where the base64 segment
    decodes to '<frontend-api-host>$'. Used only to build the CDN script URLs
    for the embedded sign-in widget; carries no secret.
    """
    parts = publishable_key.split("_", 2)
    if len(parts) != 3:
        return None

    encoded = parts[2]
    padded = encoded + "=" * (-len(encoded) % 4)
    try:
        decoded = base64.b64decode(padded).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None

    return decoded.rstrip("$")


def verify_clerk_session(request: Any, secret_key: str, authorized_party: str) -> Optional[Any]:
    """Verify the Clerk session on an incoming Flask request.

    Returns the verified token payload, or None if the request carries no
    valid Clerk session. 'authorized_party' (this app's own origin) guards
    against the subdomain cookie-leaking attack Clerk's docs warn about.
    """
    from clerk_backend_api import Clerk
    from clerk_backend_api.security.types import AuthenticateRequestOptions

    client = Clerk(bearer_auth=secret_key)
    state = client.authenticate_request(
        request,
        AuthenticateRequestOptions(authorized_parties=[authorized_party]),
    )
    if not state.is_signed_in:
        return None
    return state.payload


def clerk_username(payload: Any) -> str:
    """Best-effort human-readable identity from a verified session payload.

    The default Clerk session token only carries the user id ('sub'); email
    only appears if the Clerk instance's session token was customized to
    include it.
    """
    get = payload.get if isinstance(payload, dict) else (lambda k, d=None: getattr(payload, k, d))
    return get("email") or get("sub") or "clerk-user"
