from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_token

security = HTTPBearer()


def current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        return decode_token(credentials.credentials)
    except Exception as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        ) from error


def require_roles(*roles):
    def dependency(user=Depends(current_user)):
        if user.get("role") not in roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
        return user

    return dependency
