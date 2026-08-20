"""Tests for Clerk authentication service and middleware."""

import pytest
import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from unittest.mock import MagicMock, patch
from flask import Flask, jsonify

from nanoidp.services.clerk_auth import ClerkAuthService, init_clerk_auth
from nanoidp.models import Settings


@pytest.fixture
def rsa_keypair():
    """Generate a test RSA keypair for JWT signing."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    return private_key, public_key


@pytest.fixture
def clerk_service():
    """Create a ClerkAuthService with test settings."""
    return ClerkAuthService(
        enabled=True,
        publishable_key="pk_test_ZXF1YW5pbW8uY2xlcmsuYWNjb3VudHMuZGV2JA",
        frontend_api="equanimo.clerk.accounts.dev",
        jwks_url="https://equanimo.clerk.accounts.dev/.well-known/jwks.json",
        allowed_domains=["@equanimo.ai"],
    )


def test_public_paths(clerk_service):
    """Test that public OAuth, SAML, and health paths are exempt."""
    assert clerk_service.is_public_path("/health") is True
    assert clerk_service.is_public_path("/api/health") is True
    assert clerk_service.is_public_path("/token") is True
    assert clerk_service.is_public_path("/authorize") is True
    assert clerk_service.is_public_path("/.well-known/openid-configuration") is True
    assert clerk_service.is_public_path("/.well-known/jwks.json") is True
    assert clerk_service.is_public_path("/oauth2/token") is True
    assert clerk_service.is_public_path("/saml/sso") is True
    assert clerk_service.is_public_path("/static/css/style.css") is True

    # Protected paths
    assert clerk_service.is_public_path("/") is False
    assert clerk_service.is_public_path("/wizard") is False
    assert clerk_service.is_public_path("/api/config/reload") is False


def test_token_extraction(clerk_service):
    """Test token extraction from Bearer header, custom header, and cookie."""
    app = Flask(__name__)

    with app.test_request_context(headers={"Authorization": "Bearer test-bearer-token"}):
        assert clerk_service.extract_token() == "test-bearer-token"

    with app.test_request_context(headers={"x-clerk-auth-token": "test-custom-token"}):
        assert clerk_service.extract_token() == "test-custom-token"

    with app.test_request_context(headers={"Cookie": "__session=test-cookie-token"}):
        assert clerk_service.extract_token() == "test-cookie-token"

    with app.test_request_context():
        assert clerk_service.extract_token() is None


def test_clerk_middleware_blocks_unauthenticated_ui(rsa_keypair):
    """Test that unauthenticated requests to protected endpoints are intercepted."""
    app = Flask(__name__)
    app.secret_key = "test-secret"
    settings = Settings(
        clerk_enabled=True,
        clerk_publishable_key="pk_test_dummy",
        clerk_sign_in_url="https://accounts.equanimo.ai/sign-in",
    )

    init_clerk_auth(app, settings)

    @app.route("/")
    def index():
        return "dashboard"

    @app.route("/api/config/sync", methods=["POST"])
    def sync_api():
        return jsonify({"status": "ok"})

    client = app.test_client()

    # Browser GET -> redirects to Clerk Sign-In
    resp = client.get("/")
    assert resp.status_code == 302
    assert "https://accounts.equanimo.ai/sign-in" in resp.headers["Location"]

    # API JSON POST -> returns 401 JSON
    resp_api = client.post("/api/config/sync", headers={"Accept": "application/json"})
    assert resp_api.status_code == 401
    assert resp_api.json["error"] == "unauthorized"


def test_clerk_token_verification(rsa_keypair):
    """Test successful token verification using mock JWKS."""
    private_key, public_key = rsa_keypair
    app = Flask(__name__)
    app.secret_key = "test-secret"

    settings = Settings(
        clerk_enabled=True,
        clerk_jwks_url="https://test.clerk.accounts.dev/.well-known/jwks.json",
        clerk_allowed_domains=["@equanimo.ai"],
    )

    init_clerk_auth(app, settings)

    @app.route("/")
    def index():
        return "dashboard"

    client = app.test_client()

    # Generate valid JWT signed with private key
    payload = {
        "sub": "user_2test123",
        "email": "engineer@equanimo.ai",
        "exp": 9999999999,
        "nbf": 0,
    }
    token = jwt.encode(payload, private_key, algorithm="RS256")

    # Mock PyJWKClient to return our test public key
    mock_jwk = MagicMock()
    mock_jwk.key = public_key
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_jwk

    with patch("nanoidp.services.clerk_auth._get_jwk_client", return_value=mock_client):
        resp = client.get("/", headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 200
        assert resp.data.decode("utf-8") == "dashboard"


def test_clerk_org_authorization(rsa_keypair):
    """Test organization gating with Clerk org_id."""
    private_key, public_key = rsa_keypair
    app = Flask(__name__)
    app.secret_key = "test-secret"

    settings = Settings(
        clerk_enabled=True,
        clerk_jwks_url="https://test.clerk.accounts.dev/.well-known/jwks.json",
        clerk_allowed_orgs=["org_3IAADDh9tenYWKUofjRdltKWc60"],
    )

    init_clerk_auth(app, settings)

    @app.route("/")
    def index():
        return "dashboard"

    client = app.test_client()
    mock_jwk = MagicMock()
    mock_jwk.key = public_key
    mock_client = MagicMock()
    mock_client.get_signing_key_from_jwt.return_value = mock_jwk

    with patch("nanoidp.services.clerk_auth._get_jwk_client", return_value=mock_client):
        # 1. Matching org -> allowed
        valid_payload = {
            "sub": "user_2test123",
            "org_id": "org_3IAADDh9tenYWKUofjRdltKWc60",
            "exp": 9999999999,
        }
        token_valid = jwt.encode(valid_payload, private_key, algorithm="RS256")
        resp = client.get("/", headers={"Authorization": f"Bearer {token_valid}"})
        assert resp.status_code == 200

        # 2. Different org -> rejected (redirected or 401)
        invalid_payload = {
            "sub": "user_2test123",
            "org_id": "org_other999",
            "exp": 9999999999,
        }
        token_invalid = jwt.encode(invalid_payload, private_key, algorithm="RS256")
        resp = client.get("/", headers={"Authorization": f"Bearer {token_invalid}"})
        assert resp.status_code == 200  # Fallback to login HTML template
        assert b"Authentication Required" in resp.data

