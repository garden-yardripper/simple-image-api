import secrets
import hashlib
from database import Database

# TODO: add salting

def generate_api_key() -> str:
    return secrets.token_urlsafe(32)

def hash_api_key(key: str) -> bytes:
    return hashlib.sha256(key.encode()).digest()

async def add_key_to_db(db: Database, hashed_key: bytes):
    await db.execute("INSERT INTO api_keys (api_key) VALUES (%s)", (hashed_key,))
    
async def key_in_db(db: Database, key: str):
    hashed_key = hash_api_key(key)
    result = await db.fetchone("SELECT api_key FROM api_keys WHERE api_key = %s", (hashed_key,))
    return result is not None