import os

from fastapi import Header, HTTPException, status


def _parse_api_keys() -> set[str]:
    # Comma separated list: NEUROWEAVE_API_KEYS="devkey1,devkey2"
    raw = os.getenv("NEUROWEAVE_API_KEYS", "dev-local-key")
    return {item.strip() for item in raw.split(",") if item.strip()}


def require_api_key(x_api_key: str | None = Header(default=None)) -> str:
    valid_keys = _parse_api_keys()
    if not x_api_key or x_api_key not in valid_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key",
        )
    return x_api_key
