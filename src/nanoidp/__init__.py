"""
NanoIDP - Lightweight Identity Provider
=======================================
A configurable identity provider for testing OAuth2/OIDC and SAML integrations.

Features:
- OAuth2 token endpoint with password and client_credentials grants
- OIDC discovery and JWKS endpoints
- SAML SSO and metadata endpoints
- Configurable users with custom attributes
- Web UI for monitoring and testing
"""
try:
    from importlib.metadata import PackageNotFoundError, version
    __version__ = version("nanoidp")
except Exception:
    __version__ = "2.5.0"

__author__ = "NanoIDP Contributors"

