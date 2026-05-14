import secrets
import hashlib
from enum import Enum
from database import Database
from config import settings
from pydantic import BaseModel
import hmac
from responses import ApiKeyMissingError, ApiKeyInvalidError
import logging
from fastapi import Depends, Header
from typing import Annotated
from dependencies import get_db

logger = logging.getLogger(__name__)

class KeyType(Enum):
    live = "ak_live_"
    dev = "ak_dev_"

class UserApiKey(BaseModel):
    raw_key: str
    key_id: str
    
    @property
    def full_key(self) -> str:
        return self.key_id + "." + self.raw_key
    
    @classmethod
    def from_full_key(cls, full_key: str) -> "UserApiKey":
        try:
            key_id, raw_key = full_key.split(".", 1)
        except ValueError:
            logger.exception("Cannot split full key into key_id and raw_key.")
            raise ApiKeyInvalidError
        return cls(key_id=key_id, raw_key=raw_key)

class DatabaseApiKey(BaseModel):
    hashed_key: bytes
    key_id: str

def create_api_key(key_type: KeyType) -> UserApiKey:
    raw_key = secrets.token_urlsafe(32)
    key_id = secrets.token_urlsafe(12)
    return UserApiKey(raw_key=raw_key, key_id=key_type.value + key_id)

def hash_api_key(key: UserApiKey) -> DatabaseApiKey:
    hashed_key = hmac.new(settings.api_secret.encode(), key.raw_key.encode(), hashlib.sha256).digest()
    return DatabaseApiKey(hashed_key=hashed_key, key_id=key.key_id)

async def store_api_key(db: Database, key: DatabaseApiKey, username: str) -> None:
    async with db.transaction() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                INSERT INTO auth (api_key, key_id) VALUES (%s, %s);
            """, (key.hashed_key, key.key_id))
            
            await cur.execute("""
                INSERT INTO users (username, key_id) VALUES (%s, %s);
            """, (username, key.key_id))
            
    logger.info(
        "New API key stored in database.", 
        extra={"username": username, "key_id": key.key_id, "dev_key": key.key_id.startswith(KeyType.dev.value)}
    )
    
async def create_and_store_key(db: Database, username: str, key_type: KeyType) -> UserApiKey:
    user_key = create_api_key(key_type)
    database_key = hash_api_key(user_key)
    await store_api_key(db, database_key, username)
    return user_key
    
async def validate_key(db: Database, key: str | UserApiKey) -> bool:
    """Validate that an API key exists in the database. Returns True if valid, else False."""
    user_key = key if isinstance(key, UserApiKey) else UserApiKey.from_full_key(key)
    result = await db.fetchone("SELECT api_key FROM auth WHERE key_id = %s", (user_key.key_id,))
    if not result:
        return False
    
    api_key = result["api_key"]
    
    hashed_key = hmac.new(settings.api_secret.encode(), user_key.raw_key.encode(), hashlib.sha256).digest()
    valid = hmac.compare_digest(hashed_key, api_key)
    if valid:
        logger.info("API key is VALID.", extra={"key_id": user_key.key_id})
    else:
        logger.warning("API key is INVALID.", extra={"key_id": user_key.key_id})
    
    return valid

async def check_for_key(
    db: Annotated[Database, Depends(get_db)],
    api_key: Annotated[str | None, Header(alias="api-key")] = None
) -> UserApiKey:
    if not api_key:
        logger.info("User is missing API key.")
        raise ApiKeyMissingError
    
    user_key = UserApiKey.from_full_key(api_key)
    if not await validate_key(db, user_key):
        raise ApiKeyInvalidError
    return user_key