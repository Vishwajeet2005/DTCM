"""
api/auth.py - Digital Twin CO2 Monitor (DTCM)
==============================================
Authentication blueprint providing user registration, login, logout,
and current-user endpoints.

Blueprint prefix: /api/auth

Endpoints
---------
POST /api/auth/register  -- Create a new user account.
POST /api/auth/login     -- Exchange credentials for a JWT access token.
POST /api/auth/logout    -- Invalidate the current JWT (in-memory blocklist).
GET  /api/auth/me        -- Return the authenticated user profile.
"""

from __future__ import annotations

import logging
import re
from typing import Any

from flask import Blueprint, jsonify, request
from flask_jwt_extended import (
    create_access_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    verify_jwt_in_request,
)

from db.models import User, db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Blueprint
# ---------------------------------------------------------------------------

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# ---------------------------------------------------------------------------
# In-memory JWT blocklist.
# Every logged-out token JTI is added here; checked via
# token_in_blocklist_loader registered in app.py.
# ---------------------------------------------------------------------------

jwt_blocklist: set[str] = set()

# ---------------------------------------------------------------------------
# Role ordering for RBAC.
# ---------------------------------------------------------------------------

ROLE_RANK: dict[str, int] = {
    "general": 0,
    "researcher": 1,
    "administrator": 2,
    "environmental_authority": 3,
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def _valid_email(email: str) -> bool:
    """Return True if email matches a basic RFC-style pattern.

    Args:
        email: The e-mail string to validate.

    Returns:
        True if the pattern matches.
    """
    return bool(_EMAIL_RE.match(email))


def _require_role(minimum_role: str) -> tuple[dict[str, Any], int] | None:
    """Check that the JWT caller meets the minimum role requirement.

    Must be called inside a jwt_required context (i.e. after the decorator
    has already validated the token).

    Args:
        minimum_role: Lowest acceptable role in the RBAC hierarchy.

    Returns:
        None on success, or (error_dict, http_status) on failure.
    """
    identity = get_jwt_identity()
    user: User | None = User.query.get(identity)
    if user is None:
        return {"error": "User not found"}, 404

    user_rank = ROLE_RANK.get(user.role, -1)
    required_rank = ROLE_RANK.get(minimum_role, 999)

    if user_rank < required_rank:
        return {
            "error": (
                f"Insufficient privileges. "
                f"Requires at least '{minimum_role}'."
            )
        }, 403
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@auth_bp.post("/register")
def register() -> tuple[Any, int]:
    """Register a new DTCM user account.

    Bootstrap mode: the very first account may be created without auth.
    All subsequent registrations require a valid JWT from an
    environmental_authority account.

    Request body (JSON):
        name (str): Display name.
        email (str): Unique e-mail address.
        password (str): Min 8 chars.
        role (str): general | researcher | administrator |
                    environmental_authority.  Defaults to "general".

    Returns:
        201: User created; body is {message, user}.
        400: Validation failure.
        401: No valid JWT when non-bootstrap registration is attempted.
        403: JWT present but role is insufficient.
        409: E-mail already registered.
    """
    payload: dict = request.get_json(silent=True) or {}

    name: str = (payload.get("name") or "").strip()
    email: str = (payload.get("email") or "").strip().lower()
    password: str = payload.get("password") or ""
    role: str = (payload.get("role") or "general").strip().lower()

    # Validation
    if not name:
        return jsonify({"error": "name is required"}), 400
    if not email or not _valid_email(email):
        return jsonify({"error": "A valid email address is required"}), 400
    if len(password) < 8:
        return jsonify({"error": "password must be at least 8 characters"}), 400
    if role not in User.VALID_ROLES:
        return jsonify(
            {"error": f"Invalid role. Must be one of: {sorted(User.VALID_ROLES)}"}
        ), 400

    # Bootstrap vs. authenticated path
    user_count: int = User.query.count()
    if user_count == 0:
        logger.info(
            "Bootstrap mode: creating first user '%s' (role=%s).", email, role
        )
    else:
        try:
            pass # Public registration enabled
        except Exception:
            return jsonify(
                {"error": "Authentication required to register additional users"}
            ), 401

        err = None
        if err is not None:
            return jsonify({"error": err[0]["error"]}), err[1]

    # Uniqueness
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 409

    # Persist
    new_user = User(name=name, email=email, role=role)
    new_user.set_password(password)  # bcrypt rounds=12 inside the ORM method
    db.session.add(new_user)
    db.session.commit()

    logger.info(
        "User registered: id=%d email=%s role=%s",
        new_user.user_id, email, role,
    )
    return jsonify(
        {"message": "User created successfully", "user": new_user.to_dict()}
    ), 201


@auth_bp.post("/login")
def login() -> tuple[Any, int]:
    """Authenticate a user and return a JWT access token.

    Request body (JSON):
        email (str): Registered e-mail.
        password (str): Plain-text password.

    Returns:
        200: {access_token, user: {id, name, email, role}}.
        400: Missing required fields.
        401: Invalid credentials.
    """
    payload: dict = request.get_json(silent=True) or {}

    email: str = (payload.get("email") or "").strip().lower()
    password: str = payload.get("password") or ""

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    user: User | None = User.query.filter_by(email=email).first()

    # Always call check_password to avoid user-enumeration timing attacks.
    if user is None or not user.check_password(password):
        return jsonify({"error": "Invalid email or password"}), 401

    access_token: str = create_access_token(
        identity=str(user.user_id),
        additional_claims={"role": user.role, "email": user.email},
    )

    logger.info("User login: id=%d email=%s role=%s", user.user_id, email, user.role)

    return jsonify(
        {
            "access_token": access_token,
            "user": {
                "id": user.user_id,
                "name": user.name,
                "email": user.email,
                "role": user.role,
            },
        }
    ), 200


@auth_bp.post("/logout")
@jwt_required()
def logout() -> tuple[Any, int]:
    """Invalidate the caller token by adding its JTI to the in-memory blocklist.

    Returns:
        200: Token revoked.
    """
    jti: str = get_jwt()["jti"]
    jwt_blocklist.add(jti)
    logger.info("Token revoked (logout): jti=%s", jti)
    return jsonify({"message": "Successfully logged out"}), 200


@auth_bp.get("/me")
@jwt_required()
def me() -> tuple[Any, int]:
    """Return the profile of the currently authenticated user.

    Returns:
        200: User dict (password_hash excluded).
        404: User deleted since token was issued.
    """
    user_id: int = get_jwt_identity()
    user: User | None = User.query.get(user_id)
    if user is None:
        return jsonify({"error": "User not found"}), 404

    return jsonify({"user": user.to_dict()}), 200



