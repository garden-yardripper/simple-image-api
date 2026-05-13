import secrets
import hashlib
from enum import Enum
from database import Database
from config import settings
from pydantic import BaseModel
import hmac
from responses import ApiKeyMissingError, ApiKeyInvalidError

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
        key_id, raw_key = full_key.split(".", 1)
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
    await db.execute("""
        INSERT INTO auth (api_key, key_id) VALUES (%s, %s);
    """, (key.hashed_key, key.key_id))
    
    await db.execute("""
        INSERT INTO users (username, key_id) VALUES (%s, %s);
    """, (username, key.key_id))
    
async def validate_key(db: Database, key: str | UserApiKey) -> bool:
    """Validate that an API key exists in the database. Returns True if valid, else False."""
    user_key = key if isinstance(key, UserApiKey) else UserApiKey.from_full_key(key)
    result = await db.fetchone("SELECT api_key FROM auth WHERE key_id = %s", (user_key.key_id,))
    if not result:
        return False
    
    api_key = result["api_key"]
    
    hashed_key = hmac.new(settings.api_secret.encode(), user_key.raw_key.encode(), hashlib.sha256).digest()
    return hmac.compare_digest(hashed_key, api_key)

async def check_for_key(db: Database, api_key: str) -> UserApiKey:
    if not api_key:
        raise ApiKeyMissingError
    
    user_key = UserApiKey.from_full_key(api_key)
    if not await validate_key(db, user_key):
        raise ApiKeyInvalidError
    return user_key