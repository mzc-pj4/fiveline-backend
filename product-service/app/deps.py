from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False, scheme_name="JWT")


class CurrentUser:
    def __init__(self, user_id: int, role: str, name: str = "") -> None:
        self.user_id = user_id
        self.role = role
        self.name = name


def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    if creds is None or not creds.credentials:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "missing bearer token")
    claims = decode_token(creds.credentials)
    try:
        return CurrentUser(
            user_id=int(claims["sub"]),
            role=claims.get("role", "customer"),
            name=claims.get("name", ""),
        )
    except (KeyError, ValueError):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "invalid token claims")
