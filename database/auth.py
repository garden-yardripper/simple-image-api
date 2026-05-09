import secrets
import hashlib
from database import Database
from pydantic import BaseModel

class UserApiKey(BaseModel):
    raw_key: str
    key_id: str # 16 characters
    
    @property
    def full_key(self) -> str:
        return self.key_id + self.raw_key

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

async def store_api_key(db: Database, key: DatabaseApiKey) -> None:
    await db.execute("""
        INSERT INTO auth (api_key, key_id, salt)
        VALUES (%s, %s, %s)
    """, (key.salted_key, key.key_id, key.salt))
    
async def validate_key(db: Database, key: str) -> bool:
    key_id = key[:16]
    result = await db.fetchone("SELECT api_key, salt FROM auth WHERE key_id = %s", (key_id,))
    if not result:
        return False
    
    salted_key = result["api_key"]
    salt = result["salt"]
    raw_key = key[16:]
    
    hashed_key = hashlib.sha256(salt + raw_key.encode()).digest()
    return hashed_key == salted_key