from fastapi import Depends, Header, HTTPException, status

from ..config import Settings, get_settings


def require_worker_key(
    x_worker_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> None:
    if not settings.worker_api_key:
        return

    if not x_worker_key or x_worker_key != settings.worker_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Worker key invalida.",
        )
