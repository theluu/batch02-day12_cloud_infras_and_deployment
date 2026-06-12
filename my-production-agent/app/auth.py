"""API key authentication — header X-API-Key, trả về user_id."""
from fastapi import HTTPException, Security
from fastapi.security.api_key import APIKeyHeader

from .config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def verify_api_key(api_key: str = Security(api_key_header)) -> str:
    if not api_key:
        raise HTTPException(
            status_code=401,
            detail="Missing API key. Include header: X-API-Key: <your-key>",
        )
    user_id = settings.api_key_map().get(api_key)
    if user_id is None:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return user_id
