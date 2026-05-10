from fastapi import Depends, FastAPI, HTTPException, Header, Request, UploadFile, Query
from contextlib import asynccontextmanager
from aiomysql import MySQLError
import redis.asyncio as redis
from redis.exceptions import RedisError
from logs import setup_logging
from config import settings
from database import images, auth
from database.auth import UserApiKey
import ratelimit
from responses import ApiKeyInvalidError, ApiKeyMissingError, RateLimitInfoResponse
import mimetypes
import logging
import database
import aiofiles
import uuid
import os
from PIL import Image as PILImage
import asyncio

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

# dependencies (provides better type checking)
def get_db() -> database.Database:
    return app.state.db

def get_redis() -> redis.Redis:
    return app.state.r

async def is_valid_image(file: bytes) -> bool:
    def _run():
        try:
            with PILImage.open(file) as img:
                img.verify()
            return True
        except Exception:
            return False
    
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, _run)

@app.post("/images")
async def create_image(
    request: Request,
    file: UploadFile,
    title: str = Query(default=None, min_length=1, max_length=255), 
    description: str = Query(default=None, min_length=0, max_length=1000), 
    private: bool = Query(default=False),
    api_key: str = Header(default=None, alias="api-key"),
    db: database.Database = Depends(get_db),
    redis: redis.Redis = Depends(get_redis)
):
    if not api_key:
        raise ApiKeyMissingError
    
    user_key = UserApiKey.from_full_key(api_key)
    if not await auth.validate_key(db, user_key):
        raise ApiKeyInvalidError
    
    remaining, expiration = await ratelimit.check_key_rate_limit(redis, user_key.key_id)
    
    if not file.filename:
        raise HTTPException(400, {"message": "Uploaded image must have a filename."})
    
    filename, extension = os.path.splitext(file.filename)
    if not extension:
        raise HTTPException(400, {"message": "Uploaded file must have a valid extension."})
    
    extension = extension.lstrip(".").lower()
    mimetype, _ = mimetypes.guess_type(file.filename)
    
    acceptable_extensions = {"png", "jpg", "jpeg", "gif", "webp", "avif"}
    if extension not in acceptable_extensions:
        raise HTTPException(415, {"message": "Image type unsupported."})

    # validate file size is less than 10MiB
    max_size = 10 * 1024 ** 2 # 10MiB
    bytes_read = 0
    while True:
        if bytes_read > max_size:
            raise HTTPException(413, {"message": "Image file size exceeds 10MB limit."})
        
        contents = await file.read(1024 ** 2)
        contents_len = len(contents)
        bytes_read += contents_len
        
        if contents_len < 1024 ** 2:
            break # EOF reached
    
    await file.seek(0)
    file_bytes = await file.read()
    if not await is_valid_image(file_bytes):
        raise HTTPException(415, {"message": "Uploaded file is not a valid image or is malformed."})
    
    image_id = str(uuid.uuid4())
    path = os.path.join(settings.image_directory, f"{image_id}.{extension}")
    
    async with aiofiles.open(path, "wb") as f:
        await f.write(file_bytes)
    
    image = await images.store_image_metadata(
        db, image_id, user_key.key_id, str(request.base_url), extension,
        path, filename, bytes_read, mimetype, title, description, private
    )
    
    return RateLimitInfoResponse(
        image.model_dump(), remaining, expiration
    )