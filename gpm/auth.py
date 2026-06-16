from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader

from gpm.config import settings

_api_key_header = APIKeyHeader(name="X-GPM-API-Key", auto_error=False)


async def require_gpm_api_key(api_key: str | None = Security(_api_key_header)) -> str:
    """
    Validates the internal API key sent by abcdyi (or other trusted callers).
    All GPM endpoints require this header.
    """
    if not api_key or api_key != settings.GPM_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing GPM API key",
        )
    return api_key
