"""
Authentication helpers: password hashing and JWT issue / verification,
plus @token_required / @role_required decorators used to protect routes.
"""
import jwt
import bcrypt
import datetime
from functools import wraps
from flask import request, jsonify, g
from config import Config


def hash_password(plain_password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generate_token(user_id: str, role: str, name: str) -> str:
    payload = {
        "user_id": str(user_id),
        "role": role,
        "name": name,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXP_HOURS),
        "iat": datetime.datetime.utcnow(),
    }
    return jwt.encode(payload, Config.JWT_SECRET_KEY, algorithm=Config.JWT_ALGORITHM)


def decode_token(token: str):
    return jwt.decode(token, Config.JWT_SECRET_KEY, algorithms=[Config.JWT_ALGORITHM])


def token_required(f):
    """Require a valid Bearer JWT. Populates flask.g.user with the decoded payload."""

    @wraps(f)
    def decorated(*args, **kwargs):
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({"success": False, "message": "Authorization token is missing"}), 401
        token = auth_header.split(" ", 1)[1]
        try:
            payload = decode_token(token)
        except jwt.ExpiredSignatureError:
            return jsonify({"success": False, "message": "Token has expired, please log in again"}), 401
        except jwt.InvalidTokenError:
            return jsonify({"success": False, "message": "Invalid token"}), 401

        g.user = payload
        return f(*args, **kwargs)

    return decorated


def role_required(*roles):
    """Restrict a route to one or more roles. Use together with @token_required."""

    def wrapper(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if g.user.get("role") not in roles:
                return jsonify({"success": False, "message": "You do not have permission to perform this action"}), 403
            return f(*args, **kwargs)

        return decorated

    return wrapper
