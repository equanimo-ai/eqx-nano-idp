"""
Clerk Authentication Service for NanoIDP.
Protects Dashboard, Admin, and UI routes with Clerk session authentication.
"""

import logging
import os
import time
from typing import Any, Dict, List, Optional, Set
from urllib.parse import quote

import jwt
from jwt import PyJWKClient
from flask import (
    Flask,
    Response,
    jsonify,
    redirect,
    render_template_string,
    request,
    session,
)

logger = logging.getLogger(__name__)

# Protected paths that require Clerk authentication (UI, Dashboard, Settings, Config API)
PROTECTED_PREFIXES = (
    "/api/config/",
    "/ui/",
    "/settings",
    "/clients",
    "/users",
    "/wizard",
    "/audit",
)

PROTECTED_EXACT_PATHS: Set[str] = {
    "/",
    "/settings",
    "/clients",
    "/users",
    "/wizard",
    "/audit",
}

_jwk_client_cache: Dict[str, PyJWKClient] = {}


def _get_jwk_client(jwks_url: str) -> PyJWKClient:
    """Get or create a cached PyJWKClient instance."""
    if jwks_url not in _jwk_client_cache:
        _jwk_client_cache[jwks_url] = PyJWKClient(jwks_url, cache_jwk_set=True, lifespan=3600)
    return _jwk_client_cache[jwks_url]


class ClerkAuthService:
    """Service to handle Clerk session verification and access control."""

    def __init__(
        self,
        enabled: bool = False,
        publishable_key: str = "",
        secret_key: str = "",
        frontend_api: str = "",
        sign_in_url: str = "",
        jwks_url: str = "",
        allowed_domains: Optional[List[str]] = None,
        allowed_emails: Optional[List[str]] = None,
        allowed_orgs: Optional[List[str]] = None,
    ) -> None:
        self.enabled = enabled or bool(os.environ.get("CLERK_ENABLED", "").lower() in ("true", "1"))
        self.publishable_key = (
            publishable_key
            or os.environ.get("CLERK_PUBLISHABLE_KEY")
            or os.environ.get("NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY", "")
        )
        self.secret_key = secret_key or os.environ.get("CLERK_SECRET_KEY", "")
        self.frontend_api = frontend_api or os.environ.get("CLERK_FRONTEND_API", "")
        self.sign_in_url = sign_in_url or os.environ.get("CLERK_SIGN_IN_URL", "")
        self.jwks_url = jwks_url or os.environ.get("CLERK_JWKS_URL", "")
        self.allowed_domains = allowed_domains or [
            d.strip() for d in os.environ.get("CLERK_ALLOWED_DOMAINS", "").split(",") if d.strip()
        ]
        self.allowed_emails = allowed_emails or [
            e.strip().lower() for e in os.environ.get("CLERK_ALLOWED_EMAILS", "").split(",") if e.strip()
        ]
        self.allowed_orgs = allowed_orgs or [
            o.strip() for o in os.environ.get("CLERK_ALLOWED_ORGS", "").split(",") if o.strip()
        ]

        # Derive JWKS URL from Frontend API / Publishable Key if not explicitly configured
        if self.enabled and not self.jwks_url:
            if self.frontend_api:
                clean_api = self.frontend_api.rstrip("/")
                if not clean_api.startswith("http"):
                    clean_api = f"https://{clean_api}"
                self.jwks_url = f"{clean_api}/.well-known/jwks.json"
            elif self.publishable_key:
                # Clerk publishable key encodes frontend API: pk_test_<base64> or pk_live_<base64>
                try:
                    import base64
                    key_part = self.publishable_key.split("_")[-1]
                    # Add padding
                    padding = 4 - (len(key_part) % 4)
                    if padding != 4:
                        key_part += "=" * padding
                    decoded = base64.b64decode(key_part).decode("utf-8", errors="ignore").rstrip("$")
                    if decoded:
                        self.frontend_api = decoded
                        self.jwks_url = f"https://{decoded}/.well-known/jwks.json"
                except Exception as e:
                    logger.warning(f"Could not derive Clerk JWKS URL from publishable key: {e}")

    def is_protected_path(self, path: str) -> bool:
        """Check if request path requires Clerk auth."""
        if path in PROTECTED_EXACT_PATHS:
            return True
        for prefix in PROTECTED_PREFIXES:
            if path.startswith(prefix):
                return True
        return False


    def extract_token(self) -> Optional[str]:
        """Extract Clerk JWT session token from request cookies or headers."""
        # 1. Bearer header
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            return auth_header[7:].strip()

        # 2. Clerk custom header
        if "x-clerk-auth-token" in request.headers:
            return request.headers["x-clerk-auth-token"].strip()

        # 3. Standard Clerk session cookies
        if "__session" in request.cookies:
            return request.cookies["__session"].strip()

        return None

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify Clerk session token using JWKS."""
        if not self.jwks_url:
            raise ValueError("Clerk JWKS URL is not configured")

        jwk_client = _get_jwk_client(self.jwks_url)
        signing_key = jwk_client.get_signing_key_from_jwt(token)

        # Verify RS256 token
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_exp": True, "verify_nbf": True},
        )

        # Validate authorized party / email / domains if configured
        email = claims.get("email") or claims.get("email_address") or ""
        if self.allowed_emails and email.lower() not in self.allowed_emails:
            raise PermissionError(f"Email {email} is not in allowed list")

        if self.allowed_domains and email:
            domain = "@" + email.split("@")[-1].lower()
            if not any(domain.endswith(d.lower()) for d in self.allowed_domains):
                raise PermissionError(f"Domain {domain} is not in allowed list")

        # Validate authorized organization if configured
        user_org_id = claims.get("org_id") or claims.get("orgId") or (claims.get("org") or {}).get("id") or ""
        if self.allowed_orgs:
            if not user_org_id or user_org_id not in self.allowed_orgs:
                raise PermissionError(f"Organization '{user_org_id}' is not in allowed list: {self.allowed_orgs}")

        return claims

    def _get_external_url(self) -> str:
        """Get canonical external HTTPS request URL behind reverse proxy."""
        proto = request.headers.get("X-Forwarded-Proto") or ("https" if request.is_secure else request.scheme)
        if "equanimo.io" in request.host or request.headers.get("X-Forwarded-Proto") == "https":
            proto = "https"
        host = request.headers.get("X-Forwarded-Host") or request.host
        path = request.full_path.rstrip("?") if request.query_string else request.path
        return f"{proto}://{host}{path}"

    def handle_unauthenticated(self) -> Response:
        """Handle unauthenticated browser or API request."""
        # API / JSON request -> return 401 JSON
        if (
            request.path.startswith("/api/")
            or request.headers.get("Accept", "").startswith("application/json")
            or request.is_json
        ):
            return jsonify({
                "error": "unauthorized",
                "message": "Clerk authentication required for administrative access",
            }), 401

        # Handle Clerk Account Portal return handshake
        if any(k in request.args for k in ("__clerk_handshake", "__clerk_ticket", "__clerk_status", "__clerk_created_session")):
            handshake_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Completing Sign In - NanoIDP</title>
    <script
        async
        crossorigin="anonymous"
        data-clerk-publishable-key="{{ publishable_key }}"
        src="https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.browser.js"
        type="text/javascript">
    </script>
    <style>
        body {
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
            text-align: center;
        }
        .spinner {
            width: 48px;
            height: 48px;
            border: 4px solid rgba(56, 189, 248, 0.2);
            border-top-color: #38bdf8;
            border-radius: 50%;
            animation: spin 1s linear infinite;
            margin: 0 auto 1.5rem;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
    </style>
</head>
<body>
    <div>
        <div class="spinner"></div>
        <h2 style="font-weight: 600; margin-bottom: 0.5rem;">Completing authentication...</h2>
        <p style="color: #94a3b8;">Establishing session with NanoIDP</p>
    </div>
    <script>
        window.addEventListener("load", async function () {
            try {
                await window.Clerk.load();
                // Strip clerk query parameters and reload to dashboard
                const cleanUrl = window.location.origin + window.location.pathname;
                window.location.replace(cleanUrl);
            } catch (err) {
                console.error("Clerk handshake error:", err);
                window.location.reload();
            }
        });
    </script>
</body>
</html>
            """
            return render_template_string(handshake_html, publishable_key=self.publishable_key)

        external_url = self._get_external_url()


        # Redirect to configured Clerk Sign-In URL if set
        if self.sign_in_url:
            redirect_url = quote(external_url, safe="")
            sep = "&" if "?" in self.sign_in_url else "?"
            return redirect(f"{self.sign_in_url}{sep}redirect_url={redirect_url}")


        # Render integrated Clerk login template
        login_html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>NanoIDP - Clerk Sign In</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css">
    <style>
        body {
            background-color: #0f172a;
            color: #f8fafc;
            display: flex;
            align-items: center;
            justify-content: center;
            min-height: 100vh;
            margin: 0;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        }
        .card {
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            box-shadow: 0 20px 25px -5px rgba(0, 0, 0, 0.5);
            max-width: 480px;
            width: 100%;
            padding: 2rem;
        }
        .brand {
            font-size: 1.5rem;
            font-weight: 700;
            color: #38bdf8;
            margin-bottom: 0.5rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
    </style>
    {% if publishable_key %}
    <script
        async
        crossorigin="anonymous"
        data-clerk-publishable-key="{{ publishable_key }}"
        src="https://cdn.jsdelivr.net/npm/@clerk/clerk-js@5/dist/clerk.browser.js"
        type="text/javascript">
    </script>
    {% endif %}
</head>
<body>
    <div class="card text-center">
        <div class="brand justify-content-center">
            <span>🛡️ NanoIDP</span>
        </div>
        <p class="text-secondary mb-4">Authentication Required</p>

        <div id="clerk-sign-in" class="d-flex justify-content-center my-3"></div>

        {% if not publishable_key and not sign_in_url %}
        <div class="alert alert-warning text-start small">
            <strong>Clerk Protection Enabled:</strong><br>
            Please set <code>CLERK_PUBLISHABLE_KEY</code>, <code>CLERK_SECRET_KEY</code>, or <code>CLERK_SIGN_IN_URL</code> in environment to complete setup.
        </div>
        {% endif %}
    </div>

    {% if publishable_key %}
    <script>
        window.addEventListener("load", async function () {
            await window.Clerk.load();
            if (window.Clerk.user) {
                // User is already signed in -> redirect back to requested URL
                window.location.reload();
            } else {
                const signInDiv = document.getElementById("clerk-sign-in");
                window.Clerk.mountSignIn(signInDiv, {
                    afterSignInUrl: window.location.href,
                    afterSignUpUrl: window.location.href,
                });
            }
        });
    </script>
    {% endif %}
</body>
</html>
        """
        return render_template_string(
            login_html,
            publishable_key=self.publishable_key,
            sign_in_url=self.sign_in_url,
        )


def init_clerk_auth(app: Flask, config_settings: Any) -> ClerkAuthService:
    """Initialize Clerk authentication middleware on the Flask app."""
    service = ClerkAuthService(
        enabled=getattr(config_settings, "clerk_enabled", False),
        publishable_key=getattr(config_settings, "clerk_publishable_key", ""),
        secret_key=getattr(config_settings, "clerk_secret_key", ""),
        frontend_api=getattr(config_settings, "clerk_frontend_api", ""),
        sign_in_url=getattr(config_settings, "clerk_sign_in_url", ""),
        jwks_url=getattr(config_settings, "clerk_jwks_url", ""),
        allowed_domains=getattr(config_settings, "clerk_allowed_domains", []),
        allowed_emails=getattr(config_settings, "clerk_allowed_emails", []),
        allowed_orgs=getattr(config_settings, "clerk_allowed_orgs", []),
    )

    if not service.enabled:
        logger.info("  - Clerk Authentication: disabled")
        return service

    logger.info("  - Clerk Authentication: ENABLED")
    if service.frontend_api:
        logger.info(f"    Frontend API: {service.frontend_api}")
    if service.jwks_url:
        logger.info(f"    JWKS URL: {service.jwks_url}")

    @app.before_request
    def enforce_clerk_auth() -> Optional[Response]:
        if not service.enabled:
            return None

        # Only enforce Clerk on protected UI/Admin paths
        if not service.is_protected_path(request.path):
            return None

        token = service.extract_token()
        if not token:
            return service.handle_unauthenticated()

        try:
            claims = service.verify_token(token)
            # Store claims in session and flask request context
            session["clerk_user"] = claims
            return None
        except Exception as e:
            logger.warning(f"Clerk token verification failed: {e}")
            return service.handle_unauthenticated()

    return service
