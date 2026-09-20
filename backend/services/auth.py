import hmac
from fastapi import Header, HTTPException, status
from config import CONTINUITY_DEMO_KEY

async def verify_demo_key(x_continuity_demo_key: str = Header(None, alias="X-Continuity-Demo-Key")):
    """Validates the static demo authorization header for mutation routes."""
    if not CONTINUITY_DEMO_KEY:
        return True
    
    if not x_continuity_demo_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Continuity-Demo-Key authorization header"
        )
    
    if not hmac.compare_digest(x_continuity_demo_key, CONTINUITY_DEMO_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Continuity-Demo-Key authorization header"
        )
    return True
