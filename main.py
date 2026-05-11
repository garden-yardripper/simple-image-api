from fastapi import FastAPI
from contextlib import asynccontextmanager
from aiomysql import MySQLError
import redis.asyncio as redis
from redis.exceptions import RedisError
from logs import setup_logging
from config import settings
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
    await db.update_tables()
    app.state.db = db
    
    logger.info("Database connection pool established and tables updated successfully.")
    
    logger.info("Creating Redis connection pool...")
    try:
        redis_pool = redis.ConnectionPool(
            max_connections=settings.redis.max_connections,
            host=settings.redis.host,
            port=settings.redis.port
        )
        r = redis.Redis(connection_pool=redis_pool)
        await r.ping() # type: ignore # "warm up" redis, otherwise the first command will be slow
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