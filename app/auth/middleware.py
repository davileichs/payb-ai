"""
Authentication middleware for JWT token validation.
"""

from typing import Optional
from fastapi import Request, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.auth.jwt_handler import get_jwt_handler


class JWTBearer(HTTPBearer):
    """JWT Bearer token authentication scheme."""
    
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)
        self.jwt_handler = get_jwt_handler()
    
    async def __call__(self, request: Request) -> Optional[HTTPAuthorizationCredentials]:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        
        if not credentials:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authorization code."
                )
            return None
        
        if credentials.scheme != "Bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid authentication scheme."
                )
            return None
        
        # Verify the JWT token
        payload = self.jwt_handler.verify_token(credentials.credentials)
        if not payload:
            if self.auto_error:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Invalid token or expired token."
                )
            return None
        
        # Add user info to request state
        request.state.user = payload
        return credentials


def get_current_user(request: Request) -> dict:
    """Get the current authenticated user from request state."""
    if not hasattr(request.state, 'user'):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
        )
    return request.state.user


# Global auth dependency
auth_scheme = JWTBearer()
