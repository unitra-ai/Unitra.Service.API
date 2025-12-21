"""Shared dependencies for dependency injection."""

from typing import Annotated, AsyncGenerator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings, get_settings
from app.db.session import get_db_session
from app.db.redis import get_redis_client

# Settings dependency
SettingsDep = Annotated[Settings, Depends(get_settings)]

# Database session dependency
DbSessionDep = Annotated[AsyncSession, Depends(get_db_session)]

# Redis client dependency - will be typed properly when redis is set up
RedisDep = Annotated[object, Depends(get_redis_client)]
