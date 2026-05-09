import secrets
import hashlib
from database import Database
from pydantic import BaseModel

# TODO: add salting

class UnhashedApiKey(BaseModel):
    key: str
    
class HashedApiKey(BaseModel):
    key: bytes

def generate_api_key() -> UnhashedApiKey:
    return UnhashedApiKey(key=secrets.token_urlsafe(32))

def hash_api_key(key: UnhashedApiKey) -> HashedApiKey:
    return HashedApiKey(key=hashlib.sha256(key.key.encode()).digest())

async def add_key_to_db(db: Database, key: HashedApiKey):
    await db.execute("INSERT INTO api_keys (api_key) VALUES (%s)", (key.key,))
    
async def key_in_db(db: Database, key: UnhashedApiKey):
    hashed_key = hash_api_key(key)
    result = await db.fetchone("SELECT api_key FROM api_keys WHERE api_key = %s", (hashed_key.key,))
    return result is not None