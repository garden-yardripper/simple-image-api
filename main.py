from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
from aiomysql import MySQLError
import redis.asyncio as redis
from redis.exceptions import RedisError
from logs import setup_logging
from config import settings
from typing import cast
from exceptions import RateLimitedError, ApiKeyMissingError
import logging
import database
import os

os.makedirs(settings.image_directory, exist_ok=True)

setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # startup
    logger.info("Creating database connection pool...")
    
    try:
        db_pool = await database.create_pool()
    except MySQLError:
        logger.exception("Database connection failed to be established.")
        raise
    db = database.Database(db_pool)
    app.state.db = db
    
    logger.info("Database connection pool established successfully.")
    
    logger.info("Creating Redis connection pool...")
    try:
        redis_pool = redis.ConnectionPool(
            max_connections=settings.redis.max_connections,
            host=settings.redis.host,
            port=settings.redis.port
        )
        r = redis.Redis(connection_pool=redis_pool)
    except RedisError:
        logger.exception("Redis connection failed to be established.")
        raise
    app.state.r = r
    
    logger.info("Redis connection pool established successfully.")
    
    yield
    
    # shutdown
    logger.info("Closing database connection pool...")
    db_pool.close()
    await db_pool.wait_closed()
    logger.info("Database connection pool closed successfully.")
    
    logger.info("Closing Redis connection pool and client...")
    await r.aclose(close_connection_pool=True)
    logger.info("Redis connection pool closed successfully.")

app = FastAPI(lifespan=lifespan)

async def check_rate_limit(api_key: str, rate: int | None = None, per: int | None = None):
    """Raises `RateLimitedError` (`HTTPException`) if `api_key` is exceeding rate limits - 
    setting `rate` or `per` overrides settings."""
    r = cast(redis.Redis, app.state.r)
    
    key = f"rate_limit:{api_key}"
    current = cast(int, r.incrby(key))
    
    if current == 1:
        r.expire(key, per or settings.per_seconds)
    
    if current > (rate or settings.rate_limit):
        retry_after = cast(float, r.pttl(key))
        raise RateLimitedError(message="Rate limit exceeded", retry_after=retry_after)
    
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    api_key = request.headers.get("api-key")
    
    if not api_key:
        raise ApiKeyMissingError
    # TODO: also check if the API key is not in the database when it's ready
    
    await check_rate_limit(api_key)
    return await call_next(request)