import hmac
from fastapi import Header, HTTPException, status
from config import CONTINUITY_DEMO_KEY

async def verify_demo_key(x_continuity_demo_key: str = Header(None, alias="X-Continuity-Demo-Key")):
    """Validates the static demo write-guard header for mutation routes.
    
    This operates as demo friction against automated web scrapers, crawlers, and accidental
    internet traffic mutating state. Because the frontend is statically exported and ships
    the default key in client-side bundles, this is intentionally characterized as a demo
    write guard rather than an enterprise identity/authentication boundary.
    """
    if not CONTINUITY_DEMO_KEY:
        return True
    
    if not x_continuity_demo_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing required X-Continuity-Demo-Key write-guard header"
        )
    
    if not hmac.compare_digest(x_continuity_demo_key, CONTINUITY_DEMO_KEY):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid X-Continuity-Demo-Key write-guard header"
        )
    return True
