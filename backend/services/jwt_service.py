"""
Token service for WebSocket authentication with Centrifugo.
"""

import logging
import time

import jwt

from config import CENTRIFUGO_SECRET

logger = logging.getLogger(__name__)


def generate_ws_token(user_id: str, expiry_minutes: int = 60 * 24) -> str:
    """
    Generate a connection token for WebSocket connections with Centrifugo.

    Args:
        user_id: The user ID to include in the token
        expiry_minutes: Token expiry time in minutes (default: 24 hours)

    Returns:
        str: Connection token
    """
    # Calculate expiration time
    exp = int(time.time()) + (expiry_minutes * 60)

    # Create token claims
    claims = {
        "sub": user_id,  # Subject (user ID) - required by Centrifugo
        "exp": exp,  # Expiration time as Unix timestamp
        "iat": int(time.time()),  # Issued at time
        "info": {  # Additional user info
            "user_id": user_id,
        },
        "channels": [  # Channel permissions
            f"user:{user_id}",  # User's personal channel
        ],
    }

    # Generate JWT token using HS256 algorithm
    token = jwt.encode(claims, CENTRIFUGO_SECRET, algorithm="HS256")

    logger.debug(f"Generated WebSocket token for user {user_id}: {token[:20]}...")
    return token


def decode_ws_token(token: str) -> dict:
    """
    Decode and validate a WebSocket token.

    Args:
        token: Token to decode

    Returns:
        dict: Payload from the token

    Raises:
        ValueError: If token is invalid
    """
    try:
        # Decode JWT token
        claims = jwt.decode(token, CENTRIFUGO_SECRET, algorithms=["HS256"])

        # Check expiration
        if claims["exp"] < int(time.time()):
            raise ValueError("Token expired")

        return claims
    except Exception as e:
        logger.error(f"Token error: {e!s}")
        raise ValueError(f"Invalid token: {e!s}") from e
