import secrets
import hashlib
from database import Database
from pydantic import BaseModel
import hmac

class UserApiKey(BaseModel):
    raw_key: str
    key_id: str # 16 characters
    
    @property
    def full_key(self) -> str:
        return self.key_id + self.raw_key
    
    @classmethod
    def from_full_key(cls, full_key: str) -> "UserApiKey":
        key_id = full_key[:16]
        raw_key = full_key[16:]
        return cls(key_id=key_id, raw_key=raw_key)

class DatabaseApiKey(BaseModel):
    salted_key: bytes
    salt: bytes
    key_id: str

def create_api_key() -> UserApiKey:
    raw_key = secrets.token_urlsafe(32)
    key_id = secrets.token_urlsafe(12)
    return UserApiKey(raw_key=raw_key, key_id=key_id)

def hash_api_key(key: UserApiKey) -> DatabaseApiKey:
    salt = secrets.token_bytes(16)
    hashed_key = hashlib.sha256(salt + key.raw_key.encode()).digest()
    return DatabaseApiKey(salted_key=hashed_key, salt=salt, key_id=key.key_id)

async def store_api_key(db: Database, key: DatabaseApiKey, username: str) -> None:
    await db.execute("""
        INSERT INTO auth (api_key, key_id, salt) VALUES (%s, %s, %s);
        INSERT INTO users (username, key_id) VALUES (%s, %s);
    """, (key.salted_key, key.key_id, key.salt, username, key.key_id))
    
async def validate_key(db: Database, key: str | UserApiKey) -> bool:
    """Validate that an API key exists in the database. Returns True if valid, else False."""
    user_key = key if isinstance(key, UserApiKey) else UserApiKey.from_full_key(key)
    result = await db.fetchone("SELECT api_key, salt FROM auth WHERE key_id = %s", (user_key.key_id,))
    if not result:
        return False
    
    salted_key = result["api_key"]
    salt = result["salt"]
    
    hashed_key = hashlib.sha256(salt + user_key.raw_key.encode()).digest()
    return hmac.compare_digest(hashed_key, salted_key)