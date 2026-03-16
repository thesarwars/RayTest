"""FastAPI dependencies for auth and common injection."""

from uuid import UUID

import jwt
from fastapi import Depends, Header

from app.core.exceptions import AuthenticationError
from app.core.security import decode_access_token
from app.db.session import AsyncSession, get_db


async def get_current_user_id(authorization: str = Header(...)) -> UUID:
    """Extract and validate the JWT from the Authorization header.

    Expects: ``Authorization: Bearer <token>``
    """
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise AuthenticationError("Missing or malformed Authorization header")
    try:
        payload = decode_access_token(token)
    except jwt.ExpiredSignatureError:
        raise AuthenticationError("Token has expired")
    except jwt.InvalidTokenError:
        raise AuthenticationError("Invalid token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthenticationError("Token missing subject")
    return UUID(user_id)
