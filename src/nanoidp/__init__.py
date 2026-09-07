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
from importlib.metadata import version

__version__ = version("nanoidp")
__author__ = "NanoIDP Contributors"
